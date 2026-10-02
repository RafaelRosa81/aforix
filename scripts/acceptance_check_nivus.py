from __future__ import annotations

import argparse
import datetime as dt
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import yaml


METADATA_COLUMNS = {
    "instrument",
    "source",
    "station_id",
    "station_name",
    "measurement_date",
    "measurement_time",
    "timezone",
    "source_file",
    "source_run_dir",
    "input_file",
    "input_path",
    "run_id",
}


def project_root_from_config(config_path: Path) -> Path:
    resolved = config_path.resolve()
    for candidate in [resolved.parent, *resolved.parents]:
        if (candidate / ".git").exists() or (candidate / "pyproject.toml").exists():
            return candidate
    return Path.cwd().resolve()


def latest_run(runs_root: Path) -> Path:
    root = runs_root / "ingest_nivus"
    candidates = sorted(p for p in root.iterdir() if p.is_dir())
    if not candidates:
        raise FileNotFoundError(f"No Nivus acceptance runs found in: {root}")
    return candidates[-1]


def element_key(element: ET.Element) -> str:
    unit = str(element.attrib.get("unit", "")).strip()
    return f"{element.tag} [{unit}]" if unit else element.tag


def element_value(element: ET.Element) -> str:
    if "val" in element.attrib:
        return str(element.attrib.get("val", "")).strip()
    return str(element.text or "").strip()


def simple_children(parent: ET.Element, skip_tags: set[str] | None = None) -> dict[str, str]:
    skip_tags = skip_tags or set()
    row: dict[str, str] = {}
    for child in parent:
        if child.tag in skip_tags:
            continue
        has_children = len(list(child)) > 0
        value = element_value(child)
        if has_children and value == "":
            continue
        row[element_key(child)] = value
    return row


def parse_timestamp(value: str, filename: str) -> tuple[str, str]:
    text = str(value or "").strip()
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
    ):
        try:
            parsed = dt.datetime.strptime(text, fmt)
            return parsed.strftime("%Y%m%d"), parsed.strftime("%H%M%S")
        except ValueError:
            pass

    match = re.search(
        r"(?P<year>\d{4})[-/](?P<month>\d{2})[-/](?P<day>\d{2})[T\s_]"
        r"(?P<hour>\d{2}):?(?P<minute>\d{2}):?(?P<second>\d{2})",
        text,
    )
    if match:
        return (
            f"{match.group('year')}{match.group('month')}{match.group('day')}",
            f"{match.group('hour')}{match.group('minute')}{match.group('second')}",
        )

    matches = re.findall(r"(\d{8})_(\d{6})", filename)
    if matches:
        return matches[-1]
    return "unknown_date", "unknown_time"


def parse_xml_independently(path: Path) -> tuple[dict[str, str], dict[str, list[dict[str, str]]]]:
    root = ET.parse(path).getroot()
    timestamp = root.find("./timestamp")
    if timestamp is None:
        raise ValueError("missing ./timestamp")

    ref = timestamp.find("./ref")
    name = timestamp.find("./name")
    station_id = str(ref.attrib.get("val", "")).strip() if ref is not None else ""
    station_name = str(name.attrib.get("val", "")).strip() if name is not None else ""
    timestamp_time = str(timestamp.attrib.get("time", "")).strip()
    measurement_date, measurement_time = parse_timestamp(timestamp_time, path.name)

    metadata = {
        "station_id": station_id,
        "station_name": station_name,
        "measurement_date": measurement_date,
        "measurement_time": measurement_time,
    }

    groups: dict[str, list[dict[str, str]]] = {
        "Summary": [],
        "Points": [],
        "Sections": [],
        "Gates": [],
    }

    summary: dict[str, str] = {}
    for key, value in root.attrib.items():
        summary[f"archive_{key}"] = str(value).strip()
    for key, value in timestamp.attrib.items():
        summary[f"timestamp_{key}"] = str(value).strip()
    summary.update(simple_children(timestamp, {"sect", "point", "calib"}))
    groups["Summary"].append(summary)

    for sect in timestamp.findall("./sect"):
        row = {str(k): str(v).strip() for k, v in sect.attrib.items()}
        row.update(simple_children(sect))
        groups["Sections"].append(row)

    for point in timestamp.findall("./point"):
        row = {str(k): str(v).strip() for k, v in point.attrib.items()}
        row.update(simple_children(point, {"gate"}))
        groups["Points"].append(row)

    for point in timestamp.findall("./point"):
        parent_index = str(point.attrib.get("index", "")).strip()
        for gate in point.findall("./gate"):
            row = {"point_index": parent_index}
            row.update({str(k): str(v).strip() for k, v in gate.attrib.items()})
            row.update(simple_children(gate))
            groups["Gates"].append(row)

    return metadata, groups


def emptyish(value: object) -> bool:
    if value is None or pd.isna(value):
        return True
    return str(value).strip() == ""


def as_float(value: object) -> float | None:
    if emptyish(value):
        return None
    text = str(value).strip().replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def equal_value(expected: object, observed: object, tol: float) -> bool:
    if emptyish(expected) and emptyish(observed):
        return True
    e_num = as_float(expected)
    o_num = as_float(observed)
    if e_num is not None and o_num is not None:
        return math.isclose(e_num, o_num, rel_tol=0.0, abs_tol=tol)
    return str(expected).strip() == str(observed).strip()


