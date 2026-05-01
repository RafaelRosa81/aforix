from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from aforix.config.loader import load_config
from aforix.runs.manager import create_run
from aforix.normalize.registry import NormalizationRegistry
from aforix.normalize.normalizer import normalize_table, TRACEABILITY_COLUMNS


DEFAULT_GROUPS = ["Summary", "Points", "Sections", "Gates"]
DEFAULT_CONCAT_GROUPS = ["Summary"]


def _resolve_config_path(path_value: str | Path, *, project_root: Path) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = project_root / path
    return path.resolve()


def _get_project_root(config_path: Path) -> Path:
    resolved = config_path.resolve()
    if len(resolved.parents) >= 3:
        return resolved.parents[2]
    return Path.cwd().resolve()


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
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

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
        print(
            f"WARNING: cannot enrich Nivus Points for {label}. "
            f"Missing point columns={missing_points}; "
            f"missing section columns={missing_sections}"
        )
        return points_df

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
        print(
            f"WARNING: Nivus Points/Sections mismatch for {label}: "
            f"points={len(pts)}, sections={len(sec)}. "
            "Expected sections = points + 2. Enrichment skipped."
        )
        return out

    point_indices = pts.index.tolist()

    for i, row_idx in enumerate(point_indices):
        if i == 0:
            assigned_sections = sec.iloc[[0, 1]]
        elif i == len(point_indices) - 1:
            assigned_sections = sec.iloc[[-2, -1]]
        else:
            assigned_sections = sec.iloc[[i + 1]]

        area_m2 = (assigned_sections["width_m"] * assigned_sections["depth_m"]).sum()
        q_ls = assigned_sections["q_ls"].sum()
        percent_q = assigned_sections["percent_q"].sum()

        out.loc[row_idx, "area_m2"] = area_m2
        out.loc[row_idx, "q_ls"] = q_ls
        out.loc[row_idx, "q_m3s"] = q_ls / 1000.0
        out.loc[row_idx, "percent_q"] = percent_q

    return out


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
        print(
            f"WARNING: matching Nivus Sections file not found for Points file: "
            f"{points_csv_path}"
        )
        return points_df

    sections_df = _normalize_single_csv(
        sections_csv_path,
        instrument="nivus",
        group="Sections",
        registry=registry,
    )

    return _enrich_nivus_points_from_sections(
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
) -> pd.DataFrame | None:
    if not input_path.exists():
        return None

    df_norm = _normalize_single_csv(
        input_path,
        instrument=instrument,
        group=group,
        registry=registry,
    )

    outpath = output_root / instrument / f"{group}.csv"
    _write_normalized_file(df_norm, output_path=outpath)

    print(f"Normalized: {input_path} -> {outpath}")
    return df_norm


def _normalize_file_group(
    input_dir: Path,
    *,
    instrument: str,
    group: str,
    output_root: Path,
    registry: NormalizationRegistry,
) -> list[pd.DataFrame]:
    if not input_dir.exists():
        return []

    outputs: list[pd.DataFrame] = []

    for csv_path in sorted(input_dir.glob("*.csv")):
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

        outpath = output_root / instrument / group / csv_path.name
        _write_normalized_file(df_norm, output_path=outpath)

        print(f"Normalized: {csv_path} -> {outpath}")
        outputs.append(df_norm)

    return outputs


def _write_cross_instrument_concat(
    frames: list[pd.DataFrame],
    *,
    group: str,
    output_root: Path,
) -> None:
    if not frames:
        return

    merged = pd.concat(frames, ignore_index=True, sort=False)
    outpath = output_root / f"{group}.csv"

    _write_normalized_file(merged, output_path=outpath)

    print(f"Concatenated normalized group: {group} -> {outpath}")


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

    if not input_root.exists():
        raise FileNotFoundError(f"Normalize input directory not found: {input_root}")

    output_root.mkdir(parents=True, exist_ok=True)

    registry = NormalizationRegistry(registry_dir)

    print("Normalizing raw_canonical database")
    print(f"Input root: {input_root}")
    print(f"Output root: {output_root}")
    print(f"Registry dir: {registry_dir}")
    print(f"Instruments: {instruments}")
    print(f"Groups: {groups}")
    print(f"Concat groups: {sorted(concat_groups)}")

    cross_instrument_frames: dict[str, list[pd.DataFrame]] = {
        group: []
        for group in concat_groups
    }

    normalized_count = 0
    failed: list[tuple[str, str]] = []

    for instrument in instruments:
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
                    )

                    if df_norm is not None:
                        normalized_count += 1

                        if group in concat_groups:
                            cross_instrument_frames[group].append(df_norm)

                elif input_dir.exists():
                    frames = _normalize_file_group(
                        input_dir,
                        instrument=instrument,
                        group=group,
                        output_root=output_root,
                        registry=registry,
                    )

                    normalized_count += len(frames)

                    if group in concat_groups:
                        cross_instrument_frames[group].extend(frames)

                else:
                    print(f"{instrument}/{group}: no input found")

            except Exception as exc:
                failed.append((f"{instrument}/{group}", str(exc)))
                print(f"ERROR normalizing {instrument}/{group}: {exc}")

    for group, frames in cross_instrument_frames.items():
        _write_cross_instrument_concat(
            frames,
            group=group,
            output_root=output_root,
        )

    print(f"Normalized outputs: {normalized_count}")

    if failed:
        print("Failed normalize groups:")
        for label, error in failed:
            print(f" - {label}: {error}")

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