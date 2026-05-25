"""Regression tests for shared script router dispatch helpers."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from scripts.engineering.common.cli_dispatch import module_command, run_command


def _write_module(tmp_path: Path, module_name: str, source: str) -> None:
    package_root = tmp_path / "dispatch_pkg"
    package_root.mkdir()
    (package_root / "__init__.py").write_text("", encoding="utf-8")
    (package_root / f"{module_name}.py").write_text(source, encoding="utf-8")


def test_run_command_dispatches_module_main_with_argv_in_process(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_module(
        tmp_path,
        "argv_target",
        """
from __future__ import annotations


def main(argv: list[str] | None = None) -> int:
    assert argv == ["--flag", "value"]
    return 7
""".strip()
        + "\n",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("module dispatch must not spawn subprocesses")
        ),
    )

    exit_code = run_command(module_command("dispatch_pkg.argv_target"), ["--flag", "value"])

    assert exit_code == 7


def test_run_command_dispatches_module_main_without_argv_in_process(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_module(
        tmp_path,
        "sys_argv_target",
        """
from __future__ import annotations

import sys


def main() -> int:
    assert sys.argv[1:] == ["--check"]
    return 0
""".strip()
        + "\n",
    )
    original_argv = list(sys.argv)
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("module dispatch must not spawn subprocesses")
        ),
    )

    exit_code = run_command(module_command("dispatch_pkg.sys_argv_target"), ["--check"])

    assert exit_code == 0
    assert sys.argv == original_argv
