from pathlib import Path

import typer

from aforix.config.loader import load_config
from aforix.ingest.flowtracker import run as run_flowtracker
from aforix.ingest.nivus import run as run_nivus
from aforix.ingest.molinete import run as run_molinete
from aforix.ingest.m9 import run as run_m9
from aforix.analysis.statistics import run as run_statistics
from aforix.analysis.correlation.cli import app as correlation_app
from aforix.external.cli import app as external_app
from aforix.groups.build import run as run_build_groups
from aforix.filters.groups import run as run_filter_groups
from aforix.export.excel import run as run_export_excel
from aforix.database.consolidate import consolidate_flowtracker_run
from aforix.export.tables.cli import main as export_tables_main
from aforix.normalize.run import normalize_database
from aforix.validation.run import run_validation


app = typer.Typer(
    name="aforix",
    help="Aforix: tools for processing discharge gauging data.",
    add_completion=False,
)

ingest_app = typer.Typer(help="Import and standardize raw measurement files.")
analyze_app = typer.Typer(help="Run hydrological and statistical analyses.")
export_app = typer.Typer(help="Export processed results.")
consolidate_app = typer.Typer(help="Consolidate runs into stable databases.")
normalize_app = typer.Typer(help="Normalize raw grouped datasets.")
validate_app = typer.Typer(help="Validate normalized datasets.")


app.add_typer(ingest_app, name="ingest")
app.add_typer(analyze_app, name="analyze")
app.add_typer(export_app, name="export")
app.add_typer(consolidate_app, name="consolidate")
app.add_typer(normalize_app, name="normalize")
app.add_typer(validate_app, name="validate")
app.add_typer(external_app, name="external")
analyze_app.add_typer(correlation_app, name="correlation")


def _load_validated_config(config: str | Path) -> Path:
    """
    Load and validate an Aforix config file.

    The current pipeline modules still expect a config path, not the loaded dict.
    Therefore this helper validates early and then returns the normalized path.
    """

    config_path = Path(config).resolve()
    load_config(config_path)
    return config_path


@app.callback()
def main():
    """Aforix command-line interface."""
    pass


@app.command("config-check")
def config_check(
    config: str = typer.Option(..., "--config", "-c", help="Path to config file"),
):
    """Check configuration file."""

    config_path = _load_validated_config(config)
    cfg = load_config(config_path)

    typer.echo("Config loaded successfully")
    typer.echo(f"Config path: {config_path}")
    typer.echo(f"Keys: {list(cfg.keys())}")


@ingest_app.command("flowtracker")
def ingest_flowtracker(
    config: str = typer.Option(..., "--config", "-c", help="Path to config file"),
):
    """Import FlowTracker files."""

    config_path = _load_validated_config(config)
    run_dir = run_flowtracker(config_path)

    typer.echo(f"FlowTracker ingest completed: {run_dir}")


@ingest_app.command("molinete")
def ingest_molinete(
    config: str = typer.Option(..., "--config", "-c", help="Path to config file"),
):
    """Import Molinete files."""

    config_path = _load_validated_config(config)
    run_dir = run_molinete(config_path)

    typer.echo(f"Molinete ingest completed: {run_dir}")


@ingest_app.command("nivus")
def ingest_nivus(
    config: str = typer.Option(..., "--config", "-c", help="Path to config file"),
):
    """Import Nivus XML files."""

    config_path = _load_validated_config(config)
    run_dir = run_nivus(config_path)

    typer.echo(f"Nivus ingest completed: {run_dir}")


@ingest_app.command("m9")
def ingest_m9(
    config: str = typer.Option(..., "--config", "-c", help="Path to config file"),
):
    """Import M9 files."""

    config_path = _load_validated_config(config)
    run_dir = run_m9(config_path)

    typer.echo(f"M9 ingest completed: {run_dir}")


@analyze_app.command("statistics")
def analyze_statistics(
    config: str = typer.Option(..., "--config", "-c", help="Path to config file"),
):
    """Run statistical analysis."""

    config_path = _load_validated_config(config)
    run_dir = run_statistics(config_path)

    typer.echo(f"Statistical analysis completed: {run_dir}")


@app.command("build-groups")
def build_groups(
    config: str = typer.Option(..., "--config", "-c", help="Path to config file"),
):
    """Build grouped datasets."""

    config_path = _load_validated_config(config)
    run_dir = run_build_groups(config_path)

    typer.echo(f"Groups built: {run_dir}")


@app.command("filter-groups")
def filter_groups(
    config: str = typer.Option(..., "--config", "-c", help="Path to config file"),
):
    """Filter grouped datasets."""

    config_path = _load_validated_config(config)
    run_dir = run_filter_groups(config_path)

    typer.echo(f"Groups filtered: {run_dir}")


@export_app.command("excel")
def export_excel(
    config: str = typer.Option(..., "--config", "-c", help="Path to config file"),
):
    """Export results to Excel."""

    config_path = _load_validated_config(config)
    run_dir = run_export_excel(config_path)

    typer.echo(f"Excel export completed: {run_dir}")


@export_app.command("tables")
def export_tables(
    config: str = typer.Option(..., "--config", "-c", help="Path to config file"),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        help="Run interactive export tables menu",
    ),
):
    """Export normalized tables from database/normalized."""

    config_path = _load_validated_config(config)

    argv = ["-c", str(config_path)]

    if interactive:
        argv.append("--interactive")

    export_tables_main(argv)


@consolidate_app.command("flowtracker")
def consolidate_flowtracker(
    run_dir: str = typer.Option(
        ...,
        "--run-dir",
        help="Path to FlowTracker ingest run directory.",
    ),
    database_root: str = typer.Option(
        "database",
        "--database-root",
        help="Root database directory.",
    ),
):
    """Consolidate FlowTracker ingest outputs into unified CSV files."""

    target_root = consolidate_flowtracker_run(
        run_dir=Path(run_dir),
        database_root=Path(database_root),
    )

    typer.echo(f"FlowTracker database updated: {target_root}")


@normalize_app.command("run")
def normalize_run_cmd(
    config: str = typer.Option(..., "--config", "-c", help="Path to config file"),
):
    """Normalize raw_canonical database using the registry."""

    config_path = _load_validated_config(config)
    run_dir = normalize_database(config_path)

    typer.echo(f"Normalize completed: {run_dir}")


@validate_app.command("run")
def validate_run_cmd(
    config: str = typer.Option(..., "--config", "-c", help="Path to config file"),
):
    """Validate normalized database tables."""

    config_path = _load_validated_config(config)
    output_dir = run_validation(config_path)

    typer.echo(f"Validation completed: {output_dir}")


if __name__ == "__main__":
    app()
