"""Report assembly and CLI orchestration for observability closure campaigns."""

# ruff: noqa: F403, F405

from __future__ import annotations

from scripts.engineering.qa.run_observability_closure_campaign import *
from scripts.engineering.qa.run_observability_closure_campaign import (
    _bootstrap_campaign_context,
    _build_parser,
    _campaign_binding,
    _discover_chembl_pipelines,
    _dq_hard_failure_test_command,
    _evidence_gate,
    _finalize_campaign,
    _has_non_empty_decision_trace,
    _planned_attempts,
    _repo_root,
    _residual_findings_gate,
    _run_attempt,
    _run_phase_command,
    _scorecard,
    _sha256_file,
    _stage_standalone_fixture_cache,
    _stage_workflow_fixture,
    _tree_signature,
    _utc_now,
    _workflow_baseline_command,
    _workflow_failure_command,
)


def _planned_payload(
    *,
    parity_ok: bool,
    pipelines: tuple[str, ...],
    registered_pipelines: tuple[str, ...],
    planned: list[dict[str, str | bool]],
    source_revision: str,
    source_provenance: dict[str, object],
    registry_completed: subprocess.CompletedProcess[str],
    external_gate: dict[str, object],
    scorecard: dict[str, dict[str, float]],
    residual_limitations: list[str],
    finding_ids: list[str],
) -> dict[str, object]:
    """Dry-run campaign plan payload."""
    return {
        "status": "planned",
        "pipeline_config_parity": parity_ok,
        "pipelines": list(pipelines),
        "registered_pipelines": list(registered_pipelines),
        "attempts": planned,
        "source_revision": source_revision,
        "source_provenance": source_provenance,
        "registry_command": list(registry_completed.args),
        "registry_stdout": registry_completed.stdout,
        "external_evidence_gate": external_gate,
        "scorecard": scorecard,
        "residual_limitations": residual_limitations,
        "finding_ids": finding_ids,
    }


def _run_standalone_attempts(
    *,
    repo_root: Path,
    audit_root: Path,
    python: Path,
    planned: list[dict[str, str | bool]],
    limit: int,
    timeout_seconds: int,
    cached_bronze_root: Path,
) -> list[AttemptEvidence]:
    """Execute planned offline standalone pipeline attempts."""
    attempts: list[AttemptEvidence] = []
    for item in planned:
        attempts.append(
            _run_attempt(
                repo_root=repo_root,
                audit_root=audit_root,
                python=python,
                pipeline=str(item["pipeline"]),
                limit=limit,
                tracing=bool(item["tracing"]),
                timeout_seconds=timeout_seconds,
                cached_bronze_root=cached_bronze_root,
            )
        )
    return attempts


def _run_campaign_phases(
    *,
    repo_root: Path,
    audit_root: Path,
    python: Path,
    limit: int,
    timeout_seconds: int,
    workflow_fixture_root: Path,
) -> tuple[PhaseEvidence, PhaseEvidence, PhaseEvidence]:
    """Run baseline, expected-failure, and DQ hard-failure phases."""
    workflow_phase_root = audit_root / "phases" / "chembl-baseline"
    workflow_phase = _run_phase_command(
        name="chembl_baseline",
        command=_workflow_baseline_command(
            python=python,
            limit=limit,
            cached_bronze_root=workflow_fixture_root,
        ),
        repo_root=repo_root,
        phase_root=workflow_phase_root,
        data_root=workflow_phase_root / "data",
        timeout_seconds=timeout_seconds,
    )
    failure_phase_root = audit_root / "phases" / "chembl-baseline-failure"
    empty_bronze_root = failure_phase_root / "empty-bronze"
    empty_bronze_root.mkdir(parents=True, exist_ok=True)
    failure_phase = _run_phase_command(
        name="chembl_baseline_expected_failure",
        command=_workflow_failure_command(
            python=python,
            limit=limit,
            empty_bronze_root=empty_bronze_root,
        ),
        repo_root=repo_root,
        phase_root=failure_phase_root,
        data_root=failure_phase_root / "data",
        timeout_seconds=timeout_seconds,
        expected_outcome="failure",
    )
    dq_phase_root = audit_root / "phases" / "dq-hard-failure"
    dq_phase = _run_phase_command(
        name="dq_hard_failure_boundary",
        command=_dq_hard_failure_test_command(python=python),
        repo_root=repo_root,
        phase_root=dq_phase_root,
        data_root=dq_phase_root / "data",
        timeout_seconds=timeout_seconds,
        isolated_workdir=False,
    )
    return workflow_phase, failure_phase, dq_phase


