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
from aforix.analysis.correlation.io.gauges import _finalize_rows
from aforix.analysis.correlation.io.model import load_model_data
from aforix.analysis.correlation.workflows.gauges_vs_stations import _station_sort_key as gauge_station_sort_key


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

def test_correlation_gauge_finalize_preserves_prefixed_station_ids():
    rows = pd.DataFrame(
        [
            {
                "point": "P71",
                "date": pd.Timestamp("2026-01-20"),
                "source": "FT",
                "q_gauge_l/s": 12.0,
            },
            {
                "point": "7071",
                "date": pd.Timestamp("2026-01-20"),
                "source": "FT",
                "q_gauge_l/s": 34.0,
            },
        ]
    )

    result = _finalize_rows(rows, ["FT"], {"FT": "FT"})

    assert set(result) == {"P71", "7071"}
    assert result["P71"]["q_gauge_l/s"].tolist() == [12.0]
    assert result["7071"]["q_gauge_l/s"].tolist() == [34.0]

def test_gauges_vs_stations_all_pairs_sort_accepts_prefixed_station_ids():
    assert sorted(["P71", "7071"], key=gauge_station_sort_key) == ["7071", "P71"]

def test_model_filename_p_prefix_is_not_measured_station_namespace(tmp_path):
    model_file = tmp_path / "P71_model_data.csv"
    pd.DataFrame(
        {
            "date": ["2026-01-20"],
            "q(m3/s)": [0.123],
        }
    ).to_csv(model_file, index=False)

    model_data = load_model_data(tmp_path)

    assert set(model_data) == {"71"}
    assert "P71" not in model_data
