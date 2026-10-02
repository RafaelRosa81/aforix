from __future__ import annotations

import pandas as pd
import pytest

from aforix.metadata import canonical_station_id
from aforix.batch.default_registry import _parse_points
from aforix.export.tables.runner import available_points, normalize_point_token
from aforix.analysis.correlation.workflows.model_vs_stations import _normalize_model_point_id


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("P1", "P1"),
        ("P71", "P71"),
        ("P101", "P101"),
        ("7001", "7001"),
        ("7071", "7071"),
        ("7101", "7101"),
    ],
)
def test_canonical_station_id_preserves_station_namespace(raw: str, expected: str) -> None:
    assert canonical_station_id(raw) == expected


@pytest.mark.parametrize("raw", ["1", "44", "71", "101", "117"])
def test_canonical_station_id_preserves_unprefixed_external_numeric_ids(raw: str) -> None:
    """Bare numeric IDs are not enough evidence that an ID belongs to Aforix."""
    assert canonical_station_id(raw) == raw


def test_batch_point_parser_preserves_distinct_station_namespaces() -> None:
    assert _parse_points("P1 P71 P101 7001 7071 7101") == [
        "P1",
        "P71",
        "P101",
        "7001",
        "7071",
        "7101",
    ]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("P1", "7001"),
        ("P71", "7071"),
        ("P101", "7101"),
        ("7001", "7001"),
        ("7071", "7071"),
        ("7101", "7101"),
    ],
)
def test_export_point_normalizer_preserves_station_namespace(raw: str, expected: str) -> None:
    assert normalize_point_token(raw) == expected


def test_export_available_points_keeps_distinct_station_namespaces() -> None:
    df = pd.DataFrame({"station_id": ["P1", "7001", "P71", "7071", "P101", "7101"]})
    assert available_points(df) == ["7001", "7071", "7101", "P1", "P101", "P71"]


def test_model_point_namespace_accepts_pm_and_internal_bare_ids() -> None:
    assert _normalize_model_point_id("Pm71") == "71"
    assert _normalize_model_point_id("71") == "71"


def test_model_point_namespace_rejects_measured_aforix_point() -> None:
    with pytest.raises(ValueError, match="Expected a model point id"):
        _normalize_model_point_id("P71")
