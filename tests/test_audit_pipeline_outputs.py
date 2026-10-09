from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


def _load_audit_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "audit_pipeline_outputs.py"
    spec = importlib.util.spec_from_file_location("audit_pipeline_outputs", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load audit script: {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


audit_module = _load_audit_module()
audit_duplicates = audit_module.audit_duplicates
audit_points_completeness = audit_module.audit_points_completeness
audit_points_width_consistency = audit_module.audit_points_width_consistency
audit_hydraulic_consistency = audit_module.audit_hydraulic_consistency


MEASUREMENT = {
    "instrument": "flowtracker",
    "station_id": "7005",
    "measurement_date": "20251217",
    "measurement_time": "093425",
}


def test_audit_duplicates_flowtracker_distinct_percent_depth_is_not_duplicate(tmp_path):
    points_dir = tmp_path / "normalized" / "flowtracker" / "Points"
    points_dir.mkdir(parents=True)

    pd.DataFrame(
        [
            {
                **MEASUREMENT,
                "point_index": "16",
                "percent_depth": "0.2",
                "distance_m": "3.0",
                "q_m3s": "0.01",
            },
            {
                **MEASUREMENT,
                "point_index": "16",
                "percent_depth": "0.8",
                "distance_m": "3.0",
                "q_m3s": "0.02",
            },
        ]
    ).to_csv(points_dir / "7005_Points_20251217_093425.csv", index=False)

    report = audit_duplicates(tmp_path / "normalized")

    assert len(report) == 1
    assert report.loc[0, "instrument"] == "flowtracker"
    assert report.loc[0, "group"] == "Points"
    assert report.loc[0, "status"] == "ok"
    assert report.loc[0, "n_duplicated_rows"] == 0



def test_audit_duplicates_flowtracker_same_percent_depth_is_duplicate(tmp_path):
    points_dir = tmp_path / "normalized" / "flowtracker" / "Points"
    points_dir.mkdir(parents=True)

    row = {
        **MEASUREMENT,
        "point_index": "16",
        "percent_depth": "0.2",
        "distance_m": "3.0",
        "q_m3s": "0.01",
    }
    pd.DataFrame([row, row]).to_csv(
        points_dir / "7005_Points_20251217_093425.csv",
        index=False,
    )

    report = audit_duplicates(tmp_path / "normalized")

    assert len(report) == 1
    assert report.loc[0, "status"] == "duplicates"
    assert report.loc[0, "n_duplicated_rows"] == 2
    assert report.loc[0, "n_duplicate_keys"] == 1

def test_audit_duplicates_percent_depth_key_is_instrument_name_agnostic(tmp_path):
    points_dir = tmp_path / "normalized" / "flowtracker_alias" / "Points"
    points_dir.mkdir(parents=True)

    measurement = {
        **MEASUREMENT,
        "instrument": "FT",
    }
    pd.DataFrame(
        [
            {
                **measurement,
                "point_index": "16",
                "percent_depth": "0.2",
                "distance_m": "3.0",
                "q_m3s": "0.01",
            },
            {
                **measurement,
                "point_index": "16",
                "percent_depth": "0.8",
                "distance_m": "3.0",
                "q_m3s": "0.02",
            },
        ]
    ).to_csv(points_dir / "7005_Points_20251217_093425.csv", index=False)

    report = audit_duplicates(tmp_path / "normalized")

    assert len(report) == 1
    assert report.loc[0, "status"] == "ok"
    assert report.loc[0, "n_duplicated_rows"] == 0
    assert "percent_depth" in report.loc[0, "key_columns_used"].split(";")


def test_audit_points_completeness_flags_all_missing_velocity(tmp_path):
    points_dir = tmp_path / "normalized" / "molinete" / "Points"
    points_dir.mkdir(parents=True)

    pd.DataFrame(
        [
            {
                **MEASUREMENT,
                "instrument": "molinete",
                "point_label": "1",
                "velocity_mean_m_s": None,
                "percent_q": "40",
                "width_m": "14.8",
            },
            {
                **MEASUREMENT,
                "instrument": "molinete",
                "point_label": "2",
                "velocity_mean_m_s": None,
                "percent_q": "60",
                "width_m": "14.8",
            },
        ]
    ).to_csv(points_dir / "7005_Points.csv", index=False)

    report = audit_points_completeness(tmp_path / "normalized")
    row = report[
        (report["instrument"] == "molinete")
        & (report["column"] == "velocity_mean_m_s")
    ].iloc[0]

    assert row["status"] == "all_missing"
    assert row["n_populated"] == 0


def test_audit_points_width_requires_same_summary_width_on_every_row(tmp_path):
    root = tmp_path / "normalized"
    instrument_dir = root / "flowtracker"
    points_dir = instrument_dir / "Points"
    points_dir.mkdir(parents=True)

    summary = {
        **MEASUREMENT,
        "width_total_m": "14.7",
    }
    pd.DataFrame([summary]).to_csv(instrument_dir / "Summary.csv", index=False)
    pd.DataFrame(
        [
            {**MEASUREMENT, "width_m": "14.7"},
            {**MEASUREMENT, "width_m": "14.6"},
        ]
    ).to_csv(points_dir / "7005_Points.csv", index=False)

    report = audit_points_width_consistency(root)
    assert len(report) == 1
    assert report.loc[0, "status"] == "multiple_point_widths"


def test_audit_hydraulic_consistency_checks_percent_q_sums_to_100(tmp_path):
    root = tmp_path / "normalized"
    instrument_dir = root / "flowtracker"
    points_dir = instrument_dir / "Points"
    points_dir.mkdir(parents=True)

    pd.DataFrame(
        [
            {
                **MEASUREMENT,
                "q_total_m3s": "0.03",
                "q_total_ls": "30",
                "area_total_m2": "1.0",
            }
        ]
    ).to_csv(instrument_dir / "Summary.csv", index=False)
    pd.DataFrame(
        [
            {
                **MEASUREMENT,
                "point_index": "1",
                "distance_m": "1",
                "depth_m": "1",
                "area_m2": "0.5",
                "q_m3s": "0.01",
                "q_ls": "10",
                "percent_q": "40",
            },
            {
                **MEASUREMENT,
                "point_index": "2",
                "distance_m": "2",
                "depth_m": "1",
                "area_m2": "0.5",
                "q_m3s": "0.02",
                "q_ls": "20",
                "percent_q": "50",
            },
        ]
    ).to_csv(points_dir / "7005_Points.csv", index=False)

    report = audit_hydraulic_consistency(root)
    percent_row = report[report["check"] == "percent_q"].iloc[0]

    assert percent_row["points_sum"] == 90.0
    assert percent_row["status"] == "mismatch"


def test_width_audit_loads_file_group_summaries(tmp_path):
    root = tmp_path / "normalized"
    instrument_dir = root / "molinete"
    summary_dir = instrument_dir / "Summary"
    points_dir = instrument_dir / "Points"
    summary_dir.mkdir(parents=True)
    points_dir.mkdir(parents=True)

    pd.DataFrame(
        [
            {
                **MEASUREMENT,
                "width_total_m": "14.8",
            }
        ]
    ).to_csv(summary_dir / "7005_Summary.csv", index=False)

    pd.DataFrame(
        [
            {
                **MEASUREMENT,
                "width_m": "14.7",
            },
            {
                **MEASUREMENT,
                "width_m": "14.7",
            },
        ]
    ).to_csv(points_dir / "7005_Points.csv", index=False)

    report = audit_points_width_consistency(root)

    assert len(report) == 1
    assert report.loc[0, "status"] == "width_mismatch"
    assert report.loc[0, "summary_width_total_m"] == 14.8
    assert report.loc[0, "points_width_m"] == 14.7


def test_audit_points_completeness_flags_partial_percent_q(tmp_path):
    points_dir = tmp_path / "normalized" / "flowtracker" / "Points"
    points_dir.mkdir(parents=True)

    pd.DataFrame(
        [
            {**MEASUREMENT, "percent_q": "40", "point_label": "1", "velocity_mean_m_s": "0.1", "width_m": "10"},
            {**MEASUREMENT, "percent_q": "60", "point_label": "2", "velocity_mean_m_s": "0.2", "width_m": "10"},
            {**MEASUREMENT, "percent_q": None, "point_label": "3", "velocity_mean_m_s": "0.3", "width_m": "10"},
        ]
    ).to_csv(points_dir / "7005_Points.csv", index=False)

    report = audit_points_completeness(tmp_path / "normalized")
    row = report[
        (report["instrument"] == "flowtracker")
        & (report["column"] == "percent_q")
    ].iloc[0]

    assert row["status"] == "incomplete"
    assert row["n_populated"] == 2
    assert row["n_missing"] == 1


def test_width_audit_reports_missing_measurement_keys_instead_of_crashing(tmp_path):
    root = tmp_path / "normalized"
    instrument_dir = root / "flowtracker"
    points_dir = instrument_dir / "Points"
    points_dir.mkdir(parents=True)

    pd.DataFrame(
        [
            {
                "instrument": "flowtracker",
                "station_id": "7005",
                "measurement_date": "20260120",
                "width_total_m": "10.0",
            }
        ]
    ).to_csv(instrument_dir / "Summary.csv", index=False)

    pd.DataFrame(
        [
            {
                "instrument": "flowtracker",
                "station_id": "7005",
                "measurement_date": "20260120",
                "measurement_time": "141519",
                "width_m": "10.0",
            }
        ]
    ).to_csv(points_dir / "7005_Points.csv", index=False)

    report = audit_points_width_consistency(root)

    assert len(report) == 1
    assert report.loc[0, "status"] == "missing_key_columns"
    assert report.loc[0, "missing_summary_keys"] == "measurement_time"


def test_width_audit_flags_conflicting_summary_widths(tmp_path):
    root = tmp_path / "normalized"
    instrument_dir = root / "flowtracker"
    points_dir = instrument_dir / "Points"
    points_dir.mkdir(parents=True)

    pd.DataFrame(
        [
            {**MEASUREMENT, "width_total_m": "14.7"},
            {**MEASUREMENT, "width_total_m": "14.8"},
        ]
    ).to_csv(instrument_dir / "Summary.csv", index=False)

    pd.DataFrame(
        [
            {**MEASUREMENT, "width_m": "14.7"},
            {**MEASUREMENT, "width_m": "14.7"},
        ]
    ).to_csv(points_dir / "7005_Points.csv", index=False)

    report = audit_points_width_consistency(root)

    assert len(report) == 1
    assert report.loc[0, "status"] == "conflicting_summary_widths"
    assert report.loc[0, "summary_width_unique"] == 2



def test_zero_flow_percentages_are_not_applicable_in_both_audits(tmp_path):
    root = tmp_path / "normalized"
    instrument_dir = root / "nivus"
    instrument_dir.mkdir(parents=True)
    metadata = {**MEASUREMENT, "instrument": "nivus"}
    pd.DataFrame([{**metadata, "q_total_ls": 0, "q_total_m3s": 0}]).to_csv(
        instrument_dir / "Summary.csv", index=False,
    )
    pd.DataFrame([{**metadata, "point_index": i, "point_label": str(i),
                   "velocity_mean_m_s": 0, "q_ls": 0, "q_m3s": 0,
                   "percent_q": None, "width_m": 1} for i in (1, 2)]).to_csv(
        instrument_dir / "Points.csv", index=False,
    )
    hydraulic = audit_hydraulic_consistency(root)
    share = hydraulic.loc[hydraulic.check.eq("percent_q")].iloc[0]
    assert share.status == "not_applicable_zero_flow"
    assert pd.isna(share.summary_value)
    complete = audit_points_completeness(root)
    share = complete.loc[complete.column.eq("percent_q")].iloc[0]
    assert share.status == "not_applicable_zero_flow"
    assert share.n_not_applicable == 2
    assert share.n_missing == 0
    # A conflicting total must remove the exemption.
    pd.DataFrame([{**metadata, "q_total_ls": 1, "q_total_m3s": 0.001}]).to_csv(
        instrument_dir / "Summary.csv", index=False,
    )
    complete = audit_points_completeness(root)
    assert complete.loc[complete.column.eq("percent_q"), "status"].iloc[0] == "all_missing"
