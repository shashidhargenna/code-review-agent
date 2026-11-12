import tempfile
import subprocess
import sys

from pathlib import Path
from langchain_core.tools import tool


@tool
def run_linter_tool(code_string: str) -> str:
    """
    Analyzes Python code using Flake8.
    Returns linting errors and execution results.
    """

    try:

        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:

            # Create a Python file
            file_path = Path(temp_dir) / "review_code.py"

            # Write code into the file
            file_path.write_text(code_string, encoding="utf-8")

            # Execute Flake8
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "flake8",
                    str(file_path)
                ],
                capture_output=True,
                text=True,
                timeout=10
            )

            # Capture results
            if result.returncode == 0:

                return "No linting errors found."

            return result.stdout + result.stderr

    except subprocess.TimeoutExpired:

        return "Linting process timed out."

    except Exception as e:

        return f"Linting failed: {str(e)}"
    