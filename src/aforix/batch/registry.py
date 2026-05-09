from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from aforix.batch.errors import RegistryError


@dataclass(slots=True)
class RegisteredCommand:
    name: str
    callable: Callable[..., Any]
    description: str = ""
    category: str = "general"


class CommandRegistry:
    """Central registry for batch-executable commands."""

    def __init__(self) -> None:
        self._commands: dict[str, RegisteredCommand] = {}

    def register(self, command: RegisteredCommand) -> None:
        if command.name in self._commands:
            raise RegistryError(f"Command already registered: {command.name}")

        self._commands[command.name] = command

    def exists(self, name: str) -> bool:
        return name in self._commands

    def get(self, name: str) -> RegisteredCommand:
        try:
            return self._commands[name]
        except KeyError as exc:
            raise RegistryError(f"Unknown command: {name}") from exc

    def list_commands(self) -> list[str]:
        return sorted(self._commands)
