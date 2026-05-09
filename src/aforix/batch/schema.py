from typing import Any

from aforix.batch.errors import BatchValidationError


REQUIRED_ROOT_KEYS = {
    "version",
    "batch",
    "project",
    "execution",
    "steps",
}


REQUIRED_STEP_KEYS = {
    "id",
    "command",
}


SUPPORTED_BATCH_VERSION = 1


class BatchSchemaValidator:
    """Validates batch YAML structure."""

    def validate(self, data: dict[str, Any]) -> None:
        self._validate_root(data)
        self._validate_version(data)
        self._validate_steps(data)

    def _validate_root(self, data: dict[str, Any]) -> None:
        missing = REQUIRED_ROOT_KEYS - set(data)
        if missing:
            raise BatchValidationError(
                f"Missing required root keys: {sorted(missing)}"
            )

    def _validate_version(self, data: dict[str, Any]) -> None:
        version = data.get("version")

        if version != SUPPORTED_BATCH_VERSION:
            raise BatchValidationError(
                f"Unsupported batch version: {version}"
            )

    def _validate_steps(self, data: dict[str, Any]) -> None:
        steps = data.get("steps")

        if not isinstance(steps, list):
            raise BatchValidationError("'steps' must be a list.")

        seen_ids: set[str] = set()

        for index, step in enumerate(steps):
            if not isinstance(step, dict):
                raise BatchValidationError(
                    f"Step at index {index} must be a mapping/dictionary."
                )

            missing = REQUIRED_STEP_KEYS - set(step)
            if missing:
                raise BatchValidationError(
                    f"Step at index {index} missing required keys: {sorted(missing)}"
                )

            step_id = step["id"]

            if step_id in seen_ids:
                raise BatchValidationError(
                    f"Duplicate step id detected: {step_id}"
                )

            seen_ids.add(step_id)
