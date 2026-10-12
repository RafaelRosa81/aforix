"""Regression tests against cached values of Template_incertidumbre_aforos_IVE3.xlsx.

Place this file under tests/analysis/uncertainty/ and the reference XLSX at
repo root (or set IVE_REFERENCE_XLSX to its absolute path).
Run: pytest -q tests/analysis/uncertainty/test_ive_excel_regression.py
"""
from __future__ import annotations

import os
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import pytest

from aforix.analysis.uncertainty.calculator import IVEPoint, calculate_ive

REFERENCE = Path(os.environ.get("IVE_REFERENCE_XLSX", "Template_incertidumbre_aforos_IVE3.xlsx"))
NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _cached_cells(zf: ZipFile, sheet_number: int) -> dict[str, str]:
    root = ET.fromstring(zf.read(f"xl/worksheets/sheet{sheet_number}.xml"))
    result = {}
    for cell in root.findall(".//x:sheetData/x:row/x:c", NS):
        value = cell.find("x:v", NS)
        if value is not None and value.text is not None:
            result[cell.attrib["r"]] = value.text
    return result


@pytest.mark.parametrize("case", [1, 2, 3])
def test_ive_matches_ive3_template(case):
    assert REFERENCE.is_file(), f"Falta el Excel de referencia: {REFERENCE.resolve()}"
    with ZipFile(REFERENCE) as zf:
        points_sheet = _cached_cells(zf, case + 6)
        uncertainty_sheet = _cached_cells(zf, case + 3)

    point_count = int(float(points_sheet["B6"]))
    width_m = float(points_sheet["B7"])
    points = [
        IVEPoint(
            distance_m=float(points_sheet[f"W{row}"]),
            depth_m=float(points_sheet[f"X{row}"]),
            velocity_m_s=float(points_sheet[f"Y{row}"]),
        )
        for row in range(16, 16 + point_count)
    ]

    result = calculate_ive(points=points, width_m=width_m)
    expected_q = float(uncertainty_sheet["E6"])
    expected_sd_depth = float(uncertainty_sheet["E9"])
    expected_sd_velocity = float(uncertainty_sheet["E11"])
    expected_relative_pct = 100 * float(uncertainty_sheet["E17"])
    expected_absolute = float(uncertainty_sheet["E18"])

    # Comparar los componentes por separado: un fallo revela dónde divergen
    # el algoritmo Python y las fórmulas de la plantilla.
    assert result.vertical_count == int(float(uncertainty_sheet["E7"])), "Conteo de verticales"
    assert result.q_mid_m3s == pytest.approx(expected_q, rel=1e-9, abs=1e-12), "Caudal mid-section"
    assert result.sd_depth_ive_m == pytest.approx(expected_sd_depth, rel=1e-9, abs=1e-12), "s_d IVE"
    assert result.sd_velocity_ive_m_s == pytest.approx(expected_sd_velocity, rel=1e-9, abs=1e-12), "s_v IVE"
    assert result.relative_uncertainty_pct == pytest.approx(expected_relative_pct, rel=1e-9, abs=1e-9), "Incertidumbre relativa"
    assert result.absolute_uncertainty_m3s == pytest.approx(expected_absolute, rel=1e-9, abs=1e-12), "Error absoluto"
