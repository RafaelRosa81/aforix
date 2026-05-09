from typing import Any


class VariableResolver:
    """Resolve ${variables} in batch definitions."""

    def resolve(self, value: Any, variables: dict[str, Any]) -> Any:
        if isinstance(value, dict):
            return {
                key: self.resolve(item, variables)
                for key, item in value.items()
            }

        if isinstance(value, list):
            return [self.resolve(item, variables) for item in value]

        if not isinstance(value, str):
            return value

        if not value.startswith("${") or not value.endswith("}"):
            return value

        variable_name = value[2:-1]

        return variables.get(variable_name, value)
