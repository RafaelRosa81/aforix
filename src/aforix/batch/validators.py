from aforix.batch.errors import BatchValidationError
from aforix.batch.registry import CommandRegistry


class RegistryValidator:
    """Validate that referenced commands exist in the registry."""

    def validate_commands(
        self,
        steps: list[dict],
        registry: CommandRegistry,
    ) -> None:
        unknown_commands: list[str] = []

        for step in steps:
            command = step["command"]

            if not registry.exists(command):
                unknown_commands.append(command)

        if unknown_commands:
            raise BatchValidationError(
                f"Unknown commands detected: {sorted(set(unknown_commands))}"
            )
