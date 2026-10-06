from aforix.export.tables.cli import parse_args


def test_export_tables_cli_defaults_to_flat_grouping():
    args = parse_args(["-c", "configs/examples/main.yaml", "--table", "Summary"])
    assert args.grouping == "none"
