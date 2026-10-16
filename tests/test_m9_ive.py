import numpy as np

from aforix.analysis.quality.ive import calculate_ive_profile


def test_ive_adaptation_calculates_relative_and_absolute_uncertainty():
    x = np.arange(12, dtype=float)
    depth = np.array([0.0, 0.2, 0.6, 1.0, 1.2, 1.1, 0.9, 0.7, 0.5, 0.3, 0.1, 0.0])
    velocity = np.array([0.0, 0.10, 0.12, 0.15, 0.18, 0.19, 0.17, 0.14, 0.12, 0.10, 0.08, 0.0])

    result = calculate_ive_profile(x, depth, velocity)

    assert result["status"] == "calculated"
    assert result["profile_sample_count"] == 12
    assert result["q_midsection_m3s"] > 0
    assert 0 < result["relative_uncertainty"] < 1
    assert np.isclose(
        result["absolute_error_m3s"],
        result["q_midsection_m3s"] * result["relative_uncertainty"],
    )
    assert result["quality"] in {"Excelente", "Buena", "Regular", "Mala"}


def test_ive_adaptation_marks_profiles_with_fewer_than_ten_rows_not_applicable():
    result = calculate_ive_profile(
        np.arange(9, dtype=float),
        np.ones(9),
        np.full(9, 0.1),
    )

    assert result["status"] == "not_applicable"
    assert result["reason"] == "IVE no aplicable: menos de 10 verticales/muestras."
