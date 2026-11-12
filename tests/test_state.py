from app.graph.state import ReviewState


def test_review_state():

    state: ReviewState = {

        "pr_url": "https://github.com/user/repo/pull/10",

        "code_contents": {},

        "lint_errors": [],

        "refactored_code": {},

        "is_approved": False,

        "reviewer_feedback": "",

        "history": []
    }

    assert state["is_approved"] is False

    assert state["lint_errors"] == []

    assert state["reviewer_feedback"] == ""
    