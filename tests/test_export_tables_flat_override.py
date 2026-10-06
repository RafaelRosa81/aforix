from __future__ import annotations

from pathlib import Path

import pandas as pd

from aforix.export.tables.runner import ExportRequest, run_export_tables


def test_flat_override_disables_grouping_and_pivot_semantics(tmp_path: Path):
    normalized_root = tmp_path / "database" / "normalized"
    normalized_root.mkdir(parents=True)

    pd.DataFrame(
        [
            {
                "instrument": "flowtracker",
                "station_id": "7071",
                "station_name": "RIO_SJOSE_C_OMBU",
                "measurement_date": "20260120",
                "measurement_time": "141519",
                "q_total_ls": 100.0,
            },
            {
                "instrument": "flowtracker",
                "station_id": "7071",
                "station_name": "RIO_SJOSE_C_OMBU",
                "measurement_date": "20260121",
                "measurement_time": "101500",
                "q_total_ls": 120.0,
            },
        ]
    ).to_csv(normalized_root / "Summary.csv", index=False)

    config = {
        "__repo_root__": str(tmp_path),
        "export": {
            "tables": {
                "input_dir": "database/normalized",
                "output_dir": "outputs/tables",
            }
        },
    }

    result = run_export_tables(
        config,
        ExportRequest(
            table="Summary",
            instrument="flowtracker",
            parameters=("q_total_ls",),
            early_date="20260120",
            late_date="20260121",
            grouping="daily",
            fmt="csv",
            pivot=False,
            aggregation="mean",
        ),
    )

    exported = pd.read_csv(result.output_file, dtype=str)
    metadata = result.metadata_file.read_text(encoding="utf-8")

    assert list(exported.columns) == [
        "instrument",
        "station_id",
        "station_name",
        "measurement_date",
        "measurement_time",
        "q_total_ls",
    ]
    assert len(exported) == 2
    assert result.output_file.name == "summary_20260120-20260121_flat_ft.csv"
    assert "grouping: none" in metadata
    assert "pivot: False" in metadata
    assert "column_order: flat" in metadata
