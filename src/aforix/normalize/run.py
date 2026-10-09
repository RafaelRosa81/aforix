from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from aforix.config.loader import load_config
from aforix.config.paths import config_root_from_path
from aforix.runs.manager import create_run
from aforix.normalize.registry import NormalizationRegistry
from aforix.normalize.normalizer import normalize_table, TRACEABILITY_COLUMNS


DEFAULT_GROUPS = ["Summary", "Points", "Sections", "Gates"]
DEFAULT_CONCAT_GROUPS = ["Summary"]
VALID_WRITE_POLICIES = {"overwrite", "fail_if_exists"}


def _resolve_config_path(path_value: str | Path, *, project_root: Path) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = project_root / path
    return path.resolve()


def _get_project_root(config_path: Path) -> Path:
    return config_root_from_path(config_path)

def _get_enabled_instruments(cfg: dict[str, Any]) -> list[str]:
    ingest_cfg = cfg.get("ingest", {})
    if not isinstance(ingest_cfg, dict):
        raise ValueError("Config section 'ingest' must be a dictionary.")

    instruments: list[str] = []

    for instrument, instrument_cfg in ingest_cfg.items():
        if not isinstance(instrument_cfg, dict):
            continue
        if instrument_cfg.get("enabled") is False:
            continue
        instruments.append(str(instrument))

    return sorted(instruments)


def _get_normalize_sources(cfg: dict[str, Any]) -> list[str]:
    normalize_cfg = cfg.get("normalize", {})
    configured_sources = normalize_cfg.get("sources")
    enabled_instruments = _get_enabled_instruments(cfg)

    if configured_sources is None:
        return enabled_instruments

    if not isinstance(configured_sources, list):
        raise ValueError("'normalize.sources' must be a list.")

    sources = [str(item) for item in configured_sources]

    unknown = sorted(set(sources) - set(enabled_instruments))
    if unknown:
        raise ValueError(
            "normalize.sources contains instruments that are not enabled "
            f"in ingest config: {unknown}"
        )

    return sorted(sources)


def _get_normalize_groups(cfg: dict[str, Any]) -> list[str]:
    normalize_cfg = cfg.get("normalize", {})
    groups = normalize_cfg.get("groups", DEFAULT_GROUPS)

    if not isinstance(groups, list):
        raise ValueError("'normalize.groups' must be a list.")

    groups = [str(group).strip() for group in groups if str(group).strip()]

    if not groups:
        raise ValueError("'normalize.groups' cannot be empty.")

    return groups


def _get_concat_groups(cfg: dict[str, Any]) -> set[str]:
    normalize_cfg = cfg.get("normalize", {})
    concat_groups = normalize_cfg.get("concat_groups", DEFAULT_CONCAT_GROUPS)

    if not isinstance(concat_groups, list):
        raise ValueError("'normalize.concat_groups' must be a list.")

    return {str(group).strip() for group in concat_groups if str(group).strip()}


def _get_write_policy(cfg: dict[str, Any]) -> str:
    normalize_cfg = cfg.get("normalize", {})
    write_policy = str(normalize_cfg.get("write_policy", "overwrite")).strip()

    if write_policy not in VALID_WRITE_POLICIES:
        raise ValueError(
            "normalize.write_policy must be one of "
            f"{sorted(VALID_WRITE_POLICIES)}. Got: {write_policy}"
        )

    return write_policy


def _get_input_root(cfg: dict[str, Any], *, config_path: Path) -> Path:
    project_root = _get_project_root(config_path)
    input_dir = cfg.get("normalize", {}).get("input_dir") or "database/raw_canonical"
    return _resolve_config_path(input_dir, project_root=project_root)


def _get_output_root(cfg: dict[str, Any], *, config_path: Path) -> Path:
    project_root = _get_project_root(config_path)
    output_dir = cfg.get("normalize", {}).get("output_dir") or "database/normalized"
    return _resolve_config_path(output_dir, project_root=project_root)


