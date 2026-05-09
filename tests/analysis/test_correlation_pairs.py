import pytest

from aforix.analysis.correlation.pairs import (
    PairValidationError,
    parse_pairs,
    validate_pair_selection,
)


def test_parse_pairs_accepts_bracketed_pairs() -> None:
    assert parse_pairs("[1 44] [8 117]") == [("1", "44"), ("8", "117")]


def test_parse_pairs_accepts_commas_inside_pair() -> None:
    assert parse_pairs("[1,44] [8,117]") == [("1", "44"), ("8", "117")]


def test_parse_pairs_empty_returns_empty_list() -> None:
    assert parse_pairs(None) == []
    assert parse_pairs("") == []


def test_parse_pairs_rejects_unbracketed_format() -> None:
    with pytest.raises(PairValidationError):
        parse_pairs("1,44;8,117")


def test_parse_pairs_rejects_pair_with_too_many_values() -> None:
    with pytest.raises(PairValidationError):
        parse_pairs("[1 44 55]")


def test_validate_pair_selection_rejects_all_pairs_with_pairs() -> None:
    with pytest.raises(PairValidationError):
        validate_pair_selection(
            correlation_type="gauges_vs_stations",
            pairs="[1 44]",
            all_pairs=True,
        )


def test_validate_pair_selection_requires_pairs_for_model_vs_stations() -> None:
    with pytest.raises(PairValidationError):
        validate_pair_selection(
            correlation_type="model_vs_stations",
            pairs=None,
            all_pairs=False,
        )


def test_validate_pair_selection_allows_model_vs_stations_all_pairs() -> None:
    validate_pair_selection(
        correlation_type="model_vs_stations",
        pairs=None,
        all_pairs=True,
    )
