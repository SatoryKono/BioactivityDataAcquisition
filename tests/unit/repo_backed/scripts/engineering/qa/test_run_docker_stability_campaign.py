from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from scripts.engineering.qa import run_docker_stability_campaign as campaign

pytestmark = pytest.mark.repo_backed


@pytest.fixture
def release_contract() -> dict[str, Any]:
    return {
        "stacks": {
            "main": {
                "project_name": "bioetl-main",
                "compose_file": "docker-compose.yml",
                "required_services": ["bioetl"],
            },
            "monitoring": {
                "project_name": "bioetl-monitoring",
                "compose_file": "docker-compose.monitoring.yml",
                "required_services": ["prometheus", "grafana"],
            },
        },
        "host_ports": {8081: {"stack": "main", "service": "bioetl"}},
    }


def test_release_bundle_is_explicit_and_contains_both_projects(
    release_contract: dict[str, Any],
) -> None:
    bundle = campaign._release_bundle(release_contract)

    assert [(spec.stack, spec.project) for spec in bundle] == [
        ("main", "bioetl-main"),
        ("monitoring", "bioetl-monitoring"),
    ]


@pytest.mark.parametrize(
    ("origin", "kind"),
    [
        (r"C:\\repo\\compose.yml", "windows"),
        ("/mnt/e/repo/docker-compose.yml", "mnt"),
        ("/tmp/runtime/docker-compose.yml", "tmp"),
        ("/home/operator/runtime/docker-compose.yml", "linux"),
    ],
)
def test_runtime_origin_classification_refuses_noncanonical_locations(
    origin: str, kind: str
) -> None:
    assert campaign._origin_kind(origin) == kind


