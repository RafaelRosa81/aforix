from __future__ import annotations

import pytest

from aforix.external import cli


@pytest.mark.parametrize(
    ("command_name", "source_name", "default_raw", "default_normalized", "converter_name"),
    [
        (
            "convert_model",
            "model",
            "database/external/raw/model",
            "database/external/normalized/model",
            "run_model_conversion",
        ),
        (
            "convert_dinagua",
            "dinagua",
            "database/external/raw/dinagua",
            "database/external/normalized/dinagua",
            "run_dinagua_conversion",
        ),
        (
            "convert_manual_stage",
            "manual_stage",
            "data/external/manual_stage",
            "database/external/normalized/manual_stage",
            "run_manual_stage_conversion",
        ),
    ],
)
def test_external_converters_resolve_paths_from_config_root(
    tmp_path,
    monkeypatch,
    command_name,
    source_name,
    default_raw,
    default_normalized,
    converter_name,
):
    config_dir = tmp_path / "job"
    config_dir.mkdir()
    config_path = config_dir / "main.yaml"
    config_path.write_text("project: {}\npaths: {}\n", encoding="utf-8")

    unrelated = tmp_path / "elsewhere"
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)

    cfg = {"external_sources": {source_name: {}}}
    captured = {}

    monkeypatch.setattr(cli, "load_config", lambda path: cfg)

    def fake_converter(inp, out):
        captured["input"] = inp
        captured["output"] = out

    monkeypatch.setattr(cli, converter_name, fake_converter)

    getattr(cli, command_name)(str(config_path))

    assert captured["input"] == (config_dir / default_raw).resolve()
    assert captured["output"] == (config_dir / default_normalized).resolve()
