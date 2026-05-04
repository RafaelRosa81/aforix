from pathlib import Path
from typing import Optional
import copy

import typer

from aforix.analysis.stage_discharge.config import load_stage_discharge_config
from aforix.analysis.stage_discharge.runner import run_stage_discharge
from aforix.analysis.stage_discharge.interactive import run_interactive

app = typer.Typer(help="Stage-discharge analysis")

INSTRUMENT_CODES = {
    "NV": "nivus",
    "FT": "flowtracker",
    "ML": "molinete",
    "M9": "m9",
}


@app.command("run")
def run_cmd(
    config: str = typer.Option(..., "--config", "-c"),
    points: Optional[str] = typer.Option(None, "--points", help="Comma-separated station IDs, e.g. P1,P8,P13. Use 'all' for all points."),
    start_date: Optional[str] = typer.Option(None, "--start-date", help="Inclusive start date in YYYY-MM-DD format."),
    end_date: Optional[str] = typer.Option(None, "--end-date", help="Inclusive end date in YYYY-MM-DD format."),
    instruments: Optional[str] = typer.Option(None, "--instruments", help="Comma-separated instrument codes/names, e.g. NV,FT or nivus,flowtracker."),
    ranking: Optional[str] = typer.Option(None, "--ranking", help="Comma-separated ranking order, e.g. NV,FT,ML."),
    depth_mode: Optional[str] = typer.Option(None, "--depth-mode", help="manual, instrument, or both."),
    instrument_stage_mode: Optional[str] = typer.Option(None, "--instrument-stage-mode", help="mean, max, or both."),
    plots: Optional[bool] = typer.Option(None, "--plots/--no-plots", help="Enable or disable plot generation."),
    excel: Optional[bool] = typer.Option(None, "--excel/--no-excel", help="Enable or disable Excel report generation."),
    max_plots: Optional[int] = typer.Option(None, "--max-plots", help="Maximum number of plots to generate."),
):
    cfg_path = Path(config)
    cfg = copy.deepcopy(load_stage_discharge_config(cfg_path))
    _apply_cli_overrides(
        cfg,
        points=points,
        start_date=start_date,
        end_date=end_date,
        instruments=instruments,
        ranking=ranking,
        depth_mode=depth_mode,
        instrument_stage_mode=instrument_stage_mode,
        plots=plots,
        excel=excel,
        max_plots=max_plots,
    )
    out = run_stage_discharge(cfg_path, override_config=cfg)
    typer.echo(f"Stage-discharge analysis completed: {out}")


@app.command("interactive")
def interactive_cmd(
    config: str = typer.Option(..., "--config", "-c"),
):
    out = run_interactive(Path(config))
    typer.echo(f"Stage-discharge interactive analysis completed: {out}")


def _apply_cli_overrides(
    cfg: dict,
    *,
    points: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
    instruments: Optional[str],
    ranking: Optional[str],
    depth_mode: Optional[str],
    instrument_stage_mode: Optional[str],
    plots: Optional[bool],
    excel: Optional[bool],
    max_plots: Optional[int],
) -> None:
    selection = cfg.setdefault("selection", {})

    if points is not None:
        parsed = _parse_list(points)
        selection["points"] = "all" if len(parsed) == 1 and parsed[0].lower() == "all" else [_normalize_station_id(p) for p in parsed]
    if start_date is not None:
        selection["start_date"] = start_date or None
    if end_date is not None:
        selection["end_date"] = end_date or None
    if depth_mode is not None:
        selection["depth_mode"] = depth_mode.strip().lower()
    if instrument_stage_mode is not None:
        selection["instrument_stage_mode"] = instrument_stage_mode.strip().lower()

    if instruments is not None:
        selected = [_to_instrument_name(v) for v in _parse_list(instruments)]
        for name, inst_cfg in cfg.get("instruments", {}).items():
            inst_cfg["enabled"] = name in selected

    if ranking is not None:
        cfg.setdefault("instrument_selection", {})["ranking"] = [_to_instrument_name(v) for v in _parse_list(ranking)]

    if plots is not None:
        cfg.setdefault("plotting", {})["enabled"] = bool(plots)
    if max_plots is not None:
        cfg.setdefault("plotting", {})["max_plots"] = max_plots
    if excel is not None:
        cfg.setdefault("excel", {})["enabled"] = bool(excel)


def _parse_list(value: str) -> list[str]:
    return [v.strip() for v in str(value).split(",") if v.strip()]


def _to_instrument_name(value: str) -> str:
    v = str(value).strip()
    return INSTRUMENT_CODES.get(v.upper(), v.lower())


def _normalize_station_id(value: str) -> str:
    s = str(value).strip().upper()
    if s.startswith("P"):
        digits = "".join(ch for ch in s[1:] if ch.isdigit())
    else:
        digits = "".join(ch for ch in s if ch.isdigit())
    return f"P{int(digits)}" if digits else s
