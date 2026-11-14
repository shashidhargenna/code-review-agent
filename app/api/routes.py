import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from langgraph.types import Command

from app.graph.workflow import compile_workflow


# Create API router
router = APIRouter()

# Compile LangGraph workflow once
workflow_app = compile_workflow()


# GitHub webhook request model
class GitHubWebhook(BaseModel):
    action: str
    pull_request: dict


# Human review request model
class ReviewDecision(BaseModel):
    approved: bool
    feedback: str = ""


# ==========================================
# ENDPOINT 1: GitHub PR Webhook
# ==========================================

@router.post("/api/webhooks/github")
def github_webhook(payload: GitHubWebhook):

    # Accept only relevant PR events
    if payload.action not in ["opened", "synchronize", "reopened"]:
        return {
            "message": "Event ignored",
            "action": payload.action
        }

    # Extract PR URL
    pr_url = payload.pull_request.get("html_url")

    if not pr_url:
        raise HTTPException(
            status_code=400,
            detail="Pull Request URL is missing."
        )

    # Generate unique review thread
    thread_id = str(uuid.uuid4())

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    # Initial LangGraph state
    initial_state = {
        "pr_url": pr_url,
        "code_contents": {},
        "lint_errors": [],
        "refactored_code": {},
        "is_approved": False,
        "reviewer_feedback": "",
        "history": []
    }

    try:

        # Start LangGraph workflow
        result = workflow_app.invoke(
            initial_state,
            config=config
        )

        return {
            "message": "Code review started",
            "thread_id": thread_id,
            "pr_url": pr_url,
            "status": (
                "awaiting_approval"
                if "__interrupt__" in result
                else "completed"
            ),
            "refactored_code": result.get(
                "refactored_code", {}
            )
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ==========================================
# ENDPOINT 2: Human Approval
# ==========================================

@router.post("/api/reviews/{thread_id}/approve")
def approve_review(thread_id: str, decision: ReviewDecision):

    # Retrieve existing workflow configuration
    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    try:

        # Retrieve saved workflow state
        current_state = workflow_app.get_state(config)

        if not current_state.values:
            raise HTTPException(
                status_code=404,
                detail="Review session not found."
            )

        # Check whether workflow is waiting for approval
        if not current_state.tasks or not current_state.tasks[0].interrupts:
            raise HTTPException(
                status_code=409,
                detail="This review is not waiting for approval."
            )

        # Resume workflow with approval or rejection
        result = workflow_app.invoke(
            Command(
                resume={
                    "approved": decision.approved,
                    "feedback": decision.feedback
                }
            ),
            config=config
        )

        return {
            "message": (
                "Changes approved"
                if decision.approved
                else "Changes rejected"
            ),
            "thread_id": thread_id,
            "status": (
                "completed"
                if decision.approved
                else "rejected"
            ),
            "result": result
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )