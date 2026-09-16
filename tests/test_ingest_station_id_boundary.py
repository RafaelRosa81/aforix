from pathlib import Path

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


def test_molinete_prefixed_adapter_value_recovers_raw_numeric_station():
    # The current Molinete adapter prefixes numeric workbook values with P.
    # The example policy removes that adapter representation without applying
    # any 7000-namespace renumbering.
    assert _extract("P7071") == "7071"
    assert _extract("P101") == "101"
