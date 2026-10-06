from __future__ import annotations

from aforix.analysis.section_profiles.cli import _normalize_point as cli_normalize_point
from aforix.analysis.section_profiles.interactive import _normalize_point as interactive_normalize_point


def test_section_profiles_cli_preserves_authoritative_station_ids():
    assert cli_normalize_point("7001") == "7001"
    assert cli_normalize_point("7071") == "7071"
    assert cli_normalize_point("P71") == "P71"


def test_section_profiles_interactive_preserves_authoritative_station_ids():
    assert interactive_normalize_point("7001") == "7001"
    assert interactive_normalize_point("7071") == "7071"
    assert interactive_normalize_point("P71") == "P71"
