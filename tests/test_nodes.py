import pytest
from app.graph.nodes import fetch_pr_node
from app.graph.nodes import lint_code_node
from types import SimpleNamespace
from app.graph.nodes import propose_refactor_node
from app.graph.nodes import apply_changes_node

def test_fetch_pr_node(monkeypatch):

    # Simulate GitHub API responses
    class FakeResponse:

        def __init__(self, data):
            self.data = data

        def json(self):
            return self.data

        def raise_for_status(self):
            pass

    # Simulate GitHub HTTP client
    class FakeClient:

        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, url, params=None):

            # Step 1: Return PR information
            if "/pulls/10" in url and "/files" not in url:
                return FakeResponse({
                    "head": {
                        "sha": "test_commit_sha",
                        "repo": {
                            "owner": {
                                "login": "user"
                            },
                            "name": "repo"
                        }
                    }
                })

            # Step 2: Return modified file list
            if "/pulls/10/files" in url:
                return FakeResponse([
                    {
                        "filename": "sample.py",
                        "status": "modified"
                    }
                ])

            # Step 3: Return actual file content (simulated)
            if "/contents/sample.py" in url:
                import base64

                code = "def add(a,b):\n return a+b"

                encoded_code = base64.b64encode(
                    code.encode("utf-8")
                ).decode("utf-8")

                return FakeResponse({
                    "encoding": "base64",
                    "content": encoded_code
                })

            raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setenv("GITHUB_TOKEN", "fake_token")

    monkeypatch.setattr(
        "app.graph.nodes.httpx.Client",
        FakeClient
    )

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

    # Verify actual filename was retrieved
    assert "sample.py" in result["code_contents"]

    # Verify decoded Python code
    assert "def add(a,b):" in result["code_contents"]["sample.py"]
    
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



def test_lint_code_node_continues_after_syntax_error(monkeypatch):

    calls = []

    def fake_linter_tool(code_string):
        calls.append(code_string)

        if "def broken(:" in code_string:
            return "E999 SyntaxError: invalid syntax"

        if "def add(a,b):" in code_string:
            return "E231 missing whitespace after comma"

        return "No linting errors found."

    monkeypatch.setattr(
    "app.graph.nodes.run_linter_tool",
    SimpleNamespace(
        invoke=lambda payload: fake_linter_tool(payload["code_string"])
    )
) 

    state = {
        "code_contents": {
            "broken.py": "def broken(:\n    pass\n",
            "style_issue.py": "def add(a,b):\n    return a+b\n",
            "clean.py": "def add(a, b):\n    return a + b\n"
        }
    }

    result = lint_code_node(state)

    # All three files should be checked.
    assert len(calls) == 3

    # Both problematic files should be reported.
    assert [item["file"] for item in result["lint_errors"]] == [
        "broken.py",
        "style_issue.py"
    ]

    assert "E999" in result["lint_errors"][0]["errors"]
    assert "E231" in result["lint_errors"][1]["errors"]        