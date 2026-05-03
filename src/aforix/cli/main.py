from pathlib import Path

import typer

from aforix.config.loader import load_config
from aforix.ingest.flowtracker import run as run_flowtracker
from aforix.ingest.nivus import run as run_nivus
from aforix.ingest.molinete import run as run_molinete
from aforix.ingest.m9 import run as run_m9
from aforix.analysis.statistics import run as run_statistics
from aforix.analysis.correlation.cli import app as correlation_app
from aforix.analysis.quality.cli import app as quality_app
from aforix.external.cli import app as external_app
from aforix.groups.build import run as run_build_groups
from aforix.filters.groups import run as run_filter_groups
from aforix.export.excel import run as run_export_excel
from aforix.database.consolidate import consolidate_flowtracker_run
from aforix.export.tables.cli import main as export_tables_main
from aforix.normalize.run import normalize_database
from aforix.validation.run import run_validation

app = typer.Typer(name="aforix", help="Aforix CLI", add_completion=False)

analyze_app = typer.Typer()

app.add_typer(analyze_app, name="analyze")
analyze_app.add_typer(correlation_app, name="correlation")
analyze_app.add_typer(quality_app, name="quality")

@app.command("config-check")
def config_check(config: str = typer.Option(..., "--config", "-c")):
    cfg = load_config(Path(config))
    typer.echo("Config loaded")
