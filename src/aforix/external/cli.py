from __future__ import annotations

from pathlib import Path

import typer

from aforix.config.loader import load_config
from aforix.external.model.convert import run_model_conversion
from aforix.external.dinagua.convert import run_dinagua_conversion

app = typer.Typer(help="External data converters")


@app.command("convert-model")
def convert_model(
    config: str = typer.Option(..., "--config", "-c"),
):
    cfg = load_config(Path(config))
    inp = Path(cfg.get("external_sources", {}).get("model", {}).get("raw_dir", "database/external/raw/model"))
    out = Path(cfg.get("external_sources", {}).get("model", {}).get("normalized_dir", "database/external/normalized/model"))
    run_model_conversion(inp, out)
    typer.echo(f"Model data converted: {out}")


@app.command("convert-dinagua")
def convert_dinagua(
    config: str = typer.Option(..., "--config", "-c"),
):
    cfg = load_config(Path(config))
    inp = Path(cfg.get("external_sources", {}).get("dinagua", {}).get("raw_dir", "database/external/raw/dinagua"))
    out = Path(cfg.get("external_sources", {}).get("dinagua", {}).get("normalized_dir", "database/external/normalized/dinagua"))
    run_dinagua_conversion(inp, out)
    typer.echo(f"DINAGUA data converted: {out}")
