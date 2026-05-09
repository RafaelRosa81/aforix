class BatchError(Exception):
    """Base batch exception."""


class BatchValidationError(BatchError):
    """Raised when batch configuration validation fails."""


class BatchPlanningError(BatchError):
    """Raised when execution planning fails."""


class BatchExecutionError(BatchError):
    """Raised when batch execution fails."""


class RegistryError(BatchError):
    """Raised when command registry resolution fails."""
