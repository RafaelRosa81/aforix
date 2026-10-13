from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from aforix.normalize.normalizer import normalize_table


ROOT = Path(__file__).resolve().parents[1]
POINTS_DIR = ROOT / "database/raw_canonical/molinete/Points"
CONFIG = ROOT / "configs/normalization/molinete.yaml"


def test_molinete_real_vertical_velocity_reconstruction():
    files = sorted(POINTS_DIR.glob("*.csv"))

    if not files:
        pytest.skip(
            "No hay datos canónicos locales de Molinete; "
            "este test requiere los 13 archivos de referencia."
        )

    if len(files) != 13:
        pytest.fail(
            f"Se esperaban 13 archivos canónicos de referencia; encontrados: {len(files)}"
        )

    with CONFIG.open(encoding="utf-8") as stream:
        spec = yaml.safe_load(stream)["tables"]["Points"]

    frames = []

    for path in files:
        raw = pd.read_csv(path, dtype=str)
        normalized = normalize_table(raw, spec)

        assert len(normalized) == len(raw), path.name

        normalized["validation_file"] = path.name
        frames.append(normalized)

    data = pd.concat(frames, ignore_index=True)

    assert len(data) == 290

    columns = [
        "n_points",
        "angle_hor_deg",
        "velocity_mean_m_s",
        "vel_point_1_ms",
        "vel_point_2_ms",
    ]

    for column in columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    n = data["n_points"]
    angle = data["angle_hor_deg"]
    v1 = data["vel_point_1_ms"]
    v2 = data["vel_point_2_ms"]
    actual = data["velocity_mean_m_s"]

    one_with_angle = (n == 1) & angle.notna()
    one_without_angle = (n == 1) & angle.isna()
    two_points = n == 2
    missing_count = n.isna()

    assert int(one_with_angle.sum()) == 51
    assert int(one_without_angle.sum()) == 219
    assert int(two_points.sum()) == 18
    assert int(missing_count.sum()) == 2

    expected = pd.Series(np.nan, index=data.index, dtype=float)

    expected.loc[one_with_angle] = (
        v1 * np.cos(np.deg2rad(angle))
    ).loc[one_with_angle]

    expected.loc[one_without_angle] = v1.loc[one_without_angle]

    expected.loc[two_points] = (
        (v1 + v2) / 2
    ).loc[two_points]

    evaluated = ~missing_count

    assert int(evaluated.sum()) == 288
    assert expected.loc[evaluated].notna().all()

    np.testing.assert_allclose(
        actual.loc[evaluated].to_numpy(dtype=float),
        expected.loc[evaluated].to_numpy(dtype=float),
        rtol=0,
        atol=1e-12,
    )

    # Los dos registros sin n_points no deben interpretarse
    # como observaciones instrumentales disponibles.
    missing = data.loc[missing_count]

    assert set(missing["validation_file"]) == {
        "7008_Points_20260226_100000.csv"
    }
    assert set(missing["point_index"].astype(int)) == {3, 27}
    assert (missing["velocity_mean_m_s"] == 0).all()
