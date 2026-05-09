import pytest

from aforix.batch.errors import BatchValidationError
from aforix.batch.schema import BatchSchemaValidator


def _valid_batch() -> dict:
    return {
        "version": 1,
        "batch": {"id": "test", "name": "Test"},
        "project": {"main_config": "configs/examples/main.yaml"},
        "execution": {"output_dir": "runs/batch"},
        "steps": [
            {"id": "config_check", "command": "config-check"},
            {"id": "normalize", "command": "normalize.run"},
        ],
    }


def test_valid_batch_schema_passes() -> None:
    BatchSchemaValidator().validate(_valid_batch())


def test_missing_root_key_fails() -> None:
    data = _valid_batch()
    data.pop("steps")

    with pytest.raises(BatchValidationError):
        BatchSchemaValidator().validate(data)


def test_duplicate_step_id_fails() -> None:
    data = _valid_batch()
    data["steps"].append({"id": "normalize", "command": "validate.run"})

    with pytest.raises(BatchValidationError):
        BatchSchemaValidator().validate(data)