def _get_registry_dir(cfg: dict[str, Any], *, config_path: Path) -> Path:
    project_root = _get_project_root(config_path)
    registry_dir = cfg.get("normalize", {}).get("registry_dir") or "configs/normalization"
    return _resolve_config_path(registry_dir, project_root=project_root)


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str)


def _normalize_single_csv(
    csv_path: Path,
    *,
    instrument: str,
    group: str,
    registry: NormalizationRegistry,
) -> pd.DataFrame:
    spec = registry.get(instrument, group)
    df_raw = _read_csv(csv_path)
    return normalize_table(df_raw, spec)


def _write_normalized_file(
    df: pd.DataFrame,
    *,
    output_path: Path,
    write_policy: str,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists():
        if write_policy == "fail_if_exists":
            raise FileExistsError(
                "Normalize output already exists and "
                f"write_policy=fail_if_exists: {output_path}"
            )
        if write_policy == "overwrite":
            print(f"Overwriting existing normalized file: {output_path}")

    trace_cols = [col for col in TRACEABILITY_COLUMNS if col in df.columns]
    remaining = [col for col in df.columns if col not in trace_cols]
    df = df[trace_cols + remaining]

    df.to_csv(output_path, index=False)


def _matching_nivus_sections_path(points_csv_path: Path) -> Path:
    return points_csv_path.parent.parent / "Sections" / points_csv_path.name.replace(
        "_Points_",
        "_Sections_",
    )


def _numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


POINT_MEASUREMENT_KEYS = [
    "instrument",
    "station_id",
    "measurement_date",
    "measurement_time",
]


def _normalized_measurement_keys(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in POINT_MEASUREMENT_KEYS:
        if col in out.columns:
            out[col] = out[col].astype("string").str.strip()
    return out


def _enrich_points_with_summary_width(
    points_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    *,
    label: str,
) -> pd.DataFrame:
    """Repeat Summary.width_total_m on every normalized Points row."""
    required_points = [*POINT_MEASUREMENT_KEYS, "width_m"]
    required_summary = [*POINT_MEASUREMENT_KEYS, "width_total_m"]

    missing_points = [col for col in required_points if col not in points_df.columns]
    missing_summary = [col for col in required_summary if col not in summary_df.columns]
    if missing_points or missing_summary:
        raise ValueError(
            f"Cannot enrich Points width for {label}. "
            f"Missing point columns={missing_points}; "
            f"missing summary columns={missing_summary}"
        )

    points = _normalized_measurement_keys(points_df)
    summary = _normalized_measurement_keys(summary_df)

    summary = summary[required_summary].copy()
    summary["width_total_m"] = pd.to_numeric(summary["width_total_m"], errors="coerce")

    conflicts = (
        summary.groupby(POINT_MEASUREMENT_KEYS, dropna=False)["width_total_m"]
        .nunique(dropna=True)
    )
    conflicting_keys = conflicts[conflicts > 1]
    if not conflicting_keys.empty:
        raise ValueError(
            f"Conflicting Summary.width_total_m values for {label}: "
            f"{list(conflicting_keys.index)}"
        )

    width_lookup = (
        summary.groupby(POINT_MEASUREMENT_KEYS, dropna=False, as_index=False)["width_total_m"]
        .first()
    )

    merged = points.merge(
        width_lookup,
        on=POINT_MEASUREMENT_KEYS,
        how="left",
        validate="many_to_one",
    )

    existing = pd.to_numeric(merged["width_m"], errors="coerce")
    from_summary = pd.to_numeric(merged["width_total_m"], errors="coerce")

    conflict_mask = (
        existing.notna()
        & from_summary.notna()
        & ((existing - from_summary).abs() > 1e-9)
    )
    if conflict_mask.any():
        raise ValueError(
            f"Points.width_m conflicts with Summary.width_total_m for {label}."
        )

    merged["width_m"] = existing.combine_first(from_summary)
    merged = merged.drop(columns=["width_total_m"])

    if merged["width_m"].isna().any():
        missing = int(merged["width_m"].isna().sum())
        raise ValueError(
            f"Missing width_m for {missing} normalized Points rows in {label}."
        )

    return merged[points_df.columns]


def _enrich_written_points_width(
    *,
    instrument: str,
    summary_paths: list[Path],
    point_paths: list[Path],
) -> list[pd.DataFrame]:
    """Enrich only Points files produced by the current normalization run."""
    if not summary_paths:
        raise FileNotFoundError(
            f"Normalized Summary required for Points.width_m: {instrument}"
        )
    if not point_paths:
        raise FileNotFoundError(
            f"Normalized Points required for Points.width_m: {instrument}"
        )

    summary_df = pd.concat(
        [_read_csv(path) for path in summary_paths],
        ignore_index=True,
        sort=False,
    )

    enriched_frames: list[pd.DataFrame] = []
    for points_path in point_paths:
        points_df = _read_csv(points_path)
        enriched = _enrich_points_with_summary_width(
            points_df,
            summary_df,
            label=f"{instrument}/{points_path.name}",
        )
        _write_normalized_file(
            enriched,
            output_path=points_path,
            write_policy="overwrite",
        )
        enriched_frames.append(enriched)

    return enriched_frames


def _enrich_nivus_points_from_sections(
    points_df: pd.DataFrame,
    sections_df: pd.DataFrame,
    *,
    label: str,
) -> pd.DataFrame:
    """
    Enrich normalized Nivus Points using normalized Nivus Sections.

    Rule:
      len(Sections) == len(Points) + 2

    Assignment:
      first point  -> first two sections
      last point   -> last two sections
      middle point -> one corresponding section
    """

    if points_df.empty or sections_df.empty:
        return points_df

    required_point_cols = ["point_index"]
    required_section_cols = ["section_index", "width_m", "depth_m", "q_ls", "percent_q"]

    missing_points = [col for col in required_point_cols if col not in points_df.columns]
    missing_sections = [col for col in required_section_cols if col not in sections_df.columns]

    if missing_points or missing_sections:
        raise ValueError(
            f"Cannot enrich Nivus Points for {label}. "
            f"Missing point columns={missing_points}; "
            f"missing section columns={missing_sections}"
        )

    out = points_df.copy()
    pts = out.copy()
    sec = sections_df.copy()

    pts["point_index"] = _numeric(pts["point_index"])
    sec["section_index"] = _numeric(sec["section_index"])

    for col in ["width_m", "depth_m", "q_ls", "percent_q"]:
        sec[col] = _numeric(sec[col])

    pts = pts.sort_values("point_index")
    sec = sec.sort_values("section_index")

    if len(sec) != len(pts) + 2:
        raise ValueError(
            f"Nivus Points/Sections mismatch for {label}: "
            f"points={len(pts)}, sections={len(sec)}. "
            "Expected sections = points + 2."
        )

    point_indices = pts.index.tolist()

    for i, row_idx in enumerate(point_indices):
        if i == 0:
            assigned_sections = sec.iloc[[0, 1]]
        elif i == len(point_indices) - 1:
            assigned_sections = sec.iloc[[-2, -1]]
        else:
            assigned_sections = sec.iloc[[i + 1]]

        hydraulic_cols = ["width_m", "depth_m", "q_ls", "percent_q"]
        missing_cols = [
            col
            for col in hydraulic_cols
            if assigned_sections[col].isna().any()
        ]
        if missing_cols:
            raise ValueError(
                f"Nivus Sections contain missing hydraulic values for {label}: "
                f"{missing_cols}"
            )

        area_m2 = (
            assigned_sections["width_m"] * assigned_sections["depth_m"]
        ).sum(min_count=1)
        q_ls = assigned_sections["q_ls"].sum(min_count=1)
        percent_q = assigned_sections["percent_q"].sum(min_count=1)

        out.loc[row_idx, "area_m2"] = area_m2
        out.loc[row_idx, "q_ls"] = q_ls
        out.loc[row_idx, "q_m3s"] = q_ls / 1000.0
        out.loc[row_idx, "percent_q"] = percent_q

    return out


def _enrich_nivus_points_by_measurement(
    points_df: pd.DataFrame,
    sections_df: pd.DataFrame,
    *,
    label: str,
) -> pd.DataFrame:
    """Enrich one or many Nivus measurements from matching Sections rows."""
    if points_df.empty:
        return points_df

    missing_keys = [
        col
        for col in POINT_MEASUREMENT_KEYS
        if col not in points_df.columns or col not in sections_df.columns
    ]
    if missing_keys:
        raise ValueError(
            f"Cannot match Nivus Points/Sections for {label}; "
            f"missing measurement keys: {missing_keys}"
        )

    points_keys = _normalized_measurement_keys(points_df)
    sections_keys = _normalized_measurement_keys(sections_df)
    out = points_df.copy()

    grouped = points_keys.groupby(
        POINT_MEASUREMENT_KEYS,
        dropna=False,
        sort=False,
    ).groups

    for key, point_index in grouped.items():
        key_values = key if isinstance(key, tuple) else (key,)
        mask = pd.Series(True, index=sections_keys.index)

        for col, value in zip(POINT_MEASUREMENT_KEYS, key_values):
            if pd.isna(value):
                mask &= sections_keys[col].isna()
            else:
                mask &= sections_keys[col].eq(value)

        section_group = sections_df.loc[mask]
        enriched = _enrich_nivus_points_from_sections(
            points_df.loc[point_index],
            section_group,
            label=f"{label}:{key_values}",
        )

        for col in ["area_m2", "q_ls", "q_m3s", "percent_q"]:
            if col in enriched.columns:
                out.loc[point_index, col] = enriched[col]

    percent = pd.to_numeric(out.get("percent_q"), errors="coerce")
    if percent.isna().any():
        missing = int(percent.isna().sum())
        raise ValueError(
            f"Nivus percent_q enrichment incomplete for {label}: "
            f"{missing} Points rows remain empty."
        )

    return out


def _normalize_nivus_sections_for_points_input(
    points_csv_path: Path,
    *,
    registry: NormalizationRegistry,
) -> pd.DataFrame:
    """Load normalized Nivus Sections from either concat or file-group layout."""
    sections_file = points_csv_path.parent / "Sections.csv"
    sections_dir = points_csv_path.parent / "Sections"

    if sections_file.exists():
        return _normalize_single_csv(
            sections_file,
            instrument="nivus",
            group="Sections",
            registry=registry,
        )

    if sections_dir.exists():
        frames = [
            _normalize_single_csv(
                path,
                instrument="nivus",
                group="Sections",
                registry=registry,
            )
            for path in sorted(sections_dir.glob("*.csv"))
        ]
        if frames:
            return pd.concat(frames, ignore_index=True, sort=False)

    raise FileNotFoundError(
        f"Matching Nivus Sections input not found for Points: {points_csv_path}"
    )


def _normalize_nivus_points_with_sections(
    points_csv_path: Path,
    *,
    registry: NormalizationRegistry,
) -> pd.DataFrame:
    points_df = _normalize_single_csv(
        points_csv_path,
        instrument="nivus",
        group="Points",
        registry=registry,
    )

    sections_csv_path = _matching_nivus_sections_path(points_csv_path)

    if not sections_csv_path.exists():
        raise FileNotFoundError(
            f"Matching Nivus Sections file not found for Points: {points_csv_path}"
        )

    sections_df = _normalize_single_csv(
        sections_csv_path,
        instrument="nivus",
        group="Sections",
        registry=registry,
    )

    return _enrich_nivus_points_by_measurement(
        points_df,
        sections_df,
        label=points_csv_path.name,
    )


def _normalize_concat_group(
    input_path: Path,
    *,
    instrument: str,
    group: str,
    output_root: Path,
    registry: NormalizationRegistry,
    write_policy: str,
) -> pd.DataFrame | None:
    if not input_path.exists():
        return None

    if instrument == "nivus" and group == "Points":
        points_df = _normalize_single_csv(
            input_path,
            instrument=instrument,
            group=group,
            registry=registry,
        )
        sections_df = _normalize_nivus_sections_for_points_input(
            input_path,
            registry=registry,
        )
        df_norm = _enrich_nivus_points_by_measurement(
            points_df,
            sections_df,
            label=input_path.name,
        )
    else:
        df_norm = _normalize_single_csv(
            input_path,
            instrument=instrument,
            group=group,
            registry=registry,
        )

    outpath = output_root / instrument / f"{group}.csv"
    _write_normalized_file(df_norm, output_path=outpath, write_policy=write_policy)

    print(f"Normalized: {input_path} -> {outpath}")
    return df_norm


def _normalize_file_group(
    input_dir: Path,
    *,
    instrument: str,
    group: str,
    output_root: Path,
    registry: NormalizationRegistry,
    write_policy: str,
) -> list[pd.DataFrame]:
    if not input_dir.exists():
        return []

    input_paths = sorted(input_dir.glob("*.csv"))
    output_dir = output_root / instrument / group
    target_paths = [output_dir / path.name for path in input_paths]

    if write_policy == "overwrite" and output_dir.exists():
        for stale_path in output_dir.glob("*.csv"):
            stale_path.unlink()

    if write_policy == "fail_if_exists":
        existing = [path for path in target_paths if path.exists()]
        if existing:
            raise FileExistsError(
                "Normalize output already exists and "
                f"write_policy=fail_if_exists: {existing[0]}"
            )

    prepared: list[tuple[Path, pd.DataFrame]] = []

    for csv_path in input_paths:
        if instrument == "nivus" and group == "Points":
            df_norm = _normalize_nivus_points_with_sections(
                csv_path,
                registry=registry,
            )
        else:
            df_norm = _normalize_single_csv(
                csv_path,
                instrument=instrument,
                group=group,
                registry=registry,
            )

        prepared.append((csv_path, df_norm))

    outputs: list[pd.DataFrame] = []
    for csv_path, df_norm in prepared:
        outpath = output_dir / csv_path.name
        _write_normalized_file(
            df_norm,
            output_path=outpath,
            write_policy="overwrite" if write_policy == "overwrite" else write_policy,
        )
        print(f"Normalized: {csv_path} -> {outpath}")
        outputs.append(df_norm)

    return outputs


def _write_cross_instrument_concat(
    frames: list[pd.DataFrame],
    *,
    group: str,
    output_root: Path,
    write_policy: str,
) -> None:
    if not frames:
        return

    merged = pd.concat(frames, ignore_index=True, sort=False)
    outpath = output_root / f"{group}.csv"

    _write_normalized_file(merged, output_path=outpath, write_policy=write_policy)

    print(f"Concatenated normalized group: {group} -> {outpath}")


def _clear_stale_concat_outputs(
    *,
    output_root: Path,
    concat_groups: set[str],
) -> None:
    """Remove prior root concatenations before an overwrite rebuild."""
    for group in concat_groups:
        path = output_root / f"{group}.csv"
        if path.exists():
            path.unlink()


def _raise_width_enrichment_failure(
    *,
    instrument: str,
    point_paths: list[Path],
    output_root: Path,
    exc: Exception,
) -> None:
    """Remove invalid Points outputs and fail normalization visibly."""
    for path in point_paths:
        path.unlink(missing_ok=True)

    (output_root / "Points.csv").unlink(missing_ok=True)

    raise RuntimeError(
        f"Failed enriching {instrument}/Points.width_m: {exc}"
    ) from exc


def normalize_database(config_path: Path) -> Path:
    config_path = Path(config_path).resolve()
    cfg = load_config(config_path)

    normalize_cfg = cfg.get("normalize", {})

    if normalize_cfg.get("enabled") is False:
        print("normalize is disabled in config.")
        return create_run("normalize", config_path)

    run_dir = create_run("normalize", config_path)

    input_root = _get_input_root(cfg, config_path=config_path)
    output_root = _get_output_root(cfg, config_path=config_path)
    registry_dir = _get_registry_dir(cfg, config_path=config_path)

    instruments = _get_normalize_sources(cfg)
    groups = _get_normalize_groups(cfg)
    concat_groups = _get_concat_groups(cfg)
    write_policy = _get_write_policy(cfg)

    if not input_root.exists():
        raise FileNotFoundError(f"Normalize input directory not found: {input_root}")

    output_root.mkdir(parents=True, exist_ok=True)

    if write_policy == "overwrite":
        _clear_stale_concat_outputs(
            output_root=output_root,
            concat_groups=concat_groups,
        )

    registry = NormalizationRegistry(registry_dir)

    print("Normalizing raw_canonical database")
    print(f"Input root: {input_root}")
    print(f"Output root: {output_root}")
    print(f"Registry dir: {registry_dir}")
    print(f"Instruments: {instruments}")
    print(f"Groups: {groups}")
    print(f"Concat groups: {sorted(concat_groups)}")
    print(f"Write policy: {write_policy}")

    cross_instrument_frames: dict[str, list[pd.DataFrame]] = {
        group: []
        for group in concat_groups
    }

    normalized_count = 0
    failed: list[tuple[str, str]] = []

    for instrument in instruments:
        points_written = False
        written_group_paths: dict[str, list[Path]] = {
            group: []
            for group in groups
        }

        for group in groups:
            try:
                registry.get(instrument, group)
            except KeyError:
                print(f"Skipping: no registry spec for {instrument}/{group}")
                continue

            try:
                input_file = input_root / instrument / f"{group}.csv"
                input_dir = input_root / instrument / group

                if input_file.exists():
                    df_norm = _normalize_concat_group(
                        input_file,
                        instrument=instrument,
                        group=group,
                        output_root=output_root,
                        registry=registry,
                        write_policy=write_policy,
                    )

                    if df_norm is not None:
                        normalized_count += 1
                        written_group_paths[group] = [
                            output_root / instrument / f"{group}.csv"
                        ]
                        if group == "Points":
                            points_written = True

                        if group in concat_groups and group != "Points":
                            cross_instrument_frames[group].append(df_norm)

                elif input_dir.exists():
                    frames = _normalize_file_group(
                        input_dir,
                        instrument=instrument,
                        group=group,
                        output_root=output_root,
                        registry=registry,
                        write_policy=write_policy,
                    )

                    normalized_count += len(frames)
                    written_group_paths[group] = [
                        output_root / instrument / group / path.name
                        for path in sorted(input_dir.glob("*.csv"))
                    ]
                    if group == "Points" and frames:
                        points_written = True

                    if group in concat_groups and group != "Points":
                        cross_instrument_frames[group].extend(frames)

                else:
                    print(f"{instrument}/{group}: no input found")

            except FileExistsError:
                raise
            except Exception as exc:
                failed.append((f"{instrument}/{group}", str(exc)))
                print(f"ERROR normalizing {instrument}/{group}: {exc}")

        if points_written:
            try:
                enriched_points_frames = _enrich_written_points_width(
                    instrument=instrument,
                    summary_paths=written_group_paths.get("Summary", []),
                    point_paths=written_group_paths.get("Points", []),
                )
                if "Points" in concat_groups:
                    cross_instrument_frames["Points"].extend(enriched_points_frames)
            except Exception as exc:
                _raise_width_enrichment_failure(
                    instrument=instrument,
                    point_paths=written_group_paths.get("Points", []),
                    output_root=output_root,
                    exc=exc,
                )

    for group, frames in cross_instrument_frames.items():
        _write_cross_instrument_concat(
            frames,
            group=group,
            output_root=output_root,
            write_policy=write_policy,
        )

    print(f"Normalized outputs: {normalized_count}")

    if failed:
        print("Failed normalize groups:")
        for label, error in failed:
            print(f" - {label}: {error}")
        details = "; ".join(f"{label}: {error}" for label, error in failed)
        raise RuntimeError(f"Normalization failed: {details}")

    print(f"Run created: {run_dir}")
    return run_dir


def normalize_run(
    run_dir: Path | None = None,
    registry_dir: Path = Path("configs/normalization"),
) -> Path:
    if run_dir is None:
        raise ValueError(
            "normalize_run(run_dir=...) is deprecated for database normalization. "
            "Use normalize_database(config_path) instead."
        )

    raise ValueError(
        "Per-run normalization is no longer the preferred pipeline path. "
        "Use normalize_database(config_path) over database/raw_canonical."
    )
