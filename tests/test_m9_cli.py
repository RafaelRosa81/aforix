from pathlib import Path

import aforix.cli.main as cli


def test_m9_cli_dispatches_to_ingest_runner(tmp_path, monkeypatch, capsys):
    config_path = tmp_path / "main.yaml"
    run_dir = tmp_path / "run"
    monkeypatch.setattr(cli, "_load_validated_config", lambda _: config_path)
    called = []
    monkeypatch.setattr(cli, "run_m9", lambda path: called.append(path) or run_dir)

    cli.ingest_m9(config="configs/examples/main.yaml")

    assert called == [config_path]
    assert "M9 ingest completed" in capsys.readouterr().out
