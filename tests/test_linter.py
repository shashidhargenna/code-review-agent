from app.tools.linter_tool import run_linter_tool


def test_linter_detects_errors():

    bad_code = """
def add(a,b):
 return a+b
"""

    result = run_linter_tool.invoke({
        "code_string": bad_code
    })

    assert "E" in result or "F" in result


def test_linter_valid_code():

    good_code = """
def add(a, b):
    return a + b
"""

    result = run_linter_tool.invoke({
        "code_string": good_code
    })

    assert result == "No linting errors found."