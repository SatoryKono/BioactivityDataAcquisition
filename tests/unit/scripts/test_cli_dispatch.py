# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Regression tests for shared script router dispatch helpers."""

from __future__ import annotations

import pytest

from pathlib import Path
import subprocess
import sys

from scripts.engineering.common.cli_dispatch import module_command, run_command


pytestmark = pytest.mark.unit


def _write_module(
    tmp_path: Path,
    *,
    package_name: str,
    module_name: str,
    source: str,
) -> str:
    package_root = tmp_path / package_name
    package_root.mkdir()
    (package_root / "__init__.py").write_text("", encoding="utf-8")
    (package_root / f"{module_name}.py").write_text(source, encoding="utf-8")
    return f"{package_name}.{module_name}"


def test_run_command_dispatches_module_main_with_argv_in_process(
    tmp_path: Path,
    monkeypatch,
) -> None:
    target = _write_module(
        tmp_path,
        package_name="dispatch_pkg_argv",
        module_name="argv_target",
        source="""
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

    exit_code = run_command(module_command(target), ["--flag", "value"])

    assert exit_code == 7


def test_run_command_dispatches_module_main_without_argv_in_process(
    tmp_path: Path,
    monkeypatch,
) -> None:
    target = _write_module(
        tmp_path,
        package_name="dispatch_pkg_sys_argv",
        module_name="sys_argv_target",
        source="""
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

    exit_code = run_command(module_command(target), ["--check"])

    assert exit_code == 0
    assert sys.argv == original_argv
