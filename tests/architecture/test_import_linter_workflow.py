"""Architecture tests for the non-skippable import-linter CI gate."""

from __future__ import annotations

from pathlib import Path

import pytest


pytestmark = pytest.mark.architecture


def test_import_linter_workflow_runs_for_all_pr_and_push_changes() -> None:
    """Import-linter gate must always materialize for PR and push events."""
    workflow = Path(".github/workflows/import-linter.yml").read_text(encoding="utf-8")

    assert "pull_request:" in workflow
    assert "push:" in workflow
    assert "workflow_dispatch:" in workflow
    assert "paths-ignore:" not in workflow


def test_import_linter_workflow_keeps_checks_complete_as_blocking_gate() -> None:
    """The aggregate gate must remain blocking across lint and architecture jobs."""
    workflow = Path(".github/workflows/import-linter.yml").read_text(encoding="utf-8")

    assert "checks-complete:" in workflow
    assert "needs:" in workflow
    assert "- lint" in workflow
    assert "- c901-governance" in workflow
    assert "- arch-tests" in workflow
    assert "if: ${{ always() }}" in workflow


def test_import_linter_workflow_requires_full_capabilities_for_arch_tests() -> None:
    """Required CI must fail fast on capability drift during architecture tests."""
    workflow = Path(".github/workflows/import-linter.yml").read_text(encoding="utf-8")

    assert "arch-tests:" in workflow
    assert 'BIOETL_REQUIRE_TEST_CAPABILITIES: "1"' in workflow
    assert (
        'uv run pytest tests/architecture/ -m "not slow and not benchmark and not memory"'
        in workflow
    )
