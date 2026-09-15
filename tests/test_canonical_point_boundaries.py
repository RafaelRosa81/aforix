from __future__ import annotations

import pandas as pd
import pytest

from aforix.metadata import canonical_station_id
from aforix.batch.default_registry import _parse_points
from aforix.export.tables.runner import available_points, normalize_point_token


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
def test_canonical_station_id_legacy_and_canonical_are_equivalent(raw: str, expected: str) -> None:
    assert canonical_station_id(raw) == expected


def test_batch_point_parser_canonicalizes_legacy_and_preserves_canonical_ids() -> None:
    assert _parse_points("P1 P71 P101 7001 7071 7101") == [
        "7001",
        "7071",
        "7101",
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
def test_export_point_normalizer_uses_canonical_ids(raw: str, expected: str) -> None:
    assert normalize_point_token(raw) == expected


def test_export_available_points_collapses_legacy_and_canonical_aliases() -> None:
    df = pd.DataFrame({"station_id": ["P1", "7001", "P71", "7071", "P101", "7101"]})
    assert available_points(df) == ["7001", "7071", "7101"]
