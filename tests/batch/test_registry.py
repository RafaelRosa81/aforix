import pytest

from aforix.batch.errors import RegistryError
from aforix.batch.registry import CommandRegistry, RegisteredCommand


registry = CommandRegistry()


def noop(params=None):
    return params


def test_register_and_get_command() -> None:
    command = RegisteredCommand(
        name="normalize.run",
        callable=noop,
    )

    registry.register(command)

    assert registry.get("normalize.run") is command


def test_duplicate_command_registration_fails() -> None:
    registry_local = CommandRegistry()

    command = RegisteredCommand(
        name="validate.run",
        callable=noop,
    )

    registry_local.register(command)

    with pytest.raises(RegistryError):
        registry_local.register(command)
