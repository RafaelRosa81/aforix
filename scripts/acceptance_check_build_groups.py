from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yaml


TRACE_REQUIRED_NONEMPTY = [
    "station_id",
    "measurement_date",
    "measurement_time",
    "instrument",
    "source_file",
    "source_run_dir",
    "run_id",
]


def project_root_from_config(config_path: Path) -> Path:
    resolved = config_path.resolve()
    for candidate in [resolved.parent, *resolved.parents]:
        if (candidate / ".git").exists() or (candidate / "pyproject.toml").exists():
            return candidate
    return Path.cwd().resolve()


def resolve_path(project_root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (project_root / path).resolve()


def latest_ingest_run(runs_root: Path, instrument: str) -> Path:
    root = runs_root / f"ingest_{instrument}"
    candidates = sorted(
        p for p in root.iterdir()
        if p.is_dir() and (p / "outputs" / "raw_canonical").exists()
    )
    if not candidates:
        raise FileNotFoundError(f"No ingest run found for {instrument}: {root}")
    return candidates[-1]


def normalize_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        out[col] = out[col].fillna("").astype(str)
    return out


def compare_common_columns(
    expected: pd.DataFrame,
    observed: pd.DataFrame,
    *,
    identity_columns: list[str] | None = None,
) -> tuple[int, list[str]]:
    common = [c for c in expected.columns if c in observed.columns]
    if not common:
        return 1, ["no common columns"]

    exp = normalize_frame(expected[common])
    obs = normalize_frame(observed[common])

    if len(exp) != len(obs):
        return 1, [f"row count differs: expected={len(exp)} observed={len(obs)}"]

    if identity_columns:
        keys = [c for c in identity_columns if c in common]
        if keys:
            exp = exp.sort_values(keys, kind="stable").reset_index(drop=True)
            obs = obs.sort_values(keys, kind="stable").reset_index(drop=True)
        else:
            exp = exp.reset_index(drop=True)
            obs = obs.reset_index(drop=True)
    else:
        exp = exp.reset_index(drop=True)
        obs = obs.reset_index(drop=True)

    mismatches = 0
    examples: list[str] = []
    for col in common:
        bad = exp[col] != obs[col]
        count = int(bad.sum())
        mismatches += count
        if count and len(examples) < 10:
            idx = bad[bad].index[0]
            identity = ""
            if identity_columns:
                present = [c for c in identity_columns if c in common]
                if present:
                    identity = " [" + ", ".join(
                        f"{c}={exp.at[idx, c]!r}" for c in present
                    ) + "]"
            examples.append(
                f"column={col} row={idx}{identity} "
                f"expected={exp.at[idx, col]!r} observed={obs.at[idx, col]!r}"
            )
    return mismatches, examples


def traceability_issues(df: pd.DataFrame) -> list[str]:
    issues: list[str] = []
    for col in TRACE_REQUIRED_NONEMPTY:
        if col not in df.columns:
            issues.append(f"missing traceability column: {col}")
            continue
        values = df[col].fillna("").astype(str).str.strip()
        n_empty = int((values == "").sum())
        if n_empty:
            issues.append(f"{col}: {n_empty} empty rows")
    return issues


def load_concat_expected(paths: list[Path]) -> pd.DataFrame:
    frames = [pd.read_csv(path, dtype=str) for path in paths]
    return pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify build-groups against the latest real-data ingest runs."
    )
    parser.add_argument("--config", default="configs/examples/acceptance_real.yaml")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    project_root = project_root_from_config(config_path)
    with config_path.open("r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    runs_root = resolve_path(project_root, cfg["paths"].get("runs_root", "runs"))
    build_cfg = cfg.get("build_groups", {}) or {}
    output_root = resolve_path(
        project_root,
        build_cfg.get("output_dir", "database/raw_canonical"),
    )

    instruments = list(build_cfg.get("sources", []))
    groups = list(build_cfg.get("groups", []))
    concat_groups = set(build_cfg.get("concat_groups", []))

    report_rows: list[dict[str, object]] = []
    expected_manifest_rows = 0

    for instrument in instruments:
        run_dir = latest_ingest_run(runs_root, instrument)
        source_root = run_dir / "outputs" / "raw_canonical" / instrument

        for group in groups:
            source_dir = source_root / group
            source_files = sorted(source_dir.glob("*.csv")) if source_dir.exists() else []
            if not source_files:
                continue

            expected_manifest_rows += len(source_files)

            if group in concat_groups:
                output_path = output_root / instrument / f"{group}.csv"
                if not output_path.exists():
                    report_rows.append({
                        "instrument": instrument,
                        "group": group,
                        "expected_files": len(source_files),
                        "observed_files": 0,
                        "expected_rows": None,
                        "observed_rows": None,
                        "content_mismatches": 1,
                        "traceability_issues": "missing concatenated output",
                        "status": "FAIL",
                    })
                    continue

                expected = load_concat_expected(source_files)
                observed = pd.read_csv(output_path, dtype=str)
                mismatches, examples = compare_common_columns(
                    expected,
                    observed,
                    identity_columns=[
                        "instrument",
                        "station_id",
                        "measurement_date",
                        "measurement_time",
                        "source_file",
                    ],
                )
                trace_issues = traceability_issues(observed)
                passed = (
                    len(expected) == len(observed)
                    and mismatches == 0
                    and not trace_issues
                )

                report_rows.append({
                    "instrument": instrument,
                    "group": group,
                    "expected_files": len(source_files),
                    "observed_files": 1,
                    "expected_rows": len(expected),
                    "observed_rows": len(observed),
                    "content_mismatches": mismatches,
                    "traceability_issues": " | ".join(trace_issues),
                    "examples": " | ".join(examples),
                    "status": "PASS" if passed else "FAIL",
                })
                continue

            output_dir = output_root / instrument / group
            output_files = sorted(output_dir.glob("*.csv")) if output_dir.exists() else []
            expected_names = {p.name for p in source_files}
            observed_names = {p.name for p in output_files}
            missing = sorted(expected_names - observed_names)
            unexpected = sorted(observed_names - expected_names)

            total_expected_rows = 0
            total_observed_rows = 0
            mismatches = 0
            trace_issues: list[str] = []
            examples: list[str] = []

            for source_path in source_files:
                expected = pd.read_csv(source_path, dtype=str)
                total_expected_rows += len(expected)
                output_path = output_dir / source_path.name
                if not output_path.exists():
                    mismatches += 1
                    if len(examples) < 10:
                        examples.append(f"missing output file: {source_path.name}")
                    continue

                observed = pd.read_csv(output_path, dtype=str)
                total_observed_rows += len(observed)
                file_mismatches, file_examples = compare_common_columns(expected, observed)
                mismatches += file_mismatches
                if file_examples and len(examples) < 10:
                    examples.extend(
                        f"{source_path.name}: {msg}"
                        for msg in file_examples[: 10 - len(examples)]
                    )
                file_trace = traceability_issues(observed)
                trace_issues.extend(f"{source_path.name}: {msg}" for msg in file_trace)

            if unexpected:
                examples.append(f"unexpected output files: {unexpected[:10]}")
            if missing:
                examples.append(f"missing output files: {missing[:10]}")

            passed = (
                not missing
                and not unexpected
                and len(source_files) == len(output_files)
                and total_expected_rows == total_observed_rows
                and mismatches == 0
                and not trace_issues
            )

            report_rows.append({
                "instrument": instrument,
                "group": group,
                "expected_files": len(source_files),
                "observed_files": len(output_files),
                "expected_rows": total_expected_rows,
                "observed_rows": total_observed_rows,
                "content_mismatches": mismatches,
                "traceability_issues": " | ".join(trace_issues[:10]),
                "examples": " | ".join(examples[:10]),
                "status": "PASS" if passed else "FAIL",
            })

    manifest_dir = output_root / "_manifests"
    manifests = sorted(manifest_dir.glob("build_groups_*.csv")) if manifest_dir.exists() else []
    manifest_status = "FAIL"
    manifest_rows = 0
    manifest_selected = 0
    manifest_path = ""

    if manifests:
        latest_manifest = manifests[-1]
        manifest_path = str(latest_manifest)
        manifest = pd.read_csv(latest_manifest, dtype=str)
        manifest_rows = len(manifest)
        if "selected" in manifest.columns:
            manifest_selected = int(
                manifest["selected"].fillna("").astype(str).str.lower().eq("true").sum()
            )
        manifest_status = (
            "PASS"
            if manifest_rows == expected_manifest_rows
            and manifest_selected == expected_manifest_rows
            else "FAIL"
        )

    report = pd.DataFrame(report_rows)
    checks_dir = runs_root / "_checks"
    checks_dir.mkdir(parents=True, exist_ok=True)
    report_path = checks_dir / "build_groups_acceptance.csv"
    report.to_csv(report_path, index=False, encoding="utf-8-sig")

    n_pass = int((report["status"] == "PASS").sum()) if not report.empty else 0
    n_fail = int((report["status"] == "FAIL").sum()) if not report.empty else 0

    print("Aforix build-groups real-data acceptance")
    print("=" * 42)
    print(f"Output root: {output_root}")
    print(f"Group checks: {len(report)}")
    print(f"PASS: {n_pass}")
    print(f"FAIL: {n_fail}")
    print(f"Manifest expected rows: {expected_manifest_rows}")
    print(f"Manifest rows         : {manifest_rows}")
    print(f"Manifest selected     : {manifest_selected}")
    print(f"Manifest status       : {manifest_status}")
    print(f"Report: {report_path}")
    if manifest_path:
        print(f"Manifest: {manifest_path}")

    if n_fail or manifest_status != "PASS":
        print("")
        print("Failed group checks:")
        if n_fail:
            cols = [
                "instrument",
                "group",
                "expected_files",
                "observed_files",
                "expected_rows",
                "observed_rows",
                "content_mismatches",
                "traceability_issues",
                "examples",
            ]
            print(report.loc[report["status"] == "FAIL", cols].to_string(index=False))
        if manifest_status != "PASS":
            print(
                f"Manifest mismatch: expected={expected_manifest_rows}, "
                f"rows={manifest_rows}, selected={manifest_selected}"
            )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