def test_runtime_mirror_does_not_require_git_metadata(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(campaign, "_origin_kind", lambda _path: "linux")

    assert campaign._canonical_runtime_origin(tmp_path) == tmp_path.resolve()


def test_live_compose_origin_pin_rejects_windows_mnt_tmp_and_outside_mirror(
    release_contract: dict[str, Any],
) -> None:
    bundle = campaign._release_bundle(release_contract)
    rows = [
        {"Name": "bioetl-main", "ConfigFiles": r"E:\\repo\\docker-compose.yml"},
        {
            "Name": "bioetl-monitoring",
            "ConfigFiles": "/home/runtime/docker-compose.monitoring.yml,/tmp/override.yml",
        },
    ]

    findings = campaign._compose_origin_findings(rows, bundle, Path("/home/runtime"))

    assert findings == [
        "bioetl-main: noncanonical origin",
        "bioetl-monitoring: noncanonical origin",
    ]


def test_bundle_volume_identity_captures_every_selected_project(
    monkeypatch: pytest.MonkeyPatch, release_contract: dict[str, Any]
) -> None:
    bundle = campaign._release_bundle(release_contract)
    seen: list[str] = []

    def volume_ids(project: str, _origin: Path) -> set[str]:
        seen.append(project)
        return {f"{project}_data"}

    monkeypatch.setattr(campaign, "_volume_ids", volume_ids)

    assert campaign._bundle_volume_ids(bundle, Path("/home/runtime")) == {
        "bioetl-main": ["bioetl-main_data"],
        "bioetl-monitoring": ["bioetl-monitoring_data"],
    }
    assert seen == ["bioetl-main", "bioetl-monitoring"]


def test_fault_matrix_has_every_required_case_and_case_local_restore(
    release_contract: dict[str, Any],
) -> None:
    cases = campaign.build_fault_cases(
        campaign._release_bundle(release_contract), release_contract
    )

    assert tuple(case.name for case in cases) == campaign.FAULT_CASE_NAMES
    assert all(case.restore for case in cases)
    assert all(case.max_seconds <= 180 for case in cases)
    assert (
        next(case for case in cases if case.name == "occupied_required_port")
        .apply[-1]
        .port
        == 8081
    )


@pytest.mark.parametrize("case_name", campaign.FAULT_CASE_NAMES)
def test_each_fault_primitive_is_reversible_and_individually_evidenced(
    case_name: str,
    tmp_path: Path,
    release_contract: dict[str, Any],
) -> None:
    cases = campaign.build_fault_cases(
        campaign._release_bundle(release_contract), release_contract
    )
    case = next(candidate for candidate in cases if candidate.name == case_name)
    state = campaign.new_state(
        bundle=campaign._release_bundle(release_contract),
        runtime_origin=Path("/home/runtime"),
        contract_sha256="a" * 64,
        cycles=100,
        soak_hours=72,
    )

    def executor(
        operation: campaign.FaultOperation, _remaining: float
    ) -> dict[str, Any]:
        if operation.expected == "failure":
            return {"returncode": 1}
        if operation.expected.startswith("classification:"):
            return {
                "returncode": 0,
                "classification": operation.expected.partition(":")[2],
            }
        return {"returncode": 0}

    assert campaign.execute_fault_case(
        case,
        executor=executor,
        volume_snapshot=lambda: {"bioetl-main": ["data"]},
        state=state,
        state_path=tmp_path / "state.json",
        evidence_dir=tmp_path / "raw",
    )
    evidence = campaign._load(tmp_path / "raw" / f"fault-{case_name}.json")
    assert evidence["passed"] is True
    assert evidence["restored"] is True
    assert not list((tmp_path / "raw").glob("incident-*.json"))


def test_failed_fault_emits_exactly_one_incident_and_cannot_be_replaced(
    tmp_path: Path, release_contract: dict[str, Any]
) -> None:
    case = campaign.build_fault_cases(
        campaign._release_bundle(release_contract), release_contract
    )[0]
    state = campaign.new_state(
        bundle=campaign._release_bundle(release_contract),
        cycles=100,
        soak_hours=72,
    )

    def fail_apply(
        operation: campaign.FaultOperation, _remaining: float
    ) -> dict[str, Any]:
        return {"returncode": 0 if operation in case.restore else 1}

    assert not campaign.execute_fault_case(
        case,
        executor=fail_apply,
        volume_snapshot=lambda: {},
        state=state,
        state_path=tmp_path / "state.json",
        evidence_dir=tmp_path / "raw",
    )
    assert len(list((tmp_path / "raw").glob("incident-*.json"))) == 1
    with pytest.raises(FileExistsError):
        campaign.execute_fault_case(
            case,
            executor=fail_apply,
            volume_snapshot=lambda: {},
            state=state,
            state_path=tmp_path / "state.json",
            evidence_dir=tmp_path / "raw",
        )


def test_recursive_redaction_covers_credentials_authorization_and_github_tokens() -> (
    None
):
    payload = {
        "credential": "value",
        "nested": [
            "Authorization: Bearer-value",
            "ghp_abcdefghijklmnopqrstuvwxyz123456",
        ],
    }

    assert campaign._redact(payload) == {
        "credential": "<redacted>",
        "nested": ["Authorization: <redacted>", "<redacted-github-token>"],
    }


def test_image_drift_uses_observed_compose_identity_without_mutating_images(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    release_contract: dict[str, Any],
) -> None:
    commands: list[list[str]] = []

    def run(command: list[str], _timeout: float, **_kwargs: object) -> dict[str, Any]:
        commands.append(command)
        return {"returncode": 0, "stdout": '[{"ID":"sha256:actual"}]'}

    monkeypatch.setattr(campaign, "_run", run)
    executor = campaign._HostFaultExecutor(
        tmp_path, campaign._release_bundle(release_contract), tmp_path
    )

    injected = executor(
        campaign.FaultOperation("inject_expected_image_drift", "main"), 10
    )
    classified = executor(campaign.FaultOperation("classify_image_drift", "main"), 10)

    assert injected["actual_identity_sha256"] != injected["expected_identity_sha256"]
    assert classified["classification"] == "image_identity_drift"
    assert commands[0][-3:] == ["images", "--format", "json"]
    assert all("tag" not in command and "pull" not in command for command in commands)


def test_signing_identity_must_match_exact_secret_key_fingerprint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        campaign,
        "_run",
        lambda *_args, **_kwargs: {
            "returncode": 0,
            "stdout": "fpr:::::::::ABCDEF1234567890:\n",
        },
    )

    assert campaign._signing_identity_matches("release", "ABCDEF1234567890")
    assert not campaign._signing_identity_matches("release", "0000000000000000")


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
