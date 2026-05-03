import typer
from pathlib import Path

from aforix.analysis.stage_discharge.runner import run_stage_discharge

app = typer.Typer(help="Stage-discharge analysis")


@app.command("run")
def run_cmd(
    config: str = typer.Option(..., "--config", "-c"),
):
    out = run_stage_discharge(Path(config))
    typer.echo(f"Stage-discharge analysis completed: {out}")
