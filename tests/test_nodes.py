import pytest
from app.graph.nodes import fetch_pr_node
from app.graph.nodes import lint_code_node
from types import SimpleNamespace
from app.graph.nodes import propose_refactor_node
from app.graph.nodes import apply_changes_node

def test_fetch_pr_node():

    state = {
        "pr_url": "https://github.com/user/repo/pull/10",
        "code_contents": {},
        "lint_errors": [],
        "refactored_code": {},
        "is_approved": False,
        "reviewer_feedback": "",
        "history": []
    }

    result = fetch_pr_node(state)

    assert "main.py" in result["code_contents"]

    assert "add" in result["code_contents"]["main.py"]

    print(result)
    
def test_lint_code_node():

    state = {
        "pr_url": "https://github.com/user/repo/pull/10",

        "code_contents": {
            "main.py": """
def add(a,b):
 return a+b
"""
        },

        "lint_errors": [],

        "refactored_code": {},

        "is_approved": False,

        "reviewer_feedback": "",

        "history": []
    }

    result = lint_code_node(state)

    assert len(result["lint_errors"]) > 0

    assert result["lint_errors"][0]["file"] == "main.py"    
 
 
def test_propose_refactor_node(monkeypatch):

    # Mock LLM class
    class FakeLLM:

        def __init__(self, **kwargs):
            pass

        def invoke(self, messages):

            return SimpleNamespace(
                content="def add(a, b):\n    return a + b"
            )

    # Replace actual ChatOpenAI with FakeLLM
    monkeypatch.setattr(
        "app.graph.nodes.ChatOpenAI",
        FakeLLM
    )

    state = {
        "pr_url": "https://github.com/user/repo/pull/10",

        "code_contents": {
            "main.py": "def add(a,b): return a+b"
        },

        "lint_errors": [
            {
                "file": "main.py",
                "errors": "E231 missing whitespace after comma"
            }
        ],

        "refactored_code": {},

        "is_approved": False,

        "reviewer_feedback": "",

        "history": []
    }

    result = propose_refactor_node(state)

    # Verify generated code
    assert "main.py" in result["refactored_code"]

    assert "def add(a, b):" in result["refactored_code"]["main.py"]

    # Verify history
    assert len(result["history"]) == 1

    assert result["history"][0]["action"] == "refactoring_generated"    


def test_apply_changes_node(monkeypatch):

    # Fake GitHub API response
    class FakeResponse:

        def __init__(self, data):
            self.data = data

        def json(self):
            return self.data

        def raise_for_status(self):
            pass

    # Fake GitHub HTTP client
    class FakeClient:

        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, url):

            if "/pulls/" in url:
                return FakeResponse({
                    "head": {
                        "ref": "feature-branch",
                        "sha": "old_commit",
                        "repo": {
                            "owner": {
                                "login": "user"
                            },
                            "name": "repo"
                        }
                    }
                })

            return FakeResponse({
                "tree": {
                    "sha": "base_tree"
                }
            })

        def post(self, url, json):

            if "/git/blobs" in url:
                return FakeResponse({"sha": "blob_sha"})

            if "/git/trees" in url:
                return FakeResponse({"sha": "tree_sha"})

            if "/git/commits" in url:
                return FakeResponse({"sha": "new_commit"})

        def patch(self, url, json):
            return FakeResponse({"ref": "refs/heads/feature-branch"})

    # Mock GitHub token
    monkeypatch.setenv("GITHUB_TOKEN", "fake_token")

    # Replace actual HTTP client
    monkeypatch.setattr(
        "app.graph.nodes.httpx.Client",
        FakeClient
    )

    state = {
        "pr_url": "https://github.com/user/repo/pull/10",

        "code_contents": {},

        "lint_errors": [],

        "refactored_code": {
            "main.py": "def add(a, b):\n    return a + b"
        },

        "is_approved": True,

        "reviewer_feedback": "Looks good",

        "history": []
    }

    result = apply_changes_node(state)

    # Verify GitHub commit
    assert result["history"][0]["commit_sha"] == "new_commit"

    # Verify updated files
    assert result["history"][0]["files_updated"] == ["main.py"]

    # Verify history
    assert result["history"][0]["action"] == "changes_applied"    
    
def test_apply_changes_without_approval():

    state = {
        "is_approved": False,
        "pr_url": "https://github.com/user/repo/pull/10"
    }

    with pytest.raises(PermissionError):
        apply_changes_node(state)