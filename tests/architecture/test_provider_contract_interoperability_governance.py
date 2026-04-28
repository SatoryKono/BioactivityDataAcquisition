"""Architecture guards for provider/interoperability drift gates."""

from __future__ import annotations

from typing import Any, cast

import pytest

from tests.architecture._test_matrix_policy_support import ROOT, load_matrix


@pytest.mark.architecture
def test_interoperability_drift_gate_workflow_matches_matrix_contract() -> None:
    """The replay gate must cover provider, xwalk, and export-manifest surfaces."""
    gate = _interoperability_drift_gates()
    workflow_path = ROOT / cast(str, gate["workflow"])

    assert workflow_path.exists()
    workflow_text = workflow_path.read_text(encoding="utf-8")
    assert gate["fast_path_mode"] == "replay_or_snapshot_only"
    assert gate["live_network_mode"] == "monthly_contract_tests_only"
    assert "BIOETL_LIVE_API_TESTS" not in workflow_text
    assert "BIOETL_NETWORK_TESTS" not in workflow_text
    assert "--network" not in workflow_text

    for command in cast(list[str], gate["required_gate_commands"]):
        _assert_command_represented(workflow_text, command)


@pytest.mark.architecture
def test_interoperability_drift_gate_surfaces_have_existing_evidence() -> None:
    """Every declared drift surface must point at real repo-owned evidence files."""
    gate = _interoperability_drift_gates()

    for surface_name, surface in _required_surfaces(gate).items():
        evidence_paths = cast(list[str], surface["evidence"])
        assert evidence_paths, f"{surface_name} must declare evidence paths"
        for relative_path in evidence_paths:
            evidence_path = ROOT / relative_path
            assert evidence_path.is_file(), (
                f"{surface_name} evidence path does not exist: {relative_path}"
            )


@pytest.mark.architecture
def test_interoperability_drift_expectations_are_backed_by_evidence() -> None:
    """Matrix expectation tokens must be present in the declared evidence surface."""
    gate = _interoperability_drift_gates()

    for surface_name, surface in _required_surfaces(gate).items():
        evidence_text = "\n".join(
            (ROOT / relative_path).read_text(encoding="utf-8")
            for relative_path in cast(list[str], surface["evidence"])
        )
        for expectation in cast(list[str], surface["expectations"]):
            assert expectation in evidence_text, (
                f"{surface_name} expectation {expectation!r} is not backed by "
                "its declared evidence files"
            )


@pytest.mark.architecture
def test_provider_drift_diagnostics_remain_actionable() -> None:
    """Drift failures should retain field-level remediation diagnostics."""
    helper_text = (ROOT / "tests/contract/_provider_contract_drift.py").read_text(
        encoding="utf-8"
    )
    replay_text = (
        ROOT / "tests/contract/test_provider_contract_drift_replay.py"
    ).read_text(encoding="utf-8")

    for token in (
        "\"provider\"",
        "\"entity\"",
        "\"probe\"",
        "\"path\"",
        "\"expected_type\"",
        "\"actual_type\"",
        "\"remediation\"",
    ):
        assert token in helper_text
    assert "remediation=" in replay_text
    assert "entity=" in replay_text


def _interoperability_drift_gates() -> dict[str, Any]:
    matrix = load_matrix()
    fixture_governance = cast(dict[str, Any], matrix["fixture_governance"])
    return cast(dict[str, Any], fixture_governance["interoperability_drift_gates"])


def _required_surfaces(gate: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return cast(dict[str, dict[str, Any]], gate["required_surfaces"])


def _assert_command_represented(workflow_text: str, command: str) -> None:
    missing_tokens = [token for token in command.split() if token not in workflow_text]
    assert not missing_tokens, (
        f"provider-contract-drift workflow does not represent command {command!r}; "
        f"missing tokens: {missing_tokens}"
    )
