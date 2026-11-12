import os
import re
import httpx
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.graph.state import ReviewState
from app.tools.linter_tool import run_linter_tool
from langgraph.types import interrupt

load_dotenv()

def fetch_pr_node(state: ReviewState):

    """
    Fetches modified files from a GitHub Pull Request.
    Currently using mock data for development.
    """

    print("Fetching Pull Request...")

    # Mock GitHub PR code
    mock_code = {
        "main.py": """
def add(a,b):
 return a+b


def multiply(a,b):
    return a*b
"""
    }

    return {
        "code_contents": mock_code
    }
    
def lint_code_node(state: ReviewState):

    """
    Analyzes all Python files using the linter tool.
    """

    print("Running code analysis...")

    all_errors = []

    # Get original code from shared state
    code_files = state["code_contents"]

    # Analyze each Python file
    for filename, code in code_files.items():

        if filename.endswith(".py"):

            result = run_linter_tool.invoke({
                "code_string": code
            })

            if result != "No linting errors found.":

                all_errors.append({
                    "file": filename,
                    "errors": result
                })

    return {
        "lint_errors": all_errors
    }

 
def propose_refactor_node(state: ReviewState):

    print("Generating refactored code...")

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0
    )

    original_files = state["code_contents"]
    lint_errors = state["lint_errors"]
    reviewer_feedback = state.get("reviewer_feedback", "")

    refactored_files = {}

    for filename, original_code in original_files.items():

        file_errors = [
            error["errors"]
            for error in lint_errors
            if error["file"] == filename
        ]

        messages = [

            SystemMessage(
                content="""
You are an expert Python developer.

Fix the linting errors.
Improve code readability.
Preserve the original functionality.
Consider reviewer feedback.

Return ONLY the complete Python source code.
Do not include Markdown code fences.
"""
            ),

            HumanMessage(
                content=f"""
Filename: {filename}

Original code:
{original_code}

Linting errors:
{file_errors}

Reviewer feedback:
{reviewer_feedback}

Generate the refactored code.
"""
            )
        ]

        response = llm.invoke(messages)

        refactored_files[filename] = response.content.strip()

    history = list(state.get("history", []))

    history.append({
        "action": "refactoring_generated",
        "feedback": reviewer_feedback
    })

    return {
        "refactored_code": refactored_files,
        "history": history
    }  
    
      
    
def apply_changes_node(state: ReviewState):

    """
    Applies approved refactored code to the GitHub PR branch.
    """

    print("Applying approved changes to GitHub...")

    # Safety check: Never modify GitHub without approval
    if not state["is_approved"]:
        raise PermissionError(
            "Changes cannot be applied without human approval."
        )

    token = os.getenv("GITHUB_TOKEN")

    if not token:
        raise ValueError("GitHub token is missing.")

    # Extract repository information from PR URL
    pr_url = state["pr_url"]

    match = re.fullmatch(
        r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)/?",
        pr_url
    )

    if not match:
        raise ValueError("Invalid GitHub Pull Request URL.")

    owner, repo, pr_number = match.groups()

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    with httpx.Client(
        headers=headers,
        timeout=30
    ) as client:

        # Step 1: Get Pull Request information
        pr_response = client.get(
            f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
        )

        pr_response.raise_for_status()

        pr_data = pr_response.json()

        head = pr_data["head"]

        branch = head["ref"]
        head_sha = head["sha"]

        head_repo = head["repo"]

        if head_repo is None:
            raise ValueError("PR source repository is unavailable.")

        target_owner = head_repo["owner"]["login"]
        target_repo = head_repo["name"]

        # Step 2: Get the current commit's tree
        commit_response = client.get(
            f"https://api.github.com/repos/{target_owner}/{target_repo}/git/commits/{head_sha}"
        )

        commit_response.raise_for_status()

        base_tree = commit_response.json()["tree"]["sha"]

        # Step 3: Create Git blobs for refactored files
        tree_entries = []

        for filename, code in state["refactored_code"].items():

            blob_response = client.post(
                f"https://api.github.com/repos/{target_owner}/{target_repo}/git/blobs",
                json={
                    "content": code,
                    "encoding": "utf-8"
                }
            )

            blob_response.raise_for_status()

            blob_sha = blob_response.json()["sha"]

            tree_entries.append({
                "path": filename,
                "mode": "100644",
                "type": "blob",
                "sha": blob_sha
            })

        # Step 4: Create a new Git tree
        tree_response = client.post(
            f"https://api.github.com/repos/{target_owner}/{target_repo}/git/trees",
            json={
                "base_tree": base_tree,
                "tree": tree_entries
            }
        )

        tree_response.raise_for_status()

        tree_sha = tree_response.json()["sha"]

        # Step 5: Create a commit
        new_commit = client.post(
            f"https://api.github.com/repos/{target_owner}/{target_repo}/git/commits",
            json={
                "message": "Apply AI-generated code refactoring",
                "tree": tree_sha,
                "parents": [head_sha]
            }
        )

        new_commit.raise_for_status()

        commit_sha = new_commit.json()["sha"]

        # Step 6: Update the PR source branch
        from urllib.parse import quote

        encoded_branch = quote(branch, safe="")

        update_response = client.patch(
            f"https://api.github.com/repos/{target_owner}/{target_repo}/git/refs/heads/{encoded_branch}",
            json={
                "sha": commit_sha,
                "force": False
            }
        )

        update_response.raise_for_status()

    # Update workflow history
    history = list(state.get("history", []))

    history.append({
        "action": "changes_applied",
        "commit_sha": commit_sha,
        "files_updated": list(state["refactored_code"].keys())
    })

    print("GitHub changes successfully committed.")

    return {
        "history": history
    }


def human_approval_node(state: ReviewState):

    decision = interrupt({
        "message": "Do you approve these refactored changes?",
        "refactored_code": state["refactored_code"]
    })

    return {
        "is_approved": decision
    }    