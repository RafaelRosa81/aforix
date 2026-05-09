from aforix.batch.models import BatchDefinition
from aforix.batch.planner import BatchPlanner
from aforix.batch.registry import CommandRegistry


class BatchRunner:
    """Coordinates batch execution.

    The runner must never implement domain processing logic directly.
    """

    def __init__(
        self,
        registry: CommandRegistry,
        planner: BatchPlanner | None = None,
    ) -> None:
        self.registry = registry
        self.planner = planner or BatchPlanner()

    def run(self, batch: BatchDefinition) -> None:
        plan = self.planner.build_execution_plan(batch)

        for step in plan:
            self.registry.get(step.command)

            # Execution will be implemented in later PRs.
            # Current phase only validates orchestration structure.
            print(f"[BATCH] planned step: {step.id} -> {step.command}")
