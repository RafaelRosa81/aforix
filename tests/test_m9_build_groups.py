from __future__ import annotations

import pandas as pd

from aforix.groups.build import _deduplicate_csv_paths


def test_m9_build_groups_keeps_same_time_transects_from_different_mat_files(tmp_path):
    run_root = tmp_path / "runs" / "ingest_m9" / "20261016_080000"
    summary_dir = run_root / "outputs" / "raw_canonical" / "m9" / "Summary"
    summary_dir.mkdir(parents=True)
    sources = ["first.mat", "second.mat"]
    csv_paths = []
    for index, source in enumerate(sources):
        path = summary_dir / f"7071_Summary_20260120_141519_{index}.csv"
        pd.DataFrame(
            [
                {
                    "station_id": "7071",
                    "measurement_date": "20260120",
                    "measurement_time": "141519",
                    "instrument": "m9",
                    "source_file": source,
                    "q_total_m3s": index + 1,
                }
            ]
        ).to_csv(path, index=False)
        csv_paths.append(path)

    selected = _deduplicate_csv_paths(
        csv_paths,
        cfg={
            "build_groups": {
                "deduplicate": True,
                "deduplicate_by": [
                    "instrument",
                    "station_id",
                    "measurement_date",
                    "measurement_time",
                    "group",
                ],
            }
        },
        instrument="m9",
        group="Summary",
        column_aliases={},
    )

    assert set(selected) == set(csv_paths)