def _tracing_result_parity(attempts: list[AttemptEvidence]) -> bool:
    """Whether every pipeline has OFF/ON pairs with matching result signatures."""
    return all(
        len(pair) == 2
        and all(attempt.satisfies_closure for attempt in pair)
        and all(_has_non_empty_decision_trace(attempt) for attempt in pair)
        and pair[0].result_signature == pair[1].result_signature
        for pipeline in CHEMBL_PIPELINES
        for pair in (
            tuple(attempt for attempt in attempts if attempt.pipeline == pipeline),
        )
    )


def _attempt_gate_satisfied(
    *,
    tracing_mode: str,
    attempts: list[AttemptEvidence],
    tracing_result_parity: bool,
) -> bool:
    """Whether standalone attempt gate requirements are met."""
    expected_attempt_keys = {
        (pipeline, tracing)
        for pipeline in CHEMBL_PIPELINES
        for tracing in (False, True)
    }
    actual_attempt_keys = {(attempt.pipeline, attempt.tracing) for attempt in attempts}
    return bool(
        tracing_mode == "both"
        and actual_attempt_keys == expected_attempt_keys
        and len(attempts) == len(expected_attempt_keys)
        and all(attempt.retains_attempt_evidence for attempt in attempts)
        and tracing_result_parity
    )


@dataclass(frozen=True, slots=True)
class _ExecuteReportInputs:
    """Packed execute-mode campaign report inputs (python:S107)."""

    source_revision: str
    source_provenance: dict[str, object]
    parity_ok: bool
    pipelines: tuple[str, ...]
    registered_pipelines: tuple[str, ...]
    registry_completed: subprocess.CompletedProcess[str]
    registry_stdout_path: Path
    attempts: list[AttemptEvidence]
    online_attempt: AttemptEvidence
    phases: tuple[PhaseEvidence, ...]
    attempt_gate: bool
    tracing_result_parity: bool
    tracing_mode: str
    tracing_pairs: dict[str, dict[bool, str]]
    standalone_fixture_evidence: dict[str, object]
    workflow_fixture_evidence: dict[str, object]
    canonical_unchanged: bool
    before: dict[str, str]
    after: dict[str, str]
    binding: dict[str, object]
    external_gate: dict[str, object]
    scorecard: dict[str, dict[str, float]]
    residual_limitations: list[str]
    finding_ids: list[str]
    residual_finding_gate: dict[str, object]
    core_complete: bool


