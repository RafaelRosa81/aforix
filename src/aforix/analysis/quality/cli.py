from __future__ import annotations

from pathlib import Path

import typer

from aforix.analysis.quality.runner import (
    discover_available_filters,
    run_quality_metrics,
)

app = typer.Typer(help="Quality metrics analysis.")


@app.command("run")
def run_quality(
    config: str = typer.Option(..., "--config", "-c", help="Path to config file"),
    interactive: bool = typer.Option(False, "--interactive", help="Run interactive quality metrics menu"),
    points: str | None = typer.Option(None, "--points", help="Comma-separated points, e.g. 1,2,21"),
    yyyymm: str | None = typer.Option(None, "--yyyymm", help="Comma-separated months, e.g. 202412,202501"),
    all_months: bool = typer.Option(False, "--all-months", help="Use all available months"),
    aggregation: str = typer.Option("daily", "--aggregation", help="measurement | daily | monthly"),
):
    config_path = Path(config)

    if interactive:
        available_points, available_months = discover_available_filters(config_path)

        typer.echo("Interactive quality metrics mode")
        typer.echo(f"Available points: {', '.join('P' + p for p in available_points) or '(none found)'}")
        point_input = typer.prompt(
            "Select points, comma-separated, empty = all",
            default="",
            show_default=False,
        )

        typer.echo(f"Available months: {', '.join(available_months) or '(none found)'}")
        month_input = typer.prompt(
            "Select months YYYYMM, comma-separated, empty = all",
            default="",
            show_default=False,
        )

        aggregation = typer.prompt(
            "Aggregation: measurement, daily, monthly",
            default=aggregation,
        )

        selected_points = _parse_csv_option(point_input)
        selected_months = _parse_csv_option(month_input)
        all_months = not selected_months
    else:
        selected_points = _parse_csv_option(points)
        selected_months = _parse_csv_option(yyyymm)

    out = run_quality_metrics(
        config_path,
        aggregation=aggregation,
        points=selected_points,
        months=selected_months,
        all_months=all_months,
    )

    typer.echo(f"Quality metrics completed: {out}")


def _parse_csv_option(value: str | None) -> list[str] | None:
    if value is None:
        return None
    parsed = [item.strip() for item in value.split(",") if item.strip()]
    return parsed or None
