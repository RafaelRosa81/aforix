from aforix.batch.models import BatchDefinition, BatchStep, ExecutionOptions
from aforix.batch.planner import BatchPlanner


planner = BatchPlanner()


def _batch_definition() -> BatchDefinition:
    return BatchDefinition(
        version=1,
        batch_id="test",
        name="Test",
        description="",
        main_config="configs/examples/main.yaml",
        execution=ExecutionOptions(),
        variables={"format": "xlsx"},
        steps=[
            BatchStep(id="a", command="config-check"),
            BatchStep(id="b", command="normalize.run", params={"format": "${format}"}),
            BatchStep(id="c", command="validate.run", enabled=False),
        ],
    )


def test_planner_skips_disabled_steps() -> None:
    plan = planner.build_execution_plan(_batch_definition())

    assert len(plan) == 2
    assert all(step.id != "c" for step in plan)


def test_planner_resolves_variables() -> None:
    plan = planner.build_execution_plan(_batch_definition())

    assert plan[1].params["format"] == "xlsx"


def test_planner_only_step() -> None:
    plan = planner.build_execution_plan(
        _batch_definition(),
        only_step="b",
    )

    assert len(plan) == 1
    assert plan[0].id == "b"