def _build_execute_report(inputs: _ExecuteReportInputs) -> dict[str, object]:
    """Assemble the execute-mode campaign report payload."""
    return {
        "schema_version": 1,
        "generated_at": _utc_now(),
        "source_revision": inputs.source_revision,
        "source_provenance": inputs.source_provenance,
        "status": (
            "awaiting_external_evidence" if inputs.core_complete else "incomplete"
        ),
        "pipeline_config_parity": inputs.parity_ok,
        "pipelines": list(inputs.pipelines),
        "registered_pipelines": list(inputs.registered_pipelines),
        "registry_command_evidence": {
            "command": list(inputs.registry_completed.args),
            "stdout_path": str(inputs.registry_stdout_path),
            "stdout_sha256": _sha256_file(inputs.registry_stdout_path),
        },
        "attempt_gate": {
            "satisfied": inputs.attempt_gate,
            "attempt_count": len(inputs.attempts),
            "required_tracing_mode": "both",
            "actual_tracing_mode": inputs.tracing_mode,
            "tracing_result_parity": inputs.tracing_result_parity,
            "representative_tracing_result_parity": inputs.tracing_result_parity,
            "tracing_result_signatures": inputs.tracing_pairs,
            "successful_attempt_count": sum(
                attempt.exit_code == 0 for attempt in inputs.attempts
            ),
            "failed_attempt_count": sum(
                attempt.exit_code != 0 for attempt in inputs.attempts
            ),
        },
        "attempts": [asdict(item) for item in inputs.attempts],
        "online_attempt_gate": {
            "satisfied": inputs.online_attempt.satisfies_closure,
            "attempt": asdict(inputs.online_attempt),
        },
        "workflow_phase_gate": {
            "satisfied": all(phase.satisfies_closure for phase in inputs.phases),
            "phases": [asdict(phase) for phase in inputs.phases],
        },
        "standalone_fixture_evidence": inputs.standalone_fixture_evidence,
        "workflow_fixture_evidence": inputs.workflow_fixture_evidence,
        "canonical_signature_gate": {
            "satisfied": inputs.canonical_unchanged,
            "before": inputs.before,
            "after": inputs.after,
        },
        "campaign_binding": inputs.binding,
        "external_evidence_gate": inputs.external_gate,
        "scorecard": inputs.scorecard,
        "residual_limitations": inputs.residual_limitations,
        "finding_ids": inputs.finding_ids,
        "residual_finding_gate": inputs.residual_finding_gate,
    }


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    repo_root = _repo_root()
    audit_root = args.audit_root.expanduser()
    canonical_roots = tuple(
        path
        for path in (args.canonical_data_root, args.canonical_log_root)
        if path is not None
    )
    try:
        (
            evidence,
            source_provenance,
            registered_pipelines,
            registry_completed,
        ) = _bootstrap_campaign_context(
            args,
            repo_root=repo_root,
            audit_root=audit_root,
            canonical_roots=canonical_roots,
        )
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, sort_keys=True))
        return 2
    pipelines = _discover_chembl_pipelines(repo_root)
    parity_ok = pipelines == registered_pipelines == CHEMBL_PIPELINES
    planned = _planned_attempts(pipelines, args.tracing_mode)
    source_revision = str(source_provenance["revision"])
    if args.finalize_report is not None:
        try:
            return _finalize_campaign(
                args=args,
                audit_root=audit_root,
                source_provenance=source_provenance,
                evidence=evidence,
            )
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            print(json.dumps({"status": "error", "error": str(exc)}, sort_keys=True))
            return 2
    external_gate = _evidence_gate(
        evidence,
        audit_root=audit_root,
        source_revision=source_revision,
    )
    scorecard = _scorecard(external_gate)
    residual_finding_gate = _residual_findings_gate(
        args.residual_limitation,
        args.finding_id,
    )
    if not args.execute:
        payload = _planned_payload(
            parity_ok=parity_ok,
            pipelines=pipelines,
            registered_pipelines=registered_pipelines,
            planned=planned,
            source_revision=source_revision,
            source_provenance=source_provenance,
            registry_completed=registry_completed,
            external_gate=external_gate,
            scorecard=scorecard,
            residual_limitations=args.residual_limitation,
            finding_ids=args.finding_id,
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if parity_ok else 1

    python = args.python.expanduser().absolute()
    audit_root.mkdir(parents=True, exist_ok=True)
    registry_evidence_root = audit_root / "evidence" / "raw"
    registry_evidence_root.mkdir(parents=True, exist_ok=True)
    registry_stdout_path = registry_evidence_root / "registry-command.stdout"
    atomic_write_text(registry_stdout_path, registry_completed.stdout)
    before = {str(path.resolve()): _tree_signature(path) for path in canonical_roots}
    assert args.canonical_data_root is not None
    cached_bronze_root, standalone_fixture_evidence = _stage_standalone_fixture_cache(
        repo_root=repo_root, audit_root=audit_root
    )
    # Validate and stage the cross-entity workflow fixture before spending the
    # campaign budget on 30 standalone processes.  A bounded input snapshot can
    # be valid for every individual pipeline yet still lack join-compatible
    # assay/target/publication rows; fail that contract before execution.
    workflow_fixture_root, workflow_fixture_evidence = _stage_workflow_fixture(
        canonical_bronze_root=cached_bronze_root,
        audit_root=audit_root,
    )
    attempts = _run_standalone_attempts(
        repo_root=repo_root,
        audit_root=audit_root,
        python=python,
        planned=planned,
        limit=args.limit,
        timeout_seconds=args.timeout_seconds,
        cached_bronze_root=cached_bronze_root,
    )
    online_attempt = _run_attempt(
        repo_root=repo_root,
        audit_root=audit_root,
        python=python,
        pipeline="chembl_activity",
        limit=args.limit,
        tracing=False,
        timeout_seconds=args.timeout_seconds,
        cached_bronze_root=None,
        run_mode="online",
    )
    phases = _run_campaign_phases(
        repo_root=repo_root,
        audit_root=audit_root,
        python=python,
        limit=args.limit,
        timeout_seconds=args.timeout_seconds,
        workflow_fixture_root=workflow_fixture_root,
    )
    after = {str(path.resolve()): _tree_signature(path) for path in canonical_roots}
    canonical_unchanged = before == after
    tracing_pairs = {
        pipeline: {
            attempt.tracing: attempt.result_signature
            for attempt in attempts
            if attempt.pipeline == pipeline
        }
        for pipeline in CHEMBL_PIPELINES
    }
    tracing_parity = _tracing_result_parity(attempts)
    attempt_gate = _attempt_gate_satisfied(
        tracing_mode=args.tracing_mode,
        attempts=attempts,
        tracing_result_parity=tracing_parity,
    )
    core_complete = bool(
        parity_ok
        and canonical_unchanged
        and attempt_gate
        and online_attempt.satisfies_closure
        and all(phase.satisfies_closure for phase in phases)
    )
    binding = _campaign_binding(
        source_provenance=source_provenance,
        attempts=attempts,
        online_attempt=online_attempt,
        phases=phases,
    )
    report = _build_execute_report(
        _ExecuteReportInputs(
            source_revision=source_revision,
            source_provenance=source_provenance,
            parity_ok=parity_ok,
            pipelines=pipelines,
            registered_pipelines=registered_pipelines,
            registry_completed=registry_completed,
            registry_stdout_path=registry_stdout_path,
            attempts=attempts,
            online_attempt=online_attempt,
            phases=phases,
            attempt_gate=attempt_gate,
            tracing_result_parity=tracing_parity,
            tracing_mode=args.tracing_mode,
            tracing_pairs=tracing_pairs,
            standalone_fixture_evidence=standalone_fixture_evidence,
            workflow_fixture_evidence=workflow_fixture_evidence,
            canonical_unchanged=canonical_unchanged,
            before=before,
            after=after,
            binding=binding,
            external_gate=external_gate,
            scorecard=scorecard,
            residual_limitations=args.residual_limitation,
            finding_ids=args.finding_id,
            residual_finding_gate=residual_finding_gate,
            core_complete=core_complete,
        )
    )
    output_path = audit_root / OBSERVABILITY_CLOSURE_CAMPAIGN_REPORT
    atomic_write_text(
        output_path,
        json.dumps(report, indent=2, sort_keys=True) + "\n",
    )
    print(
        json.dumps(
            {"status": report["status"], "report": str(output_path)}, sort_keys=True
        )
    )
    return 0 if core_complete else 1
