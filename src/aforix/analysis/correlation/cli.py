from __future__ import annotations

from pathlib import Path

import typer

from aforix.analysis.correlation.config import resolve_correlation_paths, load_correlation_config
from aforix.analysis.correlation.instruments import load_instruments
from aforix.analysis.correlation.interactive import (
    ask_correlation_type,
    ask_instruments,
    ask_date_range,
)
from aforix.analysis.correlation.workflows.gauges_vs_model import (
    run_gauges_vs_model,
    default_ranking,
)

app = typer.Typer(help="Correlation analysis commands.")


@app.command("run")
def run_correlation(
    config: str = typer.Option(..., "--config", "-c", help="Path to config file"),
    correlation_type: str = typer.Option(None, "--type", help="Correlation type"),
    ranking: str = typer.Option(None, "--ranking", help="Instrument ranking"),
    start_date: str = typer.Option(None, "--start-date"),
    end_date: str = typer.Option(None, "--end-date"),
    interactive: bool = typer.Option(False, "--interactive"),
):
    cfg = load_correlation_config(Path(config))
    paths = resolve_correlation_paths(Path(config))
    instruments = load_instruments(cfg)

    if interactive or not correlation_type:
        correlation_type = ask_correlation_type()

    if ranking:
        ranking_codes = [x.upper() for x in ranking.split()]
    else:
        ranking_codes = default_ranking(cfg, instruments)
        if interactive:
            ranking_codes = ask_instruments(ranking_codes)

    if interactive and not start_date and not end_date:
        start_date, end_date = ask_date_range()

    if correlation_type == "gauges_vs_model":
        out = run_gauges_vs_model(
            normalized_root=paths.normalized_root,
            model_dir=paths.external_model_dir,
            output_dir=paths.output_root,
            instruments=instruments,
            ranking_codes=ranking_codes,
            start_date=start_date,
            end_date=end_date,
        )
        typer.echo(f"Gauges vs Model completed: {out}")
    else:
        typer.echo(f"Correlation type '{correlation_type}' not yet implemented.")
