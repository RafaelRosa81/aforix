import pytest
from typer.testing import CliRunner

from aforix.cli.main import app


@pytest.mark.parametrize(
    ("args", "expected_message"),
    [
        (
            ["ingest", "m9", "-c", "configs/examples/main.yaml"],
            "M9/ADCP ingestion is not implemented yet",
        ),
        (
            ["analyze", "statistics", "-c", "configs/examples/main.yaml"],
            "Statistical analysis is not implemented yet",
        ),
    ],
)
def test_unimplemented_commands_exit_with_clear_error(args, expected_message):
    result = CliRunner().invoke(app, args)

    assert result.exit_code == 2
    assert expected_message in result.output
