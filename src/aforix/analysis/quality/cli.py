from __future__ import annotations

import typer
from pathlib import Path

from aforix.config.loader import load_config
from aforix.analysis.quality.runner import run_quality_metrics

app = typer.Typer(help="Quality metrics analysis.")


@app.command("run")
def run_quality(
    config: str = typer.Option(..., "--config", "-c"),
):
    cfg = load_config(Path(config))
    out = run_quality_metrics(cfg)
    typer.echo(f"Quality metrics completed: {out}")
