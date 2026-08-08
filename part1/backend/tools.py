import subprocess
import sys

from langchain_core.tools import tool

TIMEOUT_SECONDS = 30


@tool
def execute_python(code: str) -> str:
    """Execute Python code and return its output.

    Use this for calculations, data processing, and anything that needs an
    exact answer. Print the results you want to read back.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return f"return_code=-1 stderr=timed out after {TIMEOUT_SECONDS}s"

    return (
        f"return_code={result.returncode}\n"
        f"stdout={result.stdout.strip()}\n"
        f"stderr={result.stderr.strip()}"
    )


TOOLS = [execute_python]
