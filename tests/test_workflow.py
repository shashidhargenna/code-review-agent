from app.graph.workflow import compile_workflow
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from app.graph.workflow import build_workflow

def test_workflow_compilation():

    app = compile_workflow()

    assert app is not None

    print("Workflow compiled successfully!")



def test_rejection_feedback_loops_back_to_approval(monkeypatch):

    generated_feedback = []

    def fake_fetch(state):
        return {
            "code_contents": {
                "main.py": "def add(a,b): return a+b"
            }
        }

    def fake_lint(state):
        return {"lint_errors": []}

    def fake_refactor(state):

        feedback = state.get("reviewer_feedback", "")
        generated_feedback.append(feedback)

        return {
            "refactored_code": {
                "main.py": "def add(first_number, second_number): return first_number + second_number"
            },
            "history": list(state.get("history", [])) + [
                {
                    "action": "refactoring_generated",
                    "feedback": feedback
                }
            ]
        }

    def fake_apply(state):
        return {"history": state.get("history", [])}

    monkeypatch.setattr("app.graph.workflow.fetch_pr_node", fake_fetch)
    monkeypatch.setattr("app.graph.workflow.lint_code_node", fake_lint)
    monkeypatch.setattr("app.graph.workflow.propose_refactor_node", fake_refactor)
    monkeypatch.setattr("app.graph.workflow.apply_changes_node", fake_apply)

    app = build_workflow().compile(
        checkpointer=InMemorySaver()
    )

    config = {
        "configurable": {
            "thread_id": "feedback-loop-test"
        }
    }

    initial_state = {
        "pr_url": "https://github.com/user/repo/pull/10",
        "code_contents": {},
        "lint_errors": [],
        "refactored_code": {},
        "is_approved": False,
        "reviewer_feedback": "",
        "history": []
    }

    first_result = app.invoke(initial_state, config=config)

    assert "__interrupt__" in first_result
    assert generated_feedback == [""]

    second_result = app.invoke(
        Command(resume={
            "approved": False,
            "feedback": "Use descriptive variable names."
        }),
        config=config
    )

    assert "__interrupt__" in second_result

    assert generated_feedback == [
        "",
        "Use descriptive variable names."
    ]

    assert second_result["reviewer_feedback"] == "Use descriptive variable names."
    assert second_result["is_approved"] is False    