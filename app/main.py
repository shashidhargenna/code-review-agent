import uuid

from dotenv import load_dotenv
from langgraph.types import Command

from app.graph.workflow import compile_workflow


# Load environment variables
load_dotenv()


# Compile LangGraph workflow
app = compile_workflow()


def main():

    print("\n===================================")
    print("       AI CODE REVIEW AGENT")
    print("===================================\n")

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

    # Step 5: Handle human approval interrupt
    if "__interrupt__" in result:

        print("\n===================================")
        print("       REFACTORED CODE")
        print("===================================\n")

        # Display generated code
        refactored_code = result.get(
            "refactored_code", {}
        )

        for filename, code in refactored_code.items():

            print(f"\nFilename: {filename}")
            print("-----------------------------------")
            print(code)
            print("-----------------------------------")

        # Ask for human approval
        approval = input(
            "\nDo you approve these changes? (yes/no): "
        ).strip().lower()

        # Step 6: Resume workflow
        if approval == "yes":

            print("\nApproval received!")
            print("Applying changes to GitHub...\n")

            result = app.invoke(
                Command(resume=True),
                config=config
            )

        else:

            print("\nChanges rejected by reviewer.")

            result = app.invoke(
                Command(resume=False),
                config=config
            )

    # Step 7: Display final result
    print("\n===================================")
    print("       WORKFLOW COMPLETED")
    print("===================================\n")

    print("Final Workflow State:")

    print(result)

    print("\nCode Review Agent execution finished.")


if __name__ == "__main__":
    main()