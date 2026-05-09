from aforix.batch.resolver import VariableResolver


resolver = VariableResolver()


def test_resolve_string_variable() -> None:
    result = resolver.resolve("${format}", {"format": "xlsx"})
    assert result == "xlsx"


def test_resolve_nested_dictionary() -> None:
    value = {
        "table": "Summary",
        "format": "${format}",
    }

    result = resolver.resolve(value, {"format": "csv"})

    assert result["format"] == "csv"


def test_non_variable_string_is_unchanged() -> None:
    result = resolver.resolve("Summary", {})
    assert result == "Summary"
