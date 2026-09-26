# Documentation Audit Report (BioETL v5.23+)

## Summary

- Date: 2026-07-31
- Scope: issue #7340; specialized category audit of composite/checkpoint
  semantics (ADR-026), observability (ADR-017), and storage/Medallion/quarantine
  semantics (ADR-002).
- Verification mode: `verify-architecture` category mode plus a focused
  `documentation-audit` reconciliation against current code, configs, tests,
  and later accepted ADRs.
- Overall status: **WARN**. The focused runtime and architecture checks pass
  (187 tests across the selected groups), but the three accepted ADR documents
  contain actionable documentation drift. No production-code defect was found
  by this audit.
- Technical-debt outcome: unchanged. No budget, exemption, threshold, or
  production surface was modified.

## Inventory

- Docs scanned: ADR-002, ADR-017, ADR-026, ADR-046, RULES §2/§3,
  REQUIREMENTS traceability rows, composite/storage/observability reference
  docs, and their repository search neighborhoods.
- Runtime/config surfaces inspected:
  `src/bioetl/application/composite/**`,
  `src/bioetl/infrastructure/storage/**`,
  `src/bioetl/infrastructure/quarantine/**`,
  `src/bioetl/domain/aggregates/**`, observability ports/adapters/composition,
  and `configs/composites/publication.yaml`.
- Entry points checked: `README.md`, `mkdocs.yml`, ADR registry, and the
  documentation link/drift tooling.

## Findings by severity

### Critical

- None.

### High

#### DOC-7340-001 — ADR-026 does not state the current hybrid checkpoint/ledger boundary

- Location: `docs/02-architecture/decisions/ADR-026-composite-pipeline-pattern.md:780-835,1315-1357`.
- Evidence: ADR-026 describes checkpoint-only resume and its pseudocode loads,
  saves, and deletes only checkpoint state. It contains no `ledger`,
  `manifest`, or exact-replay boundary. Current runtime dependencies include
  both `checkpoint_manager` and `run_ledger_service`
  (`src/bioetl/application/composite/runtime_models.py:104-129`), and reject
  `exact_replay` for composite execution
  (`src/bioetl/application/composite/runtime_models.py:92-99`). ADR-046 records
  the implemented boundary explicitly: trusted checkpoint baseline followed by
  ledger entries strictly after `last_event_id`
  (`ADR-046-checkpoint-vs-ledger-resume.md:64-125`).
- Verification 1: focused composite/checkpoint architecture tests passed (28
  tests), including canonical surface and facade guards.
- Verification 2: composite resume/determinism/checkpoint integration group
  passed (55 tests), confirming this is documentation drift rather than an
  observed runtime failure.
- Action: add a concise “Current resume boundary” section to ADR-026 that links
  ADR-044/ADR-046, identifies checkpoint state as the operational baseline,
  identifies ledger replay as bounded suffix provenance recovery, and states
  that strict composite exact replay is unsupported. Avoid duplicating the full
  ADR-046 rationale.

#### DOC-7340-002 — ADR-026 presents noncanonical config and Python as copyable implementation

- Location: `docs/02-architecture/decisions/ADR-026-composite-pipeline-pattern.md:780-835,1015-1105,1294-1306`.
- Evidence: executable-looking examples use invalid Python identifiers such as
  `seed-runner-factory`, `self.-checkpoint-manager`, and `seed-result`, and the
  YAML example uses kebab-case keys such as `join-keys`, `timeout-seconds`,
  `left-outer`, and `checkpoint-enabled`. The live config uses canonical
  snake_case (`output_keys`, `join_keys`, `timeout_seconds`, `left_outer`,
  `conflict_resolution`) in `configs/composites/publication.yaml:121-251`.
  Current runtime uses valid typed names such as `checkpoint_manager`,
  `run_ledger_service`, and `CompositeRuntimeConfig`
  (`src/bioetl/application/composite/runtime_models.py:73-129`).
- Verification 1: `rg` comparison of ADR examples and the live config/runtime
  found the naming split above.
