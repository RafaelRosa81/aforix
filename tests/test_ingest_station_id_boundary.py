from pathlib import Path

from aforix.ingest.metadata import clean_station_id
from aforix.ingest.metadata_policy import (
    MetadataExtractionContext,
    extract_metadata_field,
)


def _legacy_policy():
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


def _extract(value: str) -> str:
    context = MetadataExtractionContext(
        raw_fields={"station_id": value},
        source_path=Path("dummy.dat"),
    )
    return extract_metadata_field(
        "station_id",
        _legacy_policy(),
        context=context,
    )


def test_clean_station_id_canonicalizes_legacy_p_code():
    assert clean_station_id("P71") == "7071"


def test_clean_station_id_preserves_canonical_numeric_id():
    assert clean_station_id("7071") == "7071"


def test_clean_station_id_preserves_unrelated_numeric_id():
    assert clean_station_id("71") == "71"


def test_clean_station_id_unwraps_flowtracker_file_name_before_canonicalizing():
    assert clean_station_id("P71.TXT.WAD") == "7071"


def test_metadata_policy_canonicalizes_before_legacy_prefix_removal():
    assert _extract("P71") == "7071"
    assert _extract("7071") == "7071"
    assert _extract("P71.TXT.WAD") == "7071"


def test_metadata_policy_recovers_prefixed_canonical_value_from_molinete_adapter():
    # Current Molinete adapter can emit P7071 when the workbook already stores
    # 7071. The ingest boundary must still preserve the intended canonical ID.
    assert _extract("P7071") == "7071"