def compare_group(
    expected_rows: list[dict[str, str]],
    observed: pd.DataFrame,
    *,
    tolerance: float,
) -> tuple[int, int, list[str]]:
    row_count_mismatch = 0 if len(expected_rows) == len(observed) else 1
    field_mismatches = 0
    examples: list[str] = []

    for idx, expected in enumerate(expected_rows):
        if idx >= len(observed):
            break
        row = observed.iloc[idx]
        for key, expected_value in expected.items():
            if key not in observed.columns:
                field_mismatches += 1
                if len(examples) < 10:
                    examples.append(f"row={idx} missing_column={key}")
                continue
            observed_value = row.get(key)
            if not equal_value(expected_value, observed_value, tolerance):
                field_mismatches += 1
                if len(examples) < 10:
                    examples.append(
                        f"row={idx} column={key} expected={expected_value!r} observed={observed_value!r}"
                    )

    return row_count_mismatch, field_mismatches, examples


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Independent real-data acceptance check for Nivus ingest."
    )
    parser.add_argument("--config", default="configs/examples/acceptance_real.yaml")
    parser.add_argument("--run-dir", default=None)
    parser.add_argument("--tolerance", type=float, default=1e-9)
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    project_root = project_root_from_config(config_path)
    with config_path.open("r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    runs_value = Path(cfg["paths"].get("runs_root", "runs"))
    runs_root = runs_value if runs_value.is_absolute() else project_root / runs_value
    run_dir = Path(args.run_dir).resolve() if args.run_dir else latest_run(runs_root)

    output_root = run_dir / "outputs" / "raw_canonical" / "nivus"
    summary_files = sorted((output_root / "Summary").glob("*.csv"))

    report_rows: list[dict[str, object]] = []
    totals = {
        "Summary": 0,
        "Points": 0,
        "Sections": 0,
        "Gates": 0,
    }
    total_field_mismatches = 0
    total_row_count_mismatches = 0
    metadata_mismatches = 0

    for summary_path in summary_files:
        summary_df = pd.read_csv(summary_path, dtype=str, encoding="utf-8-sig")
        if summary_df.empty:
            report_rows.append({
                "measurement": summary_path.name,
                "status": "FAIL",
                "detail": "empty Summary output",
            })
            continue

        first = summary_df.iloc[0]
        source_file = str(first.get("source_file", "")).strip()
        source_path = Path(source_file)
        if not source_path.exists():
            source_path = Path(str(first.get("input_path", "")).strip())

        try:
            metadata, expected_groups = parse_xml_independently(source_path)
        except Exception as exc:
            report_rows.append({
                "measurement": summary_path.name,
                "source_file": source_path.name,
                "status": "FAIL",
                "detail": f"independent XML parse failed: {exc}",
            })
            continue

        measurement_metadata_mismatches = 0
        for key, expected_value in metadata.items():
            if not equal_value(expected_value, first.get(key), args.tolerance):
                measurement_metadata_mismatches += 1

        measurement_row_mismatches = 0
        measurement_field_mismatches = 0
        example_messages: list[str] = []

        for group in ("Summary", "Points", "Sections", "Gates"):
            if group == "Summary":
                observed = summary_df
            else:
                group_path = output_root / group / summary_path.name.replace("_Summary_", f"_{group}_")
                observed = pd.read_csv(group_path, dtype=str, encoding="utf-8-sig")

            totals[group] += len(observed)
            row_bad, field_bad, examples = compare_group(
                expected_groups[group],
                observed,
                tolerance=args.tolerance,
            )
            measurement_row_mismatches += row_bad
            measurement_field_mismatches += field_bad
            if examples and len(example_messages) < 10:
                example_messages.extend(f"{group}: {item}" for item in examples[: 10 - len(example_messages)])

        metadata_mismatches += measurement_metadata_mismatches
        total_row_count_mismatches += measurement_row_mismatches
        total_field_mismatches += measurement_field_mismatches

        passed = (
            measurement_metadata_mismatches == 0
            and measurement_row_mismatches == 0
            and measurement_field_mismatches == 0
        )

        report_rows.append({
            "measurement": summary_path.name,
            "source_file": source_path.name,
            "station_id": metadata["station_id"],
            "metadata_mismatches": measurement_metadata_mismatches,
            "row_count_mismatches": measurement_row_mismatches,
            "field_mismatches": measurement_field_mismatches,
            "status": "PASS" if passed else "FAIL",
            "detail": " | ".join(example_messages),
        })

    report = pd.DataFrame(report_rows)
    checks_dir = runs_root / "_checks"
    checks_dir.mkdir(parents=True, exist_ok=True)
    report_path = checks_dir / "nivus_ingest_acceptance.csv"
    report.to_csv(report_path, index=False, encoding="utf-8-sig")

    n_pass = int((report["status"] == "PASS").sum()) if not report.empty else 0
    n_fail = int((report["status"] == "FAIL").sum()) if not report.empty else 0

    print("Aforix Nivus real-data acceptance")
    print("=" * 36)
    print(f"Run: {run_dir}")
    print(f"Measurements checked: {len(report)}")
    print(f"PASS: {n_pass}")
    print(f"FAIL: {n_fail}")
    print(f"Summary rows : {totals['Summary']}")
    print(f"Points rows  : {totals['Points']}")
    print(f"Sections rows: {totals['Sections']}")
    print(f"Gates rows   : {totals['Gates']}")
    print(f"Metadata mismatches : {metadata_mismatches}")
    print(f"Row-count mismatches: {total_row_count_mismatches}")
    print(f"Field mismatches    : {total_field_mismatches}")
    print(f"Report: {report_path}")

    if n_fail:
        print("")
        print("Failed measurements:")
        print(
            report.loc[
                report["status"] == "FAIL",
                [
                    "source_file",
                    "station_id",
                    "metadata_mismatches",
                    "row_count_mismatches",
                    "field_mismatches",
                    "detail",
                ],
            ].to_string(index=False)
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
