import typer
from pathlib import Path

from aforix.analysis.stage_discharge.runner import run_stage_discharge
from aforix.analysis.stage_discharge.interactive import run_interactive

app = typer.Typer(help="Stage-discharge analysis")


@app.command("run")
def run_cmd(
    config: str = typer.Option(..., "--config", "-c"),
):
    out = run_stage_discharge(Path(config))
    typer.echo(f"Stage-discharge analysis completed: {out}")


@app.command("interactive")
def interactive_cmd(
    config: str = typer.Option(..., "--config", "-c"),
):
    out = run_interactive(Path(config))
    typer.echo(f"Stage-discharge interactive analysis completed: {out}")
