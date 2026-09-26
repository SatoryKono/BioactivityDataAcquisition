# CodeRabbit 2026-09-25 — актуальность находок

- Каталог: `reports\quality\coderabbit\20260925_085141`
- Audit root SHA: `6bb04917c209`
- Baseline main SHA: `32d77a51e556`
- Findings extracted: **145** (ok-leaves only)
- Severity: {'minor': 43, 'major': 82, 'trivial': 17, 'critical': 3}

## Incomplete scopes (нет usable findings)
- `S03-infra-adapters`: {'findings_in_jsonl': 0, 'event_types': {'review_context': 1, 'status': 3, 'error': 1}}
- `S05-interfaces`: rate_limit/connection failed
- `S06a/S06b-tests-architecture`: all files ignored
- `S07-configs-quality`: all files ignored
- `S08a/S08b-docs`: all files ignored
- `S00c-domain-small-subdirs`: review failed / 0 findings

## Critical — ручная верификация
### [АКТУАЛЬНО] `src/bioetl/application/core/batch_executor_loop_flow.py:114-119`
- Evidence: still references fetched/total_fetched near span, records_bronze not used at cited call site
- Finding: Update the `ensure_extraction_not_shutdown` and `save_periodic_checkpoint_for_loop` calls in the batch execution loop to use `iteration_context.progress_state.records_bronze` as the checkpoint count instead of fetched-record counts, so checkpoints only include confirmed records. Save periodic checkpoints only after the buffered batch is flushed, and update the `save_periodic_checkpoint` interval c

### [АКТУАЛЬНО] `src/bioetl/application/core/batch_execution/lifecycle.py:179-193`
- Evidence: still references fetched/total_fetched near span
- Finding: Update the shutdown and exception checkpoint calls in the finalization flow to use the confirmed Bronze-record count instead of finalization_context.total_fetched, which includes records not yet committed. Apply the change to save_checkpoint_on_shutdown and save_checkpoint_on_exception; preserve their existing offsets and other arguments.

### [АКТУАЛЬНО] `src/bioetl/composition/_resource_management.py:79-87`
- Evidence: _ensure_registrations() still no PROVIDERS scope
- Finding: Update `_bootstrap_registered_resource` and `preview_cleanup` to ensure registrations with the `PROVIDERS` scope instead of calling the pipeline-scoped `_ensure_registrations()` without a registry. Reuse the registration API and scope symbols available in the code; if `preview_cleanup` requires pipeline registrations, pass it an explicit registry created with `create_registry()`.

## Spot-checks (selected majors/criticals)
- **НЕ АКТУАЛЬНО / ИЗМЕНИЛОСЬ** `src/bioetl/domain/ports/observability/metrics.py:108` — already loopback or missing
- **АКТУАЛЬНО** `src/bioetl/domain/ports/observability/metrics.py:9-23` — present=['resolve_metric_labels'] missing=['forbidden']
- **АКТУАЛЬНО** `src/bioetl/composition/factories/services/bundle.py:166-168` — present=['extract_entity_type', '_extract_entity_type'] missing=[]
- **АКТУАЛЬНО** `src/bioetl/composition/factories/storage/clear_mixin.py:107-117` — present=['table_name'] missing=['clear_delta']
- **АКТУАЛЬНО** `src/bioetl/application/core/batch_executor_loop_flow.py:114-119` — still uses fetched counts
- **АКТУАЛЬНО** `src/bioetl/application/core/batch_execution/lifecycle.py:179-193` — still uses fetched counts
- **АКТУАЛЬНО** `src/bioetl/composition/_resource_management.py:79-87` — still bare _ensure_registrations()
- **АКТУАЛЬНО** `src/bioetl/composition/_service_registry.py:36` — present=['_REGISTRY'] missing=['mutable']
- **АКТУАЛЬНО** `src/bioetl/composition/_workflow_services.py:161-166` — present=['_workflow_memory_lock', 'lock'] missing=[]
- **АКТУАЛЬНО** `src/bioetl/domain/value_objects/run_context.py:109-113` — present=['started_at'] missing=['utcoffset']
- **АКТУАЛЬНО** `src/bioetl/domain/normalization/_chembl_units.py:22-39` — present=['_UNIT_ALIASES'] missing=['case']

## Proposed GitHub issues (только по актуальным кластерам)

### ISSUE A — [P0] Checkpoint count uses fetched instead of confirmed bronze
Scope: `batch_executor_loop_flow.py`, `batch_execution/lifecycle.py`
Source: 2× critical from S01-app-core. Still uses fetched/total_fetched at checkpoint sites.

### ISSUE B — [P0] Composition resource bootstrap without PROVIDERS scope
Scope: `composition/_resource_management.py` (`_bootstrap_registered_resource`, `preview_cleanup`)
Source: 1× critical from S04-composition.

### ISSUE C — [P1] Metrics port: label allowlist + loopback default
Scope: `domain/ports/observability/metrics.py`
Source: 2× major from S00a.

### ISSUE D — [P1] Domain normalization/VO hardening cluster
Scope: chembl units case-sensitivity, standard profile overrides, RunContext UTC offset, chembl policy registry idempotency, protein class hierarchy, etc.
Source: ~20 major domain findings (triage individually in issue body).

### ISSUE E — [P1] Composition correctness (non-layering)
Scope: entity_type extraction, clear_delta None table, service registry mutable global, workflow memory lock race, replay parentage propagation, config cache key resolve, etc.
Source: subset of S04 majors that are concrete bugs/races, not pure 'move to application' advice.

### ISSUE F — [P2] Composition layering debt (move logic out of composition)
Scope: health_service persistence, archive_assessment, run_manifest policy modules, artifact publication policy.
Source: architectural majors; valid as debt but not runtime defects.

### ISSUE G — [P2] Application control-plane / app-core residual majors
Scope: remaining S01/S02 majors after checkpoint issue extracted.

## Not proposed as issues
- Incomplete leaves (S03/S05/S06/S07/S08): re-run CodeRabbit first.
- Trivial/minor doc-only items: batch into ISSUE F/G or skip.
- Pure 'move to application layer' without concrete defect: ISSUE F only.
