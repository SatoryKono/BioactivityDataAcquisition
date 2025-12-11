from __future__ import annotations

import subprocess
import sys

import pytest


def _run_tool(module: str, args: list[str]) -> None:
    cmd = [sys.executable, "-m", module, *args]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        message = (
            "Команда "
            f"{' '.join(cmd)} "
            f"завершилась с кодом {result.returncode}\n"
            f"stdout:\n{stdout}\n\nstderr:\n{stderr}"
        )
        pytest.fail(message)


@pytest.mark.parametrize(
    "module, args",
    [
        ("black", ["--check", "."]),
        ("isort", ["--check-only", "."]),
        ("ruff", ["check", ".", "--extend-ignore", "I001"]),
        (
            "xenon",
            [
                "--max-absolute",
                "B",
                "--max-modules",
                "B",
                "--max-average",
                "B",
                "--exclude",
                "tests/*,src/tools/*",
                "src",
            ],
        ),
    ],
)
def test_code_style_tools(module: str, args: list[str]) -> None:
    _run_tool(module, args)