- Verification 2: composite architecture/config contract tests passed; thus the
  canonical runtime/config is internally consistent while the ADR examples are
  stale.
- Action: either replace these blocks with small current snippets or label them
  explicitly as non-executable historical design sketches. Prefer links to the
  live config schema and public facades over maintaining a second implementation.

### Medium

#### DOC-7340-003 — ADR-026 rollout status contradicts its Accepted/current implementation status

- Location: `docs/02-architecture/decisions/ADR-026-composite-pipeline-pattern.md:1336-1363,1400-1428`.
- Evidence: every Phase 1–4 rollout item remains unchecked, including domain
  models, runner, coordinator, merge service, CLI, checkpoint service, and
  runtime options that exist and are covered by the passing focused suites.
  The generic acceptance checklist is also unchecked while the compliance table
  says verification is `pass`.
- Verification 1: current classes were found at
  `application/composite/runner_pkg/runner.py`, `coordinator.py`,
  `merge_service.py`, and `checkpoint/service.py`.
- Verification 2: 28 focused architecture tests and 55 focused
  resume/determinism tests passed.
- Action: convert rollout into a dated implemented/deferred matrix. Do not mark
  aspirational Phase 4 items complete unless runtime evidence exists.

#### DOC-7340-004 — ADR-002 does not describe the current reject/quarantine boundary

- Location: `docs/02-architecture/decisions/ADR-002-medallion-architecture.md:35-68,70-103`.
- Evidence: ADR-002 describes only progressive Bronze/Silver/Gold quality and
  does not mention filtered-out versus quarantined records, immutable
  quarantine payloads, or append-only status transitions. Current runtime has a
  unified `common.quarantine` adapter
  (`src/bioetl/infrastructure/quarantine/unified.py:118-197`) and append-only
  status events (`src/bioetl/infrastructure/quarantine/status_events.py:1-67`).
  The later normative boundary is refined by ADR-045, ADR-050, and ADR-051, but
  none is linked from ADR-002.
- Verification 1: Medallion/quarantine/Gold category group passed 26 tests.
- Verification 2: the resume/storage/quarantine group passed 55 tests,
  including `QuarantineEntry` and quarantine manager coverage.
- Action: add a short refinement note and links to ADR-045/050/051. State that
  quarantine/reject evidence is adjacent control data, not a fourth Medallion
  layer, and avoid copying their detailed taxonomy into ADR-002.

#### DOC-7340-005 — ADR-002 compliance evidence is generic rather than executable

- Location: `docs/02-architecture/decisions/ADR-002-medallion-architecture.md:70-103`.
- Evidence: the compliance row says implementation and validation expectations
  are documented, but the Verification section only says to run “relevant
  tests” and all acceptance boxes remain unchecked. The repository has concrete
  gates (`test_medallion_invariants.py`, `test_medallion_policy.py`,
  `test_quarantine_immutability.py`, Gold strict validation tests) that are not
  linked.
- Verification 1: repository test inventory located the concrete guards.
- Verification 2: the selected 26-test group passed.
- Action: link the named architecture/contract gates and make the acceptance
  status evidence-based. Do not turn the ADR into a generated test inventory.

### Low

#### DOC-7340-006 — ADR-017 has one inconsistent Prometheus label spelling

- Location: `docs/02-architecture/decisions/ADR-017-observability-architecture.md:150-161,235-243`.
- Evidence: the canonical table uses `run_type`, while the justification list
  says `run-type`. Runtime contracts and
  `docs/04-reference/contracts/observability.md:235-269` consistently use
  `run_type`.
- Verification 1: repository search confirms `run_type` across code and the
  canonical observability contract.
- Verification 2: 40 observability architecture/integration tests passed.
- Action: change the single prose spelling to `run_type`.

## Proposed changes (prioritized)

1. Reconcile ADR-026 with ADR-044/046 checkpoint + ledger suffix semantics and
   the explicit unsupported exact-replay boundary.
