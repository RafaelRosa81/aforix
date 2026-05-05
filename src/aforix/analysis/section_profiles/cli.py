from __future__ import annotations

from pathlib import Path
import copy
import typer

from aforix.analysis.section_profiles.config import load_section_profiles_config
from aforix.analysis.section_profiles.interactive import apply_interactive_overrides
from aforix.analysis.section_profiles.runner import run_section_profiles

app = typer.Typer(help="Section profiles analysis")


@app.command("run")
def run_cmd(
    config: str = typer.Option(..., "--config", "-c"),
    interactive: bool = typer.Option(False, "--interactive", help="Run an interactive section profiles menu"),
    instruments: str | None = typer.Option(None, "--instruments", help="Comma-separated instruments/codes, e.g. NV,FT or nivus,flowtracker"),
    points: str | None = typer.Option(None, "--points", help="Comma-separated station IDs, e.g. P1,P8"),
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
    x_axis: str | None = typer.Option(None, "--x-axis"),
    y_axis: str | None = typer.Option(None, "--y-axis"),
    chart_type: str | None = typer.Option(None, "--chart-type"),
):
    cfg_path = Path(config)
    cfg = copy.deepcopy(load_section_profiles_config(cfg_path))

    if interactive:
        cfg = apply_interactive_overrides(cfg)
    else:
        _apply_cli_overrides(
            cfg,
            instruments=instruments,
            points=points,
            start_date=start_date,
            end_date=end_date,
            x_axis=x_axis,
            y_axis=y_axis,
            chart_type=chart_type,
        )

    out = run_section_profiles(cfg_path, override_config=cfg)
    typer.echo(f"Section profiles analysis completed: {out}")


def _apply_cli_overrides(
    cfg: dict,
    *,
    instruments: str | None,
    points: str | None,
    start_date: str | None,
    end_date: str | None,
    x_axis: str | None,
    y_axis: str | None,
    chart_type: str | None,
) -> None:
    sel = cfg.setdefault("selection", {})

    if instruments is not None:
        sel["instruments"] = _parse_csv(instruments)
    if points is not None:
        sel["points"] = [_normalize_point(p) for p in _parse_csv(points)]
    if start_date is not None:
        sel["start_date"] = start_date
    if end_date is not None:
        sel["end_date"] = end_date

    defaults = cfg.setdefault("defaults", {})
    if x_axis is not None:
        defaults["x_axis"] = x_axis
    if y_axis is not None:
        defaults["y_axis"] = y_axis
    if chart_type is not None:
        defaults["chart_type"] = chart_type


def _parse_csv(v: str | None) -> list[str]:
    if not v:
        return []
    return [x.strip() for x in v.split(",") if x.strip()]


def _normalize_point(value: str) -> str:
    s = str(value).strip().upper()
    if s.startswith("P"):
        digits = "".join(ch for ch in s[1:] if ch.isdigit())
    else:
        digits = "".join(ch for ch in s if ch.isdigit())
    return f"P{int(digits)}" if digits else s
