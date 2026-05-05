from __future__ import annotations

from pathlib import Path
import copy
import typer

from aforix.analysis.section_profiles.config import load_section_profiles_config
from aforix.analysis.section_profiles.runner import run_section_profiles

app = typer.Typer(help="Section profiles analysis")


@app.command("run")
def run_cmd(
    config: str = typer.Option(..., "--config", "-c"),
    instruments: str | None = typer.Option(None, "--instruments", help="Comma-separated instruments, e.g. nivus,flowtracker"),
    points: str | None = typer.Option(None, "--points", help="Comma-separated station IDs, e.g. P1,P8"),
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
    x_axis: str | None = typer.Option(None, "--x-axis"),
    y_axis: str | None = typer.Option(None, "--y-axis"),
    chart_type: str | None = typer.Option(None, "--chart-type"),
):
    cfg_path = Path(config)
    cfg = copy.deepcopy(load_section_profiles_config(cfg_path))

    sel = cfg.setdefault('selection', {})

    if instruments is not None:
        sel['instruments'] = _parse_csv(instruments)
    if points is not None:
        sel['points'] = _parse_csv(points)
    if start_date is not None:
        sel['start_date'] = start_date
    if end_date is not None:
        sel['end_date'] = end_date

    defaults = cfg.setdefault('defaults', {})
    if x_axis is not None:
        defaults['x_axis'] = x_axis
    if y_axis is not None:
        defaults['y_axis'] = y_axis
    if chart_type is not None:
        defaults['chart_type'] = chart_type

    out = run_section_profiles(cfg_path, override_config=cfg)
    typer.echo(f"Section profiles analysis completed: {out}")


def _parse_csv(v: str | None):
    if not v:
        return None
    return [x.strip() for x in v.split(',') if x.strip()]
