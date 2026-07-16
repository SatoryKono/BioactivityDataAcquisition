from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

import pytest

from scripts.engineering.qa.docker_stability_campaign import commands, faults, model
from scripts.engineering.qa.docker_stability_campaign import runner as campaign
from scripts.engineering.qa.docker_stability_campaign import promotion

pytestmark = pytest.mark.repo_backed


def _passing_state() -> dict[str, object]:
    state = model.new_state(
        stack="main", project="bioetl-main", cycles=100, soak_hours=72
    )
    state.update(
        completed_cycles=100,
        soak_observed_seconds=72 * 3600,
        engine_recovery_trials=100,
        engine_recovery_successes=99,
        probe_samples=1,
        docker_vm_min_free_bytes=4 * 1024**3,
        fault_cases={name: {"passed": True} for name in model.FAULT_CASE_NAMES},
    )
    return state


def test_release_gates_cannot_pass_partial_or_unsigned_campaign() -> None:
    state = _passing_state()
    state.update(completed_cycles=99, soak_observed_seconds=72 * 3600 - 1)

    gates = model.release_gates(state, signature_exists=False)

    assert gates["cycles_complete"] is False
    assert gates["soak_complete"] is False
    assert gates["detached_signature_present"] is False


def test_release_gates_require_complete_fault_matrix_and_vm_reserve() -> None:
    state = _passing_state()
    state["fault_cases"] = {}
    state["docker_vm_min_free_bytes"] = 4 * 1024**3 - 1

    gates = model.release_gates(state, signature_exists=True)

    assert gates["fault_matrix_complete"] is False
    assert gates["fault_matrix_clean"] is False
    assert gates["docker_vm_reserve_at_least_4_gib"] is False


def test_release_gates_allow_one_resolved_recovery_failure() -> None:
    gates = model.release_gates(_passing_state(), signature_exists=True)

    assert gates["engine_recovery_99_of_100"] is True
    assert all(gates.values())


def test_subprocess_timeout_is_bounded_evidence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def timeout(*_args: object, **_kwargs: object) -> None:
        raise subprocess.TimeoutExpired(["docker", "desktop", "restart"], 1)

    monkeypatch.setattr(commands.subprocess, "run", timeout)

    result = commands.run_command(["docker", "desktop", "restart"], 1, cwd=tmp_path)

    assert result["returncode"] == 124
    assert result["timed_out"] is True
    assert "timed out" in result["stderr"]


def test_command_evidence_redacts_split_secret_value(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        commands.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            ["tool"], 1, stdout="", stderr="--token ghp_secretvalue12345"
        ),
    )

    result = commands.run_command(
        ["tool", "--password", "do-not-store"], 1, cwd=tmp_path
    )

    assert result["command"][-1] == "<redacted>"
    assert "ghp_" not in result["stderr"]


@pytest.mark.parametrize(
    ("result", "expected", "passed"),
    [
        ({"returncode": 0}, "success", True),
        (
            {"returncode": 2, "primary_cause": "service_unready"},
            "cause:service_unready",
            True,
        ),
        ({"returncode": 2, "primary_cause": "unknown"}, "cause:service_unready", False),
        (
            {"returncode": 2, "preflight_findings": ["HOST_PORT_COLLISION"]},
            "finding:HOST_PORT_COLLISION",
            True,
        ),
        ({"returncode": 2}, "finding:HOST_PORT_COLLISION", False),
        ({"returncode": -15, "interrupted": True}, "interrupted", True),
        ({"returncode": 1}, "interrupted", False),
    ],
)
def test_fault_outcomes_are_exact(
    result: dict[str, object], expected: str, passed: bool
) -> None:
    assert faults.operation_passed(result, expected) is passed


def test_fault_matrix_covers_every_required_case_once() -> None:
    cases = faults.build_fault_cases()

    assert tuple(case.name for case in cases) == model.FAULT_CASE_NAMES
    assert all(case.max_seconds <= 180 for case in cases)
    assert all(operation.expected for case in cases for operation in case.observe)


