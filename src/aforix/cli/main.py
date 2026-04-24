import typer
from pathlib import Path
from aforix.config.loader import load_config
from aforix.runs.manager import create_run
from aforix.ingest.flowtracker import run as run_flowtracker
from aforix.ingest.nivus import run as run_nivus
from aforix.ingest.molinete import run as run_molinete
from aforix.ingest.m9 import run as run_m9
from aforix.analysis.statistics import run as run_statistics
from aforix.groups.build import run as run_build_groups
from aforix.filters.groups import run as run_filter_groups
from aforix.export.excel import run as run_export_excel
from aforix.database.consolidate import consolidate_flowtracker_run


app = typer.Typer(
    name="aforix",
    help="Aforix: tools for processing discharge gauging data.",
    add_completion=False,
)

ingest_app = typer.Typer(help="Import and standardize raw measurement files.")
analyze_app = typer.Typer(help="Run hydrological and statistical analyses.")
export_app = typer.Typer(help="Export processed results.")
consolidate_app = typer.Typer(help="Consolidate runs into stable databases.")

app.add_typer(ingest_app, name="ingest")
app.add_typer(analyze_app, name="analyze")
app.add_typer(export_app, name="export")
app.add_typer(consolidate_app, name="consolidate")

@app.callback()
def main():
    """Aforix command-line interface."""
    pass


@app.command("config-check")
def config_check(
    config: str = typer.Option(..., "--config", "-c", help="Path to config file"),
):
    """Check configuration file."""
    
    config_path = Path(config)
    cfg = load_config(config_path)

    typer.echo("Config loaded successfully")
    typer.echo(f"Keys: {list(cfg.keys())}")


@ingest_app.command("flowtracker")
def ingest_flowtracker(
    config: str = typer.Option(..., "--config", "-c"),
):
    """Import FlowTracker files."""
    run_dir = run_flowtracker(Path(config))
    typer.echo(f"FlowTracker ingest completed: {run_dir}")


@ingest_app.command("molinete")
def ingest_molinete(
    config: str = typer.Option(..., "--config", "-c", help="Path to config file"),
):
    """Import Molinete files."""
    run_dir = run_molinete(Path(config))
    typer.echo(f"Molinete ingest completed: {run_dir}")


@ingest_app.command("nivus")
def ingest_nivus(
    config: str = typer.Option(..., "--config", "-c", help="Path to config file"),
):
    """Import Nivus XML files."""
    run_dir = run_nivus(Path(config))
    typer.echo(f"Nivus ingest completed: {run_dir}")


@ingest_app.command("m9")
def ingest_m9(
    config: str = typer.Option(..., "--config", "-c", help="Path to config file"),
):
    """Import M9 files."""
    run_dir = run_m9(Path(config))
    typer.echo(f"M9 ingest completed: {run_dir}")


@analyze_app.command("statistics")
def analyze_statistics(
    config: str = typer.Option(..., "--config", "-c", help="Path to config file"),
):
    """Run statistical analysis."""
    run_dir = run_statistics(Path(config))
    typer.echo(f"Statistical analysis completed: {run_dir}")


@app.command("build-groups")
def build_groups(
    config: str = typer.Option(..., "--config", "-c"),
):
    run_dir = run_build_groups(Path(config))
    typer.echo(f"Groups built: {run_dir}")


@app.command("filter-groups")
def filter_groups(
    config: str = typer.Option(..., "--config", "-c"),
):
    run_dir = run_filter_groups(Path(config))
    typer.echo(f"Groups filtered: {run_dir}")


@export_app.command("excel")
def export_excel(
    config: str = typer.Option(..., "--config", "-c"),
):
    run_dir = run_export_excel(Path(config))
    typer.echo(f"Excel export completed: {run_dir}")


@consolidate_app.command("flowtracker")
def consolidate_flowtracker(
    run_dir: str = typer.Option(..., "--run-dir", help="Path to FlowTracker ingest run directory."),
    database_root: str = typer.Option("database", "--database-root", help="Root database directory."),
):
    """Consolidate FlowTracker ingest outputs into unified CSV files."""
    target_root = consolidate_flowtracker_run(
        run_dir=Path(run_dir),
        database_root=Path(database_root),
    )
    typer.echo(f"FlowTracker database updated: {target_root}")


if __name__ == "__main__":
    app()