from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

import aforix.export.sih.ive_integration as integration
from aforix.analysis.uncertainty.calculator import IVEParameters


@pytest.mark.parametrize(
    "parameters",
    [
        None,
        IVEParameters(
            systematic_relative=0.025,
            width_relative_per_vertical=0.012,
            minimum_depth_sd_m=0.02,
        ),
    ],
    ids=["defaults", "custom"],
)
def test_ive_report_passes_parameters_to_calculator_and_excel(
    tmp_path, parameters
):
    points = pd.DataFrame({
        "distance_m": [0.0, 0.5, 1.0],
        "depth_m": [0.0, 0.2, 0.0],
        "velocity_mean_m_s": [0.0, 0.3, 0.0],
        "width_m": [1.0, 1.0, 1.0],
    })

    measurement = pd.Series({
        "station_id": "7003",
        "measurement_date": "20260122",
        "measurement_time": "115000",
    })

    output = tmp_path / "report.xlsx"
    calculated_result = object()

    with (
        patch.object(
            integration,
            "load_ive_points",
            return_value=points,
        ),
        patch.object(
            integration,
            "calculate_ive",
            return_value=calculated_result,
        ) as calculate,
        patch.object(
            integration,
            "write_ive_excel_report",
            return_value=output,
        ) as write_report,
    ):
        returned = integration.write_sih_ive_report(
            normalized_root=tmp_path,
            output_root=tmp_path,
            instrument="molinete",
            measurement=measurement,
            parameters=parameters,
        )

    calculate.assert_called_once()
    write_report.assert_called_once()

    calculation_parameters = calculate.call_args.kwargs["parameters"]
    report_parameters = write_report.call_args.kwargs["parameters"]

    if parameters is None:
        assert isinstance(calculation_parameters, IVEParameters)
        assert calculation_parameters.left_bank_mode == "preserve_depth"
        assert calculation_parameters.right_bank_mode == "preserve_depth"
        assert report_parameters == calculation_parameters
    else:
        assert calculation_parameters is parameters
        assert report_parameters is parameters

    assert write_report.call_args.kwargs["result"] is calculated_result
    assert returned == output
