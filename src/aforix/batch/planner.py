from aforix.batch.models import BatchDefinition, BatchStep


class BatchPlanner:
    """Resolves and prepares execution plans for batches."""

    def build_execution_plan(self, batch: BatchDefinition) -> list[BatchStep]:
        """Return enabled steps in execution order.

        Future versions may support:

        - dependency graphs;
        - DAG validation;
        - parallel scheduling;
        - conditional execution.
        """

        return [step for step in batch.steps if step.enabled]
