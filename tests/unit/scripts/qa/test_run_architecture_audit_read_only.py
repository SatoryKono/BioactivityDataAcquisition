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
"""Unit tests for read-only architecture audit command wiring."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from scripts.engineering.qa import run_architecture_audit_read_only as audit_lane


pytestmark = pytest.mark.unit


def test_architecture_audit_checks_are_check_only() -> None:
    checks = audit_lane.architecture_audit_checks()
    commands = {check.name: check.command for check in checks}

    assert set(commands) == {
        "contract_coverage_matrix",
        "domain_aggregate_invariant_registry",
        "domain_io_taint_inventory",
        "import_linter_contracts",
        "runtime_import_scc",
        "module_coverage_inventory",
        "observability_metric_inventory",
        "port_adapter_factory_coverage",
        "hotspot_family_baseline",
        "remote_main_debt_baseline",
        "debt_governance_gates",
    }
    for command in commands.values():
        assert "--update" not in command
        assert "--write" not in command
        assert (
            "--check" in command or "pytest" in command or "lint-imports" in command[0]
        )


def test_runtime_scc_check_disables_pytest_cacheprovider() -> None:
    commands = {
        check.name: check.command for check in audit_lane.architecture_audit_checks()
    }

    runtime_scc = commands["runtime_import_scc"]
    assert "-m" in runtime_scc
    assert "pytest" in runtime_scc
    assert "-p" in runtime_scc
    assert "no:cacheprovider" in runtime_scc
    assert "tests/architecture/test_runtime_import_scc.py" in runtime_scc


def test_mutation_guard_scope_is_limited_to_tracked_governance_surfaces() -> None:
    assert audit_lane.MUTATION_GUARD_PATHS == (
        ".github",
        "configs/quality",
        "docs",
        "reports/quality",
        "scripts",
        "src/bioetl",
        "tests",
    )


def test_mutation_guard_status_timeout_is_unavailable() -> None:
    assert audit_lane.GIT_STATUS_TIMEOUT_SECONDS == 120
    assert audit_lane._git_status_unavailable(("<git-status-timeout>", "")) is True
    assert audit_lane._git_status_unavailable((" M src/bioetl/example.py",)) is False


def test_mutation_guard_git_status_disables_lfs_filters() -> None:
    command = audit_lane._git_status_command(("src/bioetl", "tests"))

    assert command[:2] == ("git", "-c")
    assert "filter.lfs.clean=" in command
    assert "filter.lfs.smudge=" in command
    assert "filter.lfs.process=" in command
    assert "filter.lfs.required=false" in command
    assert command[-3:] == ("--", "src/bioetl", "tests")


def test_audit_environment_prepends_src_and_preserves_caller_values() -> None:
    repo_root = Path("/workspace/repo")

    env = audit_lane._audit_environment(
        repo_root,
        environ={"PYTHONPATH": "caller-path", "CALLER_FLAG": "kept"},
    )

    assert env["PYTHONPATH"] == os.pathsep.join(
        (str((repo_root / "src").resolve()), "caller-path")
    )
    assert env["CALLER_FLAG"] == "kept"
    assert env["PYTHONDONTWRITEBYTECODE"] == "1"