class _FakeFaultExecutor:
    def __init__(self, tmp_path: Path, *, fail_apply: bool = False) -> None:
        self.runtime_origin = tmp_path
        self.specs = {
            "main": model.StackSpec("main", "bioetl-main", "", ("bioetl",)),
            "monitoring": model.StackSpec(
                "monitoring", "bioetl-monitoring", "", ("prometheus",)
            ),
        }
        self.fail_apply = fail_apply
        self.closed = False

    def execute(
        self,
        operation: model.FaultOperation,
        **_kwargs: object,
    ) -> dict[str, object]:
        if self.fail_apply and operation.kind == "kill_service":
            return {"returncode": 1}
        if operation.expected.startswith("cause:"):
            return {
                "returncode": 2,
                "primary_cause": operation.expected.partition(":")[2],
            }
        if operation.expected.startswith("finding:"):
            return {
                "returncode": 2,
                "preflight_findings": [operation.expected.partition(":")[2]],
            }
        if operation.expected == "interrupted":
            return {"returncode": -15, "interrupted": True}
        return {"returncode": 0}

    def close(self) -> None:
        self.closed = True


@pytest.mark.parametrize("case_name", model.FAULT_CASE_NAMES)
def test_each_fault_case_is_restored_and_individually_evidenced(
    case_name: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(faults, "volume_ids", lambda *_args, **_kwargs: {"data"})
    case = next(item for item in faults.build_fault_cases() if item.name == case_name)
    executor = _FakeFaultExecutor(tmp_path)
    state = model.new_state(
        bundle=tuple(executor.specs.values()), cycles=100, soak_hours=72
    )
    evidence = tmp_path / "raw"

    assert faults.execute_fault_case(
        case, executor, state, tmp_path / "state.json", evidence
    )

    report = model.load_json(evidence / "faults" / case_name / "case.json")
    assert report["passed"] is True
    assert report["volume_ids_before"] == report["volume_ids_after"]
    assert executor.closed is True
    assert state["fault_cases"][case_name]["passed"] is True


def test_failed_fault_emits_one_incident_and_evidence_cannot_be_replaced(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(faults, "volume_ids", lambda *_args, **_kwargs: {"data"})
    case = faults.build_fault_cases()[0]
    executor = _FakeFaultExecutor(tmp_path, fail_apply=True)
    state = model.new_state(
        bundle=tuple(executor.specs.values()), cycles=100, soak_hours=72
    )
    evidence = tmp_path / "raw"

    assert not faults.execute_fault_case(
        case, executor, state, tmp_path / "state.json", evidence
    )
    assert state["incident_ids"] == [f"fault-{case.name}"]

    with pytest.raises(FileExistsError):
        faults.execute_fault_case(
            case,
            _FakeFaultExecutor(tmp_path, fail_apply=True),
            state,
            tmp_path / "state.json",
            evidence,
        )


def test_fault_case_reserves_deadline_for_restore(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    now = [0.0]
    monkeypatch.setattr(faults.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(faults, "volume_ids", lambda *_args, **_kwargs: {"data"})
    case = faults.build_fault_cases()[0]

    class DeadlineExecutor(_FakeFaultExecutor):
        def __init__(self, root: Path) -> None:
            super().__init__(root)
            self.calls: list[tuple[str, float]] = []

        def execute(
            self,
            operation: model.FaultOperation,
            **kwargs: object,
        ) -> dict[str, object]:
            deadline = float(kwargs["deadline"])
            self.calls.append((operation.kind, deadline))
            if operation.kind == "probe":
                now[0] = deadline
            return super().execute(operation, **kwargs)

    executor = DeadlineExecutor(tmp_path)
    state = model.new_state(
        bundle=tuple(executor.specs.values()), cycles=100, soak_hours=72
    )

    assert faults.execute_fault_case(
        case, executor, state, tmp_path / "state.json", tmp_path / "raw"
    )

    deadlines = dict(executor.calls)
    assert deadlines["recover"] > deadlines["probe"]
    report = model.load_json(
        tmp_path / "raw" / "faults" / case.name / "case.json"
    )
    assert report["steps"][-1]["phase"] == "restore"
    assert report["steps"][-1]["operation"] == "recover"


def test_pressure_fault_is_synchronous_and_verifies_no_residual_workload(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[str, ...]] = []

    def compose(
        runtime_origin: Path,
        spec: model.StackSpec,
        args: tuple[str, ...],
        timeout: float,
    ) -> dict[str, object]:
        del runtime_origin, spec, timeout
        calls.append(args)
        return {"returncode": 0}

    monkeypatch.setattr(faults, "compose_command", compose)
    bundle = (
        model.StackSpec("main", "bioetl-main", "docker-compose.yml", ("bioetl",)),
    )
    executor = faults.HostFaultExecutor(
        runtime_origin=tmp_path,
        contract=tmp_path / "contract.yml",
        evidence_dir=tmp_path / "raw",
        bundle=bundle,
        baselines={},
    )
    case = next(
        item
        for item in faults.build_fault_cases()
        if item.name == "bounded_memory_pid_pressure"
    )

    executor.execute(
        case.apply[0],
        deadline=time.monotonic() + 30,
        case_name=case.name,
        ordinal=1,
    )
    executor.execute(
        case.restore[0],
        deadline=time.monotonic() + 30,
        case_name=case.name,
        ordinal=2,
    )

    assert "--detach" not in calls[0]
    assert "bioetl-fault-pressure.pids" in calls[0][-1]
    assert "os.kill(pid, 0)" in calls[1][-1]
    assert [operation.kind for operation in case.restore] == [
        "clear_pressure",
        "probe",
    ]


def test_recursive_redaction_covers_nested_credentials_and_uri_userinfo() -> None:
    protected = model.redact(
        {
            "credential": "value",
            "nested": [
                "Authorization: bearer-value",
                "https://user:pass@example.test",
                "ghp_abcdefghijklmnopqrstuvwxyz123456",
            ],
        }
    )

    assert protected["credential"] == "<redacted>"
    assert "bearer-value" not in json.dumps(protected)
    assert "user:pass" not in json.dumps(protected)
    assert "ghp_" not in json.dumps(protected)


def test_resume_evidence_rejects_changed_or_unindexed_files(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    report = evidence / "cycle.json"
    state: dict[str, object] = {"evidence_sha256": {}}
    model.atomic_json(report, {"ok": True})
    model.remember_evidence(state, report, evidence)
    model.validate_evidence_index(state, evidence)

    model.atomic_json(report, {"ok": False})
    with pytest.raises(ValueError, match="changed"):
        model.validate_evidence_index(state, evidence)

    model.atomic_json(report, {"ok": True})
    model.atomic_json(evidence / "unindexed.json", {"ok": True})
    with pytest.raises(ValueError, match="set differs"):
        model.validate_evidence_index(state, evidence)


def test_new_evidence_refuses_replacement(tmp_path: Path) -> None:
    evidence = tmp_path / "immutable.json"
    model.atomic_json(evidence, {"generation": 1}, replace=False)

    with pytest.raises(FileExistsError):
        model.atomic_json(evidence, {"generation": 2}, replace=False)


@pytest.mark.parametrize(
    ("path", "kind"),
    [
        ("/home/fedor/runtime", "linux"),
        ("/mnt/e/repository", "mnt"),
        ("/tmp/runtime", "tmp"),
        (r"C:\\repo", "windows"),
        ("relative/path", "relative"),
    ],
)
def test_runtime_origin_classification(path: str, kind: str) -> None:
    assert model.origin_kind(path) == kind


def test_compose_origins_require_both_projects_inside_linux_mirror() -> None:
    runtime = Path("/home/fedor/.local/share/bioetl-runtime/test-origin")
    bundle = (
        model.StackSpec("main", "bioetl-main", "docker-compose.yml", ("bioetl",)),
        model.StackSpec(
            "monitoring",
            "bioetl-monitoring",
            "docker-compose.monitoring.yml",
            ("prometheus",),
        ),
    )
    rows = [{"Name": "bioetl-main", "ConfigFiles": str(runtime / "docker-compose.yml")}]

    findings = model.compose_origin_findings(rows, bundle, runtime)

    assert findings == ["bioetl-monitoring: project not running"]


def test_release_bundle_pins_both_projects_and_protected_volume_names() -> None:
    contract = {
        "stacks": {
            "main": {
                "project_name": "bioetl-main",
                "compose_file": "docker-compose.yml",
                "required_services": ["bioetl"],
                "migration": {"volume_map": {}},
            },
            "monitoring": {
                "project_name": "bioetl-monitoring",
                "compose_file": "docker-compose.monitoring.yml",
                "required_services": ["prometheus"],
                "migration": {
                    "volume_map": {"legacy-prometheus": "bioetl-monitoring-prometheus"}
                },
            },
        }
    }

    bundle = model.release_bundle(contract)

    assert [(item.stack, item.project) for item in bundle] == [
        ("main", "bioetl-main"),
        ("monitoring", "bioetl-monitoring"),
    ]
    assert bundle[1].protected_volumes == (
        "bioetl-monitoring-prometheus",
        "legacy-prometheus",
    )
    assert bundle[1].required_volumes == ("bioetl-monitoring-prometheus",)
    assert bundle[1].legacy_volumes == ("legacy-prometheus",)


def test_required_volume_precondition_fails_before_lifecycle_mutation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    bundle = (
        model.StackSpec(
            "monitoring",
            "bioetl-monitoring",
            "docker-compose.monitoring.yml",
            ("prometheus",),
            protected_volumes=("legacy-prometheus", "target-prometheus"),
            required_volumes=("target-prometheus",),
            legacy_volumes=("legacy-prometheus",),
        ),
    )
    monkeypatch.setattr(
        commands,
        "run_command",
        lambda *_args, **_kwargs: {
            "returncode": 0,
            "stdout": "legacy-prometheus\n",
        },
    )

    result = commands.required_volume_precondition(tmp_path, bundle)

    assert result["passed"] is False
    assert result["missing_required_target_volumes"] == ["target-prometheus"]
    assert result["stacks"]["monitoring"]["legacy_volumes"] == {
        "legacy-prometheus": "present"
    }
    assert result["stacks"]["monitoring"]["required_target_volumes"] == {
        "target-prometheus": "missing"
    }


def test_validate_args_refuses_reduced_thresholds() -> None:
    args = argparse.Namespace(
        execute=True,
        cycles=99,
        soak_hours=72,
        engine_recovery_trials=100,
        soak_sample_seconds=60,
        confirm_host_disruption=campaign.CONFIRM_TOKEN,
        signing_key="key",
        signing_fingerprint="A" * 40,
    )

    with pytest.raises(ValueError, match="cannot be reduced"):
        campaign.validate_args(args)


def test_validate_args_requires_exact_disruption_token_and_full_fingerprint() -> None:
    args = argparse.Namespace(
        execute=True,
        cycles=100,
        soak_hours=72,
        engine_recovery_trials=100,
        soak_sample_seconds=60,
        confirm_host_disruption="yes",
        signing_key="key",
        signing_fingerprint="ABCD",
    )
    with pytest.raises(ValueError, match="exact scheduling token"):
        campaign.validate_args(args)

    args.confirm_host_disruption = campaign.CONFIRM_TOKEN
    with pytest.raises(ValueError, match="full hexadecimal"):
        campaign.validate_args(args)


def test_secret_signing_identity_requires_exact_full_fingerprint(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        promotion,
        "run_command",
        lambda *_args, **_kwargs: {
            "returncode": 0,
            "stdout": f"fpr:::::::::{'A' * 40}:\n",
        },
    )

    assert promotion.secret_fingerprint(tmp_path, "release", "A" * 40)
    assert not promotion.secret_fingerprint(tmp_path, "release", "B" * 40)


def test_desktop_recovery_bundle_is_bounded_and_never_requests_last_resort(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    report = tmp_path / "raw" / "docker-desktop-recovery.json"
    observed: list[list[str]] = []

    def run(command: list[str], timeout: float, *, cwd: Path) -> dict[str, object]:
        del timeout, cwd
        observed.append(command)
        if command[0] == "wslpath":
            return {
                "returncode": 0,
                "stdout": "C:\\runtime\\" + Path(command[-1]).name,
            }
        model.atomic_json(
            report,
            {
                "schema_version": "bioetl-docker-desktop-recovery-v2",
                "ok": True,
            },
        )
        return {"returncode": 0, "stdout": "", "stderr": ""}

    monkeypatch.setattr(commands, "run_command", run)

    result = commands.desktop_recovery_diagnostic_bundle(tmp_path, report)

    assert result["returncode"] == 0
    assert result["diagnostic_bundle_present"] is True
    invocation = observed[-1]
    assert invocation[0] == "powershell.exe"
    assert "-ConfirmLastResort" not in invocation
    assert invocation[invocation.index("-TimeoutSeconds") + 1] == "175"


def test_failed_recovery_trial_captures_v2_desktop_diagnostics(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    bundle = (
        model.StackSpec("main", "bioetl-main", "docker-compose.yml", ("bioetl",)),
    )
    state = model.new_state(bundle=bundle, cycles=100, soak_hours=72)
    state["required_engine_recovery_trials"] = 1
    evidence = tmp_path / "raw"
    diagnostic_paths: list[Path] = []

    monkeypatch.setattr(
        promotion,
        "bundle_volume_ids",
        lambda *_args, **_kwargs: {"bioetl-main": []},
    )
    monkeypatch.setattr(
        promotion,
        "manager_step",
        lambda *_args, **_kwargs: {"returncode": 0},
    )
    monkeypatch.setattr(
        promotion,
        "observe_docker_vm_reserve",
        lambda *_args, **_kwargs: {"returncode": 0},
    )
    monkeypatch.setattr(
        promotion,
        "run_command",
        lambda *_args, **_kwargs: {"returncode": 1, "timed_out": False},
    )

    def probe(
        runtime_origin: Path,
        spec: model.StackSpec,
        output: Path,
        timeout: float,
        **_kwargs: object,
    ) -> dict[str, object]:
        del runtime_origin, timeout
        model.atomic_json(
            output,
            {
                "summary": {"ok": True},
                "services": [
                    {
                        "service": spec.required_services[0],
                        "container_id": "container-id",
                        "restart_count": 0,
                    }
                ],
                "resources": [],
            },
        )
        return {"returncode": 0}

    def diagnostics(
        runtime_origin: Path, report: Path, timeout: float
    ) -> dict[str, object]:
        del runtime_origin, timeout
        diagnostic_paths.append(report)
        model.atomic_json(
            report,
            {
                "schema_version": "bioetl-docker-desktop-recovery-v2",
                "ok": True,
            },
        )
        return {"returncode": 0, "diagnostic_bundle_present": True}

    monkeypatch.setattr(promotion, "probe_command", probe)
    monkeypatch.setattr(
        promotion, "desktop_recovery_diagnostic_bundle", diagnostics
    )

    assert promotion.run_recovery_trials(
        state,
        tmp_path / "state.json",
        evidence,
        tmp_path,
        tmp_path / "contract.yml",
        bundle,
    )

    assert diagnostic_paths == [
        evidence / "recovery" / "trial-001" / "docker-desktop-recovery.json"
    ]
    trial = model.load_json(evidence / "recovery" / "trial-001" / "trial.json")
    assert trial["success"] is False
    assert trial["post_trial_restore"][0]["action"] == (
        "desktop-recovery-diagnostics"
    )
    assert trial["incident_resolved"] is True


def test_signed_summary_is_not_modified_after_signature(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    state = _passing_state()
    state.update(
        campaign_identity={"run": "test"},
        initial_volume_ids={"bioetl-main": []},
        final_volume_ids={},
        evidence_sha256={},
    )
    state_path = tmp_path / "state.json"
    evidence = tmp_path / "raw"
    evidence.mkdir()
    summary = tmp_path / "summary.json"
    bundle = (model.StackSpec("main", "bioetl-main", "", ("bioetl",)),)
    monkeypatch.setattr(
        promotion,
        "bundle_volume_ids",
        lambda *_args, **_kwargs: {"bioetl-main": []},
    )

    def sign(_origin: Path, summary_path: Path, *_args: str):
        signature = summary_path.with_suffix(summary_path.suffix + ".asc")
        signature.write_text("signed", encoding="utf-8")
        return signature, True, {"verify": {"returncode": 0}}

    monkeypatch.setattr(promotion, "sign_and_verify", sign)

    assert (
        promotion.finalize_campaign(
            state,
            state_path,
            evidence,
            tmp_path,
            summary,
            "key",
            "A" * 40,
            bundle,
        )
        is True
    )
    signed_bytes = summary.read_bytes()
    receipt = json.loads(
        summary.with_suffix(".json.verification.json").read_text(encoding="utf-8")
    )

    assert summary.read_bytes() == signed_bytes
    assert receipt["promotion_passed"] is True
