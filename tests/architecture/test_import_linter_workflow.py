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
"""Architecture tests for the non-skippable import-linter CI gate.REQ-GOV-008: Import Linter is a change-set gate."""

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


def test_import_linter_workflow_requires_capabilities_for_sharded_arch_tests() -> None:
    """Required CI must fail fast on capability drift during architecture tests."""
    workflow = Path(".github/workflows/import-linter.yml").read_text(encoding="utf-8")

    assert "arch-tests:" in workflow
    assert 'BIOETL_REQUIRE_TEST_CAPABILITIES: "1"' in workflow
    assert "strategy:" in workflow
    assert "matrix:" in workflow
    assert "bash scripts/engineering/dev/run_pytest_sharded.sh" in workflow
    assert '--shard "${{ matrix.shard }}"' in workflow
    assert "--skip-preflight" in workflow
    assert '-m "not slow and not benchmark and not memory"' in workflow


def test_import_linter_changed_file_gate_stays_below_arg_max() -> None:
    """Large changed-file sets must stay on disk and be processed in batches."""
    workflow = Path(".github/workflows/import-linter.yml").read_text(encoding="utf-8")

    assert 'list_file="${RUNNER_TEMP}/ruff-changed-python.txt"' in workflow
    assert 'echo "list_file=${list_file}" >> "$GITHUB_OUTPUT"' in workflow
    assert 'echo "file_count=${file_count}" >> "$GITHUB_OUTPUT"' in workflow
    assert 'if [[ "$file_count" -gt 400 ]]' in workflow
    assert "xargs -a \"$list_file\" -d '\\n' -n 100" in workflow
    assert 'echo "files=' not in workflow
