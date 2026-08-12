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
"""Architecture tests for strict/probe health-mode CI policy."""

from __future__ import annotations

import pytest

from pathlib import Path


pytestmark = pytest.mark.architecture


def test_e2e_matrix_blocking_job_runs_in_probe_mode() -> None:
    workflow = Path(".github/workflows/e2e-matrix-health.yml").read_text(
        encoding="utf-8"
    )
    assert "matrix-smoke-blocking:" in workflow
    assert 'BIOETL_PIPELINE__HEALTH_CHECK_MODE: "probe"' in workflow


def test_e2e_matrix_blocking_job_covers_e2e_smoke_ssot_paths() -> None:
    """matrix-smoke-blocking must execute every e2e-smoke SSOT path (#8612/#8613)."""
    workflow = Path(".github/workflows/e2e-matrix-health.yml").read_text(
        encoding="utf-8"
    )
    # Bound assertions to the blocking job block (before nightly live job).
    start = workflow.index("matrix-smoke-blocking:")
    end = workflow.index("matrix-smoke-nightly-live:")
    blocking = workflow[start:end]
    assert "tests/e2e/test_pipeline_matrix_e2e.py" in blocking
    assert "test_pipeline_matrix_smoke" in blocking
    assert "tests/e2e/test_chembl_activity_e2e.py" in blocking
    assert "e2e_smoke" in blocking
    assert "chembl_activity-smoke.xml" in blocking


def test_e2e_matrix_nightly_job_enforces_strict_mode_policy() -> None:
    workflow = Path(".github/workflows/e2e-matrix-health.yml").read_text(
        encoding="utf-8"
    )
    assert "matrix-smoke-nightly-live:" in workflow
    assert 'BIOETL_PIPELINE__HEALTH_CHECK_MODE: "strict"' in workflow
    assert 'BIOETL_TEST_MODE: "false"' in workflow
    assert "Enforce strict health-check policy" in workflow
    assert "Strict job forbids probe/test-mode fallback" in workflow
