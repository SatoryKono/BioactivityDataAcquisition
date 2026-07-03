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


def test_e2e_matrix_nightly_job_enforces_strict_mode_policy() -> None:
    workflow = Path(".github/workflows/e2e-matrix-health.yml").read_text(
        encoding="utf-8"
    )
    assert "matrix-smoke-nightly-live:" in workflow
    assert 'BIOETL_PIPELINE__HEALTH_CHECK_MODE: "strict"' in workflow
    assert 'BIOETL_TEST_MODE: "false"' in workflow
    assert "Enforce strict health-check policy" in workflow
    assert "Strict job forbids probe/test-mode fallback" in workflow
