from __future__ import annotations

import re
from pathlib import Path

import typer

from aforix.analysis.correlation.config import load_correlation_config, resolve_correlation_paths
from aforix.analysis.correlation.instruments import load_instruments
from aforix.analysis.correlation.interactive import (
    ask_correlation_type,
    ask_date_range,
    ask_instruments,
    ask_pairs,
    ask_timestep,
)
from aforix.analysis.correlation.workflows.gauges_vs_model import default_ranking, run_gauges_vs_model
from aforix.analysis.correlation.workflows.gauges_vs_stations import run_gauges_vs_stations
from aforix.analysis.correlation.workflows.model_vs_stations import run_model_vs_stations

app = typer.Typer(help="Correlation analysis commands.")


def _parse_pairs(raw: str | None) -> list[tuple[str, str]]:
    if not raw:
        return []
    pairs: list[tuple[str, str]] = []
    blocks = re.findall(r"\[([^\]]+)\]", raw)
    if blocks:
        for block in blocks:
            parts = block.replace(",", " ").split()
            if len(parts) == 2:
                pairs.append((parts[0], parts[1]))
        return pairs
    chunks = re.split(r"[;,]+", raw)
    for chunk in chunks:
        parts = chunk.strip().split()
        if len(parts) == 2:
            pairs.append((parts[0], parts[1]))
    return pairs


@app.command("run")
def run_correlation(
    config: str = typer.Option(..., "--config", "-c", help="Path to config file"),
    correlation_type: str = typer.Option(
        None,
        "--type",
        help="gauges_vs_model | gauges_vs_stations | model_vs_stations",
    ),
    ranking: str = typer.Option(None, "--ranking", help="Instrument ranking, e.g. 'NV FT ML'"),
    timestep: str = typer.Option("daily", "--timestep", help="daily | monthly; gauges_vs_stations also accepts hourly later"),
    pairs: str = typer.Option(None, "--pairs", help='Pairs, e.g. "[44 15] [117 10]"'),
    all_pairs: bool = typer.Option(False, "--all-pairs", help="Compare all available stations and model points"),
    match_mode: str = typer.Option("exact", "--match-mode", help="exact | window"),
    window_days: int = typer.Option(0, "--window-days", help="Window size in days for match-mode=window"),
    start_date: str = typer.Option(None, "--start-date", help="YYYYMMDD"),
    end_date: str = typer.Option(None, "--end-date", help="YYYYMMDD"),
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
        if interactive and correlation_type in {"gauges_vs_model", "gauges_vs_stations"}:
            ranking_codes = ask_instruments(ranking_codes)

    if interactive and correlation_type in {"gauges_vs_stations", "model_vs_stations"}:
        timestep = ask_timestep()

    if interactive and correlation_type == "model_vs_stations" and not pairs and not all_pairs:
        parsed_pairs = ask_pairs()
    else:
        parsed_pairs = _parse_pairs(pairs)

    if interactive and not start_date and not end_date and correlation_type == "gauges_vs_model":
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
        return

    if correlation_type == "gauges_vs_stations":
        out = run_gauges_vs_stations(
            normalized_root=paths.normalized_root,
            stations_dir=paths.external_stations_dir,
            output_dir=paths.output_root,
            instruments=instruments,
            ranking_codes=ranking_codes,
            timestep=timestep,
            match_mode=match_mode,
            window_days=window_days,
        )
        typer.echo(f"Gauges vs Stations completed: {out}")
        return

    if correlation_type == "model_vs_stations":
        if not parsed_pairs and not all_pairs:
            raise typer.BadParameter("model_vs_stations requires --pairs unless --all-pairs is used")
        out = run_model_vs_stations(
            stations_dir=paths.external_stations_dir,
            model_dir=paths.external_model_dir,
            output_dir=paths.output_root,
            pairs=parsed_pairs,
            timestep=timestep,
            all_pairs=all_pairs,
        )
        typer.echo(f"Model vs Stations completed: {out}")
        return

    raise typer.BadParameter(f"Unknown correlation type: {correlation_type}")
