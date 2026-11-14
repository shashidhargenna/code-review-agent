import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver

from langgraph.graph import StateGraph, START, END

from app.graph.state import ReviewState

from app.graph.nodes import (
    fetch_pr_node,
    lint_code_node,
    propose_refactor_node,
    human_approval_node,
    apply_changes_node
)


def route_after_approval(state: ReviewState):

    if state["is_approved"]:
        return "apply_changes"

    return "propose_refactor"


def build_workflow():

    workflow = StateGraph(ReviewState)

    # Register nodes
    workflow.add_node("fetch_pr", fetch_pr_node)
    workflow.add_node("lint_code", lint_code_node)
    workflow.add_node("propose_refactor", propose_refactor_node)
    workflow.add_node("human_approval", human_approval_node)
    workflow.add_node("apply_changes", apply_changes_node)

    # Sequential execution
    workflow.add_edge(START, "fetch_pr")
    workflow.add_edge("fetch_pr", "lint_code")
    workflow.add_edge("lint_code", "propose_refactor")
    workflow.add_edge("propose_refactor", "human_approval")

    # Conditional routing after human approval
    workflow.add_conditional_edges(
        "human_approval",
        route_after_approval,
        {
            "apply_changes": "apply_changes",
            "propose_refactor": "propose_refactor"
        }
    )

    # Finish after applying approved changes
    workflow.add_edge("apply_changes", END)

    return workflow


def compile_workflow():

    # Create SQLite database connection
    conn = sqlite3.connect(
        "checkpoints.sqlite",
        check_same_thread=False
    )

    # Create SQLite checkpointer
    checkpointer = SqliteSaver(conn)

    # Initialize checkpoint storage
    checkpointer.setup()

    # Compile the graph with checkpointing
    app = build_workflow().compile(
        checkpointer=checkpointer
    )

    return app