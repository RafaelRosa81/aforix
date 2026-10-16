from aforix.ingest import m9


def test_m9_ingest_handles_empty_mat_directory(tmp_path, monkeypatch, capsys):
    config_path = tmp_path / "main.yaml"
    config_path.write_text("test", encoding="utf-8")
    run_dir = tmp_path / "run"
    raw_root = tmp_path / "raw"
    raw_root.mkdir()

    monkeypatch.setattr(
        m9,
        "load_config",
        lambda _: {"ingest": {"m9": {"enabled": True}}, "project": {"timezone": "UTC"}},
    )
    monkeypatch.setattr(m9, "create_run", lambda *_: run_dir)
    monkeypatch.setattr(m9, "_get_m9_raw_root", lambda *_, **__: raw_root)
    monkeypatch.setattr(m9, "find_files_recursive", lambda *_: [])

    result = m9.run(config_path)

    assert result == run_dir
    assert (run_dir / "outputs" / "raw_canonical" / "m9" / "Summary").is_dir()
    assert (run_dir / "outputs" / "raw_canonical" / "m9" / "Points").is_dir()
    assert "Found RiverSurveyor Live MAT files: 0" in capsys.readouterr().out
