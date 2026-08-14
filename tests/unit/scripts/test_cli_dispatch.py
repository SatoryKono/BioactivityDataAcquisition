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


def test_run_command_rejects_argv_for_zero_argument_module_main(
    tmp_path: Path,
    monkeypatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    target = _write_module(
        tmp_path,
        package_name="dispatch_pkg_sys_argv",
        module_name="sys_argv_target",
        source="""
from __future__ import annotations

import sys


def main() -> int:
    raise AssertionError("zero-argument main must not run with forwarded argv")
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

    assert exit_code == 2
    assert sys.argv == original_argv
    assert "does not accept command arguments" in capsys.readouterr().err


def test_run_command_dispatches_zero_argument_main_without_forwarded_argv(
    tmp_path: Path,
    monkeypatch,
) -> None:
    target = _write_module(
        tmp_path,
        package_name="dispatch_pkg_zero_argv",
        module_name="zero_argv_target",
        source="""
from __future__ import annotations


def main() -> int:
    return 9
""".strip()
        + "\n",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    assert run_command(module_command(target), []) == 9


def test_docs_check_drift_and_docstrings_accept_documented_flags(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """#8756: documented sliced flags must reach argparse, not dispatcher rc=2."""
    drift_rc = run_command(
        module_command("scripts.docs.checks.check_drift"),
        ["--help"],
    )
    docstrings_rc = run_command(
        module_command("scripts.docs.checks.check_docstrings"),
        ["--help"],
    )
    captured = capsys.readouterr()

    assert drift_rc == 0
    assert docstrings_rc == 0
    assert "does not accept command arguments" not in captured.err
    assert "--ports" in captured.out
    assert "--summary" in captured.out


def test_docs_verify_and_kpi_accept_workflow_flags(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exact docs workflow flags must reach argparse instead of router rc=2."""
    from scripts.docs.checks import report_docs_kpi, verify

    monkeypatch.setattr(verify, "_run_step", lambda _label, _argv: 0)
    metrics = report_docs_kpi.DocsKpiMetrics(
        generated_at_utc="2026-08-14T00:00:00+00:00",
        total_docs=1,
        in_nav=1,
        not_in_nav=0,
        orphan_candidates=0,
        baseline_not_in_nav=0,
        baseline_exists=True,
        not_in_nav_top_level={},
        orphan_top_level={},
        target_not_in_nav=120,
        hard_limit_not_in_nav=135,
        max_orphans=0,
        target_deadline="2026-12-31",
        deadline_days_remaining=139,
        status="on_track",
        breaches=[],
    )
    monkeypatch.setattr(
        report_docs_kpi,
        "compute_metrics",
        lambda **_kwargs: metrics,
    )

    verify_rc = run_command(
        module_command("scripts.docs.checks.verify"),
        ["--skip-build"],
    )
    kpi_rc = run_command(
        module_command("scripts.docs.checks.report_docs_kpi"),
        [
            "--kpi-target-not-in-nav",
            "120",
            "--hard-limit-not-in-nav",
            "135",
            "--max-orphans",
            "0",
            "--target-deadline",
            "2026-12-31",
            "--fail-on-breach",
        ],
    )
    captured = capsys.readouterr()

    assert verify_rc == 0
    assert kpi_rc == 0
    assert "does not accept command arguments" not in captured.err
