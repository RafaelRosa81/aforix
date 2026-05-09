from aforix.batch.models import BatchDefinition, BatchStep
from aforix.batch.resolver import VariableResolver


class BatchPlanner:
    """Resolves and prepares execution plans for batches."""

    def __init__(self) -> None:
        self.resolver = VariableResolver()

    def build_execution_plan(
        self,
        batch: BatchDefinition,
        *,
        from_step: str | None = None,
        only_step: str | None = None,
        skip_steps: set[str] | None = None,
    ) -> list[BatchStep]:
        """Return enabled and resolved execution steps."""

        skip_steps = skip_steps or set()

        planned_steps: list[BatchStep] = []

        for step in batch.steps:
            if not step.enabled:
                continue

            if only_step and step.id != only_step:
                continue

            if step.id in skip_steps:
                continue

            resolved_params = self.resolver.resolve(
                step.params,
                batch.variables,
            )

            planned_steps.append(
                BatchStep(
                    id=step.id,
                    command=step.command,
                    enabled=step.enabled,
                    params=resolved_params,
                    depends_on=step.depends_on,
                    tags=step.tags,
                )
            )

        if from_step:
            planned_steps = self._slice_from_step(planned_steps, from_step)

        return planned_steps

    def _slice_from_step(
        self,
        steps: list[BatchStep],
        from_step: str,
    ) -> list[BatchStep]:
        for index, step in enumerate(steps):
            if step.id == from_step:
                return steps[index:]

        return steps
