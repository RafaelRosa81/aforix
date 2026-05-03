from __future__ import annotations

import typer
from pathlib import Path

from aforix.analysis.quality.runner import run_quality_metrics

app = typer.Typer(help="Quality metrics analysis.")


@app.command("run")
def run_quality(
    config: str = typer.Option(..., "--config", "-c"),
):
    out = run_quality_metrics(Path(config))
    typer.echo(f"Quality metrics completed: {out}")
