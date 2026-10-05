from pathlib import Path

import pandas as pd
import pytest

from aforix.analysis.section_profiles.excel import write_excel


def test_section_profiles_rejects_unsupported_line_chart_type(tmp_path: Path):
    output = tmp_path / "profile.xlsx"

    sheets = [
        {
            "sheet_name": "7071_20260120_FT",
            "data": pd.DataFrame(
                {
                    "point_index": [1, 2, 3],
                    "distance_m": [0.0, 0.7, 1.4],
                    "depth_m": [0.01, 0.15, 0.25],
                }
            ),
            "summary": {
                "station_id": "7071",
                "measurement_date": "20260120",
                "measurement_time": "142300",
                "instrument": "flowtracker",
                "instrument_code": "FT",
                "n_rows": 3,
            },
        }
    ]

    with pytest.raises(ValueError, match="Unsupported section-profile chart type"):
        write_excel(
            output,
            sheets,
            x_axis="distance_m",
            y_axis="depth_m",
            chart_type="line",
        )

def test_main_config_advertises_only_supported_section_profile_chart_types():
    import yaml

    root = Path(__file__).resolve().parents[2]
    config = yaml.safe_load(
        (root / "configs" / "examples" / "main.yaml").read_text(encoding="utf-8")
    )

    chart_types = config["analysis"]["section_profiles"]["allowed"]["chart_types"]

    assert chart_types == ["scatter", "bar"]
