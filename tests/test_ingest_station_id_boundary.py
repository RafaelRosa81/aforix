from pathlib import Path

from aforix.ingest.adapters.molinete_excel import MolineteExcelAdapter
from aforix.ingest.metadata import clean_station_id
from aforix.ingest.metadata_policy import (
    MetadataExtractionContext,
    extract_metadata_field,
)


def _numeric_station_policy():
    return {
        "strategy": "first_non_empty",
        "sources": [{"type": "raw_field", "key": "station_id"}],
        "transforms": [
            "strip",
            "uppercase",
            {"name": "remove_prefix", "value": "P"},
            "digits_only",
        ],
        "normalize": {"digits_only": True},
    }


def _preserve_station_policy():
    return {
        "strategy": "first_non_empty",
        "sources": [{"type": "raw_field", "key": "station_id"}],
        "transforms": ["strip"],
    }


def _extract(value: str, policy: dict | None = None) -> str:
    context = MetadataExtractionContext(
        raw_fields={"station_id": value},
        source_path=Path("dummy.dat"),
    )
    return extract_metadata_field(
        "station_id",
        policy or _numeric_station_policy(),
        context=context,
    )


def test_clean_station_id_preserves_prefixed_id():
    assert clean_station_id("P71") == "P71"


def test_clean_station_id_preserves_numeric_id():
    assert clean_station_id("7071") == "7071"
    assert clean_station_id("71") == "71"
    assert clean_station_id("70101") == "70101"


def test_clean_station_id_unwraps_flowtracker_file_name_without_renumbering():
    assert clean_station_id("P71.TXT.WAD") == "P71"
    assert clean_station_id("70101.TXT.WAD") == "70101"


def test_metadata_policy_applies_only_configured_station_transforms():
    assert _extract("P71") == "71"
    assert _extract("7071") == "7071"
    assert _extract("70101") == "70101"


def test_metadata_policy_can_preserve_station_id_verbatim():
    policy = _preserve_station_policy()
    assert _extract("P71", policy) == "P71"
    assert _extract("7071", policy) == "7071"
    assert _extract("A15", policy) == "A15"


def test_molinete_adapter_preserves_raw_station_id():
    clean = MolineteExcelAdapter._clean_station_id

    assert clean(7008) == "7008"
    assert clean(7071) == "7071"
    assert clean(7101) == "7101"
    assert clean(7008.0) == "7008"
    assert clean("7008") == "7008"
    assert clean("A15") == "A15"


def test_molinete_raw_station_id_survives_numeric_policy():
    # A numeric station ID already read from the workbook must not acquire a
    # synthetic P prefix at the adapter boundary. The configured policy may
    # still apply its own transformations afterwards.
    assert _extract("7071") == "7071"
    assert _extract("7101") == "7101"
