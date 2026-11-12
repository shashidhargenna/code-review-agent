from app.graph.workflow import compile_workflow


def test_workflow_compilation():

    app = compile_workflow()

    assert app is not None

    print("Workflow compiled successfully!")