1. Retire or clearly label ADR-026’s invalid/stale implementation examples;
   point readers to live schemas, configs, and public facades.
1. Replace ADR-026 rollout checkboxes with an implemented/deferred evidence
   matrix.
1. Add ADR-045/050/051 refinement links and concrete test anchors to ADR-002.
1. Correct `run-type` to `run_type` in ADR-017.

## Required decisions

- Decide whether ADR-026 should remain a long implementation handbook or be
  reduced to the durable decision with implementation delegated to current
  architecture/reference docs. The latter minimizes future drift.
- Decide whether completed ADR acceptance checklists should be checked in place
  or replaced by a dated verification table; the repository currently mixes
  both conventions.

## Updated files (if changes applied)

- `reports/ai/issue-7340-specialized-subsystem-analysis-20260731.md` only.
- No production code, config, ADR, runtime instruction, or technical-debt
  budget was modified.

## Dead or orphan docs (candidates)

- None proposed for deletion. ADR-026 is active and referenced broadly; its
  stale implementation sections should be reconciled, not silently removed.

## Verification

- Composite/checkpoint architecture category:
  `pytest tests/architecture/test_composite_layer_boundaries.py tests/architecture/test_composite_canonical_surfaces.py tests/architecture/test_composite_checkpoint_facade_usage.py tests/architecture/test_checkpoint_runtime_facade_usage.py tests/architecture/test_checkpoint_policy_retired_modes_surface.py -q`
  — PASS, 28 tests.
- Observability category:
  `pytest tests/architecture/test_observability_docs_drift.py tests/architecture/test_observability_docs_sync.py tests/architecture/test_observability_metric_governance.py tests/architecture/test_observability_metric_naming_contract.py tests/architecture/test_observability_signal_governance.py tests/integration/test_observability_emission_integration.py tests/integration/test_runtime_metric_emission_consistency.py -q`
  — PASS, 40 tests.
- Medallion/quarantine/Gold category:
  `pytest tests/architecture/test_medallion_invariants.py tests/architecture/test_medallion_policy.py tests/architecture/test_quarantine_immutability.py tests/architecture/test_gold_strict_validation_policy.py tests/architecture/test_gold_validator_strict_runtime_paths.py tests/contract/test_composite_merge_golden.py -q`
  — PASS, 26 tests.
- Composite resume/storage/quarantine category:
  `pytest tests/integration/composite_resume/test_reproducibility_composite_resume_gate.py tests/integration/determinism/test_composite_reproducibility_determinism_gate.py tests/integration/infrastructure/storage/test_composite_checkpoint_writer.py tests/unit/application/core/test_quarantine_manager.py tests/unit/domain/aggregates/test_quarantine_entry.py -q`
  — PASS, 55 tests.
- ADR/docs governance:
  `pytest tests/architecture/test_adr_enforcement_matrix.py tests/architecture/test_adr_registry_governance_sync.py tests/architecture/test_control_plane_runtime_docs_alignment.py tests/architecture/test_documentation_sync.py -q`
  — PASS, 38 tests.
- Link/spec/config validation:
  `python -m scripts.docs check-links --links --specs --configs` — PASS; no
  broken relative links, missing nav docs/specs/configs, or skill-nav errors.
- Runtime mirror/freshness drift:
  `python -m scripts.docs check-drift --runtime-mirrors --freshness` — PASS,
  0 errors and 0 warnings.
- RULES.md and REQUIREMENTS.md sync: their traceability rows correctly point to
  ADR-002/017/026 and the relevant implementation/test families; no direct
  contradiction found in this focused audit.
- Full `tests/architecture` sweep skipped to keep #7340 category-bounded on the
  cloud-mounted checkout. Follow-up command:
  `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/architecture -q`.
- Strict MkDocs build skipped because the focused link/nav validator passed and
  no published docs were changed. Follow-up command:
  `.venv/bin/mkdocs build --strict`.
- Runtime mirror sync: not applicable; `.codex/**` and `.junie/**` were not
  changed.
