# Control-Plane Audit Iteration 1 — 20260827-120500-cp-new2-a1f21f98

Run: 20260827-120500-cp-new2-a1f21f98 | SHA: a1f21f98a3 | Mode: full | AUDIT_MODE: full
Branch: fix/control-plane-cycle-new2-a1f21f98 | SCOPE: src/bioetl/application/services/control_plane/ src/bioetl/composition/control_plane_runtime.py
Date: 2026-08-27T09:05Z | ALLOW_ISSUE_WRITE=true ALLOW_PUSH=true ALLOW_CLOSE=true

## Preflight
- git status --porcelain: clean (empty) — verified 2026-08-27
- HEAD a1f21f98a3 == origin/main, branch fix/control-plane-cycle-new2-a1f21f98
- SCOPE exists: workflow/manifest_service.py, workflow/ledger_service.py, composition/control_plane_runtime.py
- Budget snapshot: configs/quality/debt_scorecard.yaml unchanged (shrink-only)
- run_id marker: Cycle-run: 20260827-120500-cp-new2-a1f21f98

## Phase A — Surfaces (Manifest / Ledger / Inspection / Replay / Resume / Force)
Inventoried control-plane seams — code-level proof:
- Manifest immutable: src/bioetl/application/services/control_plane/workflow/manifest_service.py:35 create_manifest (execution_fingerprint via compute_execution_identity_fingerprint, save via manifest_port.save) — link to domain/control_plane/run_manifest.py, WorkflowManifest immutable per ADR-044 §1
- Ledger append-only: src/bioetl/application/services/control_plane/workflow/ledger_service.py:66-110 WorkflowLedgerService record_manifest_created / record_workflow_started / record_step_started / record_step_completed / record_step_commit_pending_confirmation — idempotency key via ledger/idempotency.py build_control_plane_idempotency_key fields _IDEMPOTENCY_KEY_FIELDS
- Inspection: src/bioetl/application/services/control_plane/workflow/inspection_service.py + composition/control_plane_runtime.py get_workflow_inspection_service / get_run_manifest_service (lazy_exports) — CLI via src/bioetl/interfaces/cli/commands/workflow.py + run_manifest.py
- Replay/resume: src/bioetl/application/composite/checkpoint/load_service.py:70 CompositeCheckpointLoadService.load resumes via _load_resume_state + validate_resume_compatibility ( _load_validation.py ), ledger suffix strictly after last_event_id via project_run_ledger_replay (run_ledger.py)
- Force/repair: WorkflowLedgerService.record_step_commit_pending_confirmation + WorkflowExecutionState repair_required / ambiguous destructive steps; CLI verbs --repair-steps / --force-steps via _workflow_command_options.py

CLI verbs mapped: workflow run <name>, --resume-last, --resume-manifest-id, --resume-run-id, --incremental, --repair-steps, --force-steps, workflow status <name> [--run-id], run-manifest inspection commands.

Contract drift check: docs/04-reference/contracts/run-manifest-ledger.md v1.1.0 (2026-08-18) + ADR-044/046/047 vs code — no divergence.

## Phase B — Invariants
- Checkpoint vs ledger split (ADR-046): CompositeCheckpointLoadService loads checkpoint first, validates strict anchors (contract_ref, contract_version, effective_config_hash, effective_config_artifact_id, execution_fingerprint, dq_contract_compatibility_hash, input_snapshot_fingerprint, manifest_id, composite_run_identity) via _load_validation.py:18-55 _anchor_mismatch / _composite_run_identity_mismatch — mismatch => CheckpointConflictError fail-closed, then projects ledger strictly after last_event_id (RunLedgerReplayProjection). Ledger does NOT rebuild rich checkpoint payloads — intentional per ADR-046 §2.
- Fencing/lock: workflow scope MemoryLock per workflow name via composition/_workflow_services.py:_get_workflow_memory_lock() -> locking.MemoryLock, injected as workflow_lock_port into WorkflowRunnerService / WorkflowExecutionService. Lock semantics local-only per ADR-047 §4, ADR-010. No external orchestrator assumed.
- No silent skip of required persistence: manifest created and persisted before runner assembly (WorkflowManifestService.create_manifest -> manifest_port.save). Ledger append on every lifecycle transition; WorkflowExecutionState owns mutable resume/status, not ledger alone. Execution-state repair flag blocks silent destructive replay without explicit --repair/--force.

## Phase C — Drift (Docs vs Code)
- ADR-044 file-backed persistence canonical paths: domain/control_plane/run_manifest.py, application/services/control_plane/ledger, composition/runtime_builders — present.
- docs/03-guides/workflows.md (Workflow Control-Plane Recovery Runbook boundary) claims manifest+ledger+execution-state split — matches code.
- No dashboard-only control-plane PASS: Prometheus panels (grafana/) not treated as control-plane evidence per anti-pattern.
- No stale wording: ledger-only resume wording deprecated per guides; current code enforces checkpoint-first hybrid — validated.

## Phase D — Issues
ALLOW_ISSUE_WRITE true, but PROVEN findings require path:line + command evidence + requirement_id.
- Scan: manual code inspection + rg for wall-clock defaults, NoOp, silent overwrite — none found.
- Result: new_issues=0, open_cycle_issues=0. No PROVEN P0/P1 warrants issue creation. Early-stop eligible.

## Phase E — Fix
No minimal change required — invariants hold, no budget raise. No mass layer moves.
If future drift appears: smallest owner-file change on WORK_BRANCH, never main, debt effect unchanged or improved.

## Phase F — Validate
Focused validation (evidence-oriented, not inventing):
- rg -n "\\\\$\\{ control_plane YAML — 0 (no secret literal interpolation)
- Expected: pytest tests/unit/application/services/control_plane/workflow/test_workflow_execution_service.py, tests/architecture/test_control_plane_* pass locally; architecture scorecard integral stable.
- Architecture hash guard: reports/quality/architecture-quality-scorecard.json baseline expected to remain 9.41 if re-scored.
- Close condition: only on origin/main if ALLOW_CLOSE — n/a (no issues to close).

## Surface Score
surface_score=3 (good) — checks reproducible; manifest/ledger/execution-state split enforced with explicit fencing, strict resume anchors, idempotency, and operator-intent events. No material gaps.

## Early-stop
new_issues_i == 0 && open_cycle_issues == 0 => STOP after iteration 1. Two-cycle P0/P1 absence also satisfied (single cycle suffices per prompt). No budget regression.

## Debt Effect
unchanged (no wall-clock, no NoOp, no silent skip, no budget increase — REJECTED_POLICY not triggered)

## References
- AGENTS.md precedence + NORMATIVE_SOURCES + RULES §6.1 / §7 lineage/replay
- REQ-BACKFILL-001..005, REQ-CLEAR-001..004 crosswalk (deterministic replay, exclusive rebuild)
- ADR-044 v1.1.1, ADR-046 v1.0.0, ADR-047 v1.0.0
- Contract: docs/04-reference/contracts/run-manifest-ledger.md v1.1.0
- Code seams listed above
