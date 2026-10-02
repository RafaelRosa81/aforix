from __future__ import annotations

import pandas as pd

from aforix.metadata import canonical_station_id
from aforix.batch.default_registry import _parse_points as batch_parse_points
from aforix.export.tables.runner import available_points, normalize_point_token
from aforix.external.manual_stage.convert import _normalize_station_id as manual_stage_station_id
from aforix.analysis.stage_discharge.inputs import _normalize_station_id as stage_discharge_station_id
from aforix.analysis.section_profiles.inputs import _norm_station as section_profile_station_id
from aforix.analysis.quality.runner import _normalize_point as quality_station_id
from aforix.analysis.correlation.workflows.model_vs_stations import _normalize_model_point_id


def test_canonical_station_id_is_representation_only_not_semantic_mapping():
    assert canonical_station_id("70101") == "70101"
    assert canonical_station_id("701150") == "701150"
    assert canonical_station_id("701190") == "701190"

    # A prefixed identifier is a different identifier/namespace. It must not
    # be silently interpreted as a station in the 7000 namespace.
    assert canonical_station_id("P71") == "P71"
    assert canonical_station_id("p71") == "P71"
    assert canonical_station_id("P101") == "P101"
    assert canonical_station_id("P71") != canonical_station_id("7071")

    # Representation cleanup is still allowed.
    assert canonical_station_id(" 7071 ") == "7071"
    assert canonical_station_id("7071.0") == "7071"


def test_export_table_point_filters_do_not_alias_p_codes_to_numeric_station_ids():
    assert normalize_point_token("P71") == "P71"
    assert normalize_point_token("7071") == "7071"

    df = pd.DataFrame({"station_id": ["P71", "7071", "701150"]})
    assert available_points(df) == ["7071", "701150", "P71"]


def test_batch_point_parser_keeps_distinct_station_namespaces():
    assert batch_parse_points("P71 7071 P101 7101") == [
        "P71",
        "7071",
        "P101",
        "7101",
    ]


def test_manual_stage_conversion_does_not_invent_p_prefix_or_renumber():
    assert manual_stage_station_id("7071") == "7071"
    assert manual_stage_station_id("701150") == "701150"
    assert manual_stage_station_id("P71") == "P71"


def test_analysis_input_boundaries_preserve_authoritative_station_id():
    for normalizer in (
        stage_discharge_station_id,
        section_profile_station_id,
        quality_station_id,
    ):
        assert normalizer("7071") == "7071"
        assert normalizer("701150") == "701150"
        assert normalizer("P71") == "P71"


def test_model_point_namespace_remains_separate_from_measured_station_ids():
    assert _normalize_model_point_id("Pm71") == "71"
    assert _normalize_model_point_id("71") == "71"
