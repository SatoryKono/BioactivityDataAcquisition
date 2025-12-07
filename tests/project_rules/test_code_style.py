from __future__ import annotations

import shutil
import subprocess

import pytest


def _run_tool(cmd: list[str]) -> None:
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        pytest.fail(
            f"Команда {' '.join(cmd)} завершилась с кодом {result.returncode}\n"
            f"stdout:\n{stdout}\n\nstderr:\n{stderr}"
        )


@pytest.mark.parametrize(
    "binary, args",
    [
        ("black", ["--check", "."]),
        ("isort", ["--check-only", "."]),
        ("ruff", ["check", ".", "--extend-ignore", "I001"]),
    ],
)
def test_code_style_tools(binary: str, args: list[str]) -> None:
    if shutil.which(binary) is None:
        pytest.skip(f"{binary} не установлен в окружении")
    _run_tool([binary, *args])
