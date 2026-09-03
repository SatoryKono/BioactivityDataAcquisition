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

from pathlib import Path

import pytest
import yaml


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
    assert "chembl_activity_smoke.xml" in blocking


def test_e2e_matrix_nightly_job_enforces_strict_mode_policy() -> None:
    workflow = Path(".github/workflows/e2e-matrix-health.yml").read_text(
        encoding="utf-8"
    )
    assert "matrix-smoke-nightly-live:" in workflow
    assert 'BIOETL_PIPELINE__HEALTH_CHECK_MODE: "strict"' in workflow
    assert 'BIOETL_TEST_MODE: "false"' in workflow
    assert "Enforce strict health-check policy" in workflow
    assert "Strict job forbids probe/test-mode fallback" in workflow


def test_full_nightly_replay_prompt_and_live_owners_are_fail_closed() -> None:
    workflow = yaml.safe_load(
        Path(".github/workflows/e2e-matrix-health.yml").read_text(encoding="utf-8")
    )
    jobs = workflow["jobs"]
    full = jobs["e2e-nightly-full-replay"]
    live = jobs["matrix-smoke-nightly-live"]
    prompt = jobs["prompt-tests-nightly"]
    complete = jobs["e2e-nightly-complete"]
    full_runs = "\n".join(str(step.get("run") or "") for step in full["steps"])
    live_runs = "\n".join(str(step.get("run") or "") for step in live["steps"])
    prompt_runs = "\n".join(str(step.get("run") or "") for step in prompt["steps"])
    complete_runs = "\n".join(str(step.get("run") or "") for step in complete["steps"])

    assert "tests/e2e" in full_runs
    assert "e2e and not e2e_smoke and not benchmark and not memory" in full_runs
    assert "--record-mode=none" in full_runs
    assert "-p no:xdist" in full_runs
    assert "e2e_smoke and not benchmark and not memory" in live_runs
    assert "tests/prompts/" in prompt_runs
    assert "-p no:xdist" in prompt_runs
    assert set(complete["needs"]) == {
        "matrix-smoke-blocking",
        "matrix-smoke-nightly-live",
        "e2e-nightly-full-replay",
        "prompt-tests-nightly",
    }
    assert "Schedule requires nightly jobs success" in complete_runs
    assert "Manual nightly requires blocking smoke" in complete_runs
    assert "pull_request" not in str(full["if"])
    assert "pull_request" not in str(prompt["if"])


def test_e2e_nightly_dispatch_is_not_cancelled_by_main_push() -> None:
    """Main merge-train push must not cancel schedule/manual nightly (#9976)."""
    workflow = Path(".github/workflows/e2e-matrix-health.yml").read_text(
        encoding="utf-8"
    )
    assert "format('dispatch-{0}', github.run_id)" in workflow
    assert "github.event_name == 'schedule' && 'schedule'" in workflow
    assert (
        "cancel-in-progress: ${{ github.event_name == 'pull_request' || github.event_name == 'push' }}"
        in workflow
    )
