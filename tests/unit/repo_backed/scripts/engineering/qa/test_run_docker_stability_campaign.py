from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.engineering.qa import run_docker_stability_campaign as campaign

pytestmark = pytest.mark.repo_backed


def test_signature_valid_requires_expected_fingerprint(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    summary = tmp_path / "summary.json"
    signature = tmp_path / "summary.json.asc"
    summary.write_text("{}\n", encoding="utf-8")
    signature.write_text("signature", encoding="utf-8")

    monkeypatch.setattr(
        campaign,
        "_run",
        lambda *_args: {
            "returncode": 0,
            "stdout": "[GNUPG:] VALIDSIG ABCD1234 2026-07-15 1 10 00 1 00 ABCD1234\n",
        },
    )

    assert campaign._signature_valid(summary, signature, "ABCD1234") is True
    assert campaign._signature_valid(summary, signature, "FFFF9999") is False


def test_release_gates_cannot_pass_partial_or_unsigned_campaign() -> None:
    state = campaign.new_state(
        stack="main", project="bioetl-main", cycles=100, soak_hours=72
    )
    state.update(
        completed_cycles=99,
        soak_observed_seconds=72 * 3600 - 1,
        engine_recovery_trials=100,
        engine_recovery_successes=99,
    )

    gates = campaign.release_gates(state, signature_exists=False)

    assert gates["cycles_complete"] is False
    assert gates["soak_complete"] is False
    assert gates["detached_signature_present"] is False
    assert gates["soak_continuous"] is True


def test_release_gates_require_99_of_100_and_preserved_volumes() -> None:
    state = campaign.new_state(
        stack="main", project="bioetl-main", cycles=100, soak_hours=72
    )
    state.update(
        completed_cycles=100,
        soak_observed_seconds=72 * 3600,
        engine_recovery_trials=100,
        engine_recovery_successes=98,
        volume_loss=True,
    )

    gates = campaign.release_gates(state, signature_exists=True)

    assert gates["engine_recovery_99_of_100"] is False
    assert gates["volumes_preserved"] is False


def test_subprocess_timeout_is_evidence_not_an_uncaught_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def timeout(*_args: object, **_kwargs: object) -> None:
        raise subprocess.TimeoutExpired(["docker", "desktop", "restart"], 180)

    monkeypatch.setattr(campaign.subprocess, "run", timeout)

    result = campaign._run(["docker", "desktop", "restart"], 180)

    assert result["returncode"] == 127
    assert "timed out" in result["stderr"]


def test_release_gates_reject_interrupted_soak() -> None:
    state = campaign.new_state(
        stack="main", project="bioetl-main", cycles=100, soak_hours=72
    )
    state.update(
        completed_cycles=100,
        soak_observed_seconds=72 * 3600,
        soak_interruptions=1,
        engine_recovery_trials=100,
        engine_recovery_successes=100,
        probe_samples=1,
    )

    gates = campaign.release_gates(state, signature_exists=True)

    assert gates["soak_continuous"] is False
