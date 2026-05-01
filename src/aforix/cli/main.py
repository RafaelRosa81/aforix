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
    config_path = Path(config).resolve()
    load_config(config_path)
    return config_path


@app.callback()
def main():
    pass


@analyze_app.command("statistics")
def analyze_statistics(
    config: str = typer.Option(..., "--config", "-c", help="Path to config file"),
):
    config_path = _load_validated_config(config)
    run_dir = run_statistics(config_path)
    typer.echo(f"Statistical analysis completed: {run_dir}")


if __name__ == "__main__":
    app()
