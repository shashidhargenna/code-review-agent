import uuid

from dotenv import load_dotenv
from fastapi import FastAPI
from langgraph.types import Command

from app.graph.workflow import compile_workflow
from app.api.routes import router, workflow_app


# Load environment variables
load_dotenv()


# Create FastAPI application
api = FastAPI(
    title="AI Code Review Agent",
    description="Autonomous Code Review and Refactoring Agent using LangGraph",
    version="1.0.0"
)


# Register API routes
api.include_router(router)


def main():

    print("\n===================================")
    print("       AI CODE REVIEW AGENT")
    print("===================================\n")

    # Compile workflow for terminal execution
    app = compile_workflow()

    # Step 1: Get GitHub PR URL
    pr_url = input("Enter GitHub Pull Request URL: ")

    # Step 2: Configure workflow thread
    config = {
        "configurable": {
            "thread_id": str(uuid.uuid4())
        }
    }

    # Step 3: Initialize shared state
    initial_state = {
        "pr_url": pr_url,
        "code_contents": {},
        "lint_errors": [],
        "refactored_code": {},
        "is_approved": False,
        "reviewer_feedback": "",
        "history": []
    }

    print("\nStarting Code Review Workflow...\n")

    # Step 4: Execute workflow
    result = app.invoke(
        initial_state,
        config=config
    )

       # Step 5: Handle human approval and rejection feedback loop
    while "__interrupt__" in result:

        print("\n===================================")
        print("       REFACTORED CODE")
        print("===================================\n")

        refactored_code = result.get(
            "refactored_code", {}
        )

        for filename, code in refactored_code.items():

            print(f"\nFilename: {filename}")
            print("-----------------------------------")
            print(code)
            print("-----------------------------------")

        # Ask for human approval
        while True:

            approval = input(
                "\nDo you approve these changes? (yes/no): "
            ).strip().lower()

            if approval in ["yes", "no"]:
                break

            print("Please enter either yes or no.")

        # Prepare approval decision
        if approval == "yes":

            decision = {
                "approved": True,
                "feedback": ""
            }

        else:

            feedback = input(
                "Please provide your feedback: "
            )

            decision = {
                "approved": False,
                "feedback": feedback
            }

        # Resume the interrupted workflow
        result = app.invoke(
            Command(resume=decision),
            config=config
        )

        print("\nWorkflow resumed.")

    # Workflow completed
    print("\n===================================")
    print("       WORKFLOW COMPLETED")
    print("===================================\n")

    print("Final Workflow State:")
    print(result)


if __name__ == "__main__":
    main()