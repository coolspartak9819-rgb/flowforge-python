from app.schemas import WorkflowCreate


def test_workflow_definition_accepts_supported_steps() -> None:
    workflow = WorkflowCreate(
        name="demo",
        steps=[{"name": "wait", "kind": "delay", "seconds": 1}],
    )

    assert workflow.steps[0].kind == "delay"


def test_workflow_definition_rejects_unknown_step_kind() -> None:
    try:
        WorkflowCreate(name="demo", steps=[{"name": "bad", "kind": "unknown"}])
    except ValueError:
        return
    raise AssertionError("unknown step kind was accepted")
