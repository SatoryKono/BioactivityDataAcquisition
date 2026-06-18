"""Unit tests for read-only architecture audit command wiring."""

from __future__ import annotations

import pytest

from scripts.engineering.qa import run_architecture_audit_read_only as audit_lane


pytestmark = pytest.mark.unit


def test_architecture_audit_checks_are_check_only() -> None:
    checks = audit_lane.architecture_audit_checks()
    commands = {check.name: check.command for check in checks}

    assert set(commands) == {
        "import_linter_contracts",
        "runtime_import_scc",
        "module_coverage_inventory",
        "hotspot_family_baseline",
        "remote_main_debt_baseline",
        "debt_governance_gates",
    }
    for command in commands.values():
        assert "--update" not in command
        assert "--write" not in command
        assert "--check" in command or "pytest" in command or "lint-imports" in command[0]


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
