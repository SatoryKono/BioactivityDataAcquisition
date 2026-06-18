# Architecture Refactoring RF-001..RF-008 Closeout - 2026-06-17

Scope: GitHub issues #5317 through #5324.

## RF-001 - governance and dependency evidence

Status: complete.

Evidence:

- `docs/02-architecture/generated/module-dependency-map.json`
- `docs/02-architecture/generated/module-dependency-map.md`
- `reports/quality/module-coverage-inventory.json`
- `reports/quality/architecture-quality-scorecard.json`
- `reports/quality/hotspot-family-baseline.json`
- `reports/quality/debt-governance-gates.json`

Verification:

- `python scripts/engineering/qa/generate_architecture_dependency_map.py --check`
- `python -m scripts.engineering.qa report-module-coverage --check`
- `python -m scripts.engineering.qa report-architecture-debt-remote-main-baseline --check`
- `python -m scripts.engineering.qa report-debt-governance-gates --check`
- `python -m scripts.engineering.qa report-family-baseline --check`

Closeout result: generated governance/dependency artifacts are rebound to the
current source tree. Debt governance gates report `26/26` pass, with no failing
or warning gates.

## RF-002 - HTTP control-plane selector context split

Status: complete.

Primary modules:

- `src/bioetl/interfaces/http/control_plane_selector_context.py`
- `src/bioetl/interfaces/http/_control_plane_selector_records.py`
- `src/bioetl/interfaces/http/_control_plane_selector_filters.py`
- `src/bioetl/interfaces/http/_control_plane_selector_payloads.py`

Closeout result: `control_plane_selector_context.py` is now a facade. Record
construction, filtering, and payload rendering are separated by responsibility,
while public constants and functions remain exported through the existing
module.

Verification:

- `pytest tests/unit/interfaces/http/test_health_server_control_plane_identity.py -q`
- `ruff check src/bioetl/interfaces/http/control_plane_selector_context.py src/bioetl/interfaces/http/_control_plane_selector_records.py src/bioetl/interfaces/http/_control_plane_selector_filters.py src/bioetl/interfaces/http/_control_plane_selector_payloads.py`

## RF-003 - observability workflow support split

Status: complete.

Primary modules:

- `src/bioetl/application/services/_observability_workflow_support.py`
- `src/bioetl/application/services/_observability_workflow_lookup_support.py`
- `src/bioetl/application/services/_observability_workflow_traceability_support.py`
- `src/bioetl/application/services/_observability_workflow_evidence_support.py`
- `src/bioetl/application/services/_observability_workflow_next_steps_support.py`
- `src/bioetl/application/services/_observability_workflow_status_support.py`

Closeout result: `_observability_workflow_support.py` is now a compatibility
facade. Lookup, traceability, evidence classification, next-step generation, and
status projection are split into focused helpers.

Verification:

- `pytest tests/unit/application/services/test_observability_workflow_service.py -q`
- `ruff check src/bioetl/application/services/_observability_workflow_support.py src/bioetl/application/services/_observability_workflow_lookup_support.py src/bioetl/application/services/_observability_workflow_traceability_support.py src/bioetl/application/services/_observability_workflow_evidence_support.py src/bioetl/application/services/_observability_workflow_next_steps_support.py src/bioetl/application/services/_observability_workflow_status_support.py`

## RF-004 - RecordProcessor span/error orchestration split

Status: complete.

Primary modules:

- `src/bioetl/application/core/record_processor.py`
- `src/bioetl/application/core/_record_processor_span_support.py`

Closeout result: span lifecycle, span attributes, and operation-error handling
are delegated to `RecordProcessorSpanExecutor`. `RecordProcessor` remains
focused on medallion flow orchestration.

Verification:

- `pytest tests/unit/application/core/test_record_processor.py::TestRecordProcessorTracing -q`
- `ruff check src/bioetl/application/core/record_processor.py src/bioetl/application/core/_record_processor_span_support.py`

## RF-005 - BatchExecutor runtime-state coupling

Status: closed by gated decision.

Evidence:

- `src/bioetl/application/core/batch_executor.py`
- `src/bioetl/application/core/batch_executor_dependencies.py`
- `src/bioetl/application/core/batch_execution_flows.py`
- `src/bioetl/application/core/batch_execution_result_builder.py`
- `src/bioetl/application/core/batch_executor_services.py`

Decision: no broad `BatchExecutor` rewrite is justified in this closeout. The
current implementation already gates runtime-state coupling through dependency
bundles and flow/result helper seams. The family baseline and governance gates
are clean after artifact refresh.

Risk control:

- Keep `BatchExecutorDependencies` as the ownership seam for runtime services.
- Require future changes to pass `report-family-baseline --check` and
  `report-debt-governance-gates --check`.

## RF-006 - retained public entrypoints

Status: complete by refreshed rationale.

Evidence:

- `reports/quality/compatibility-importer-census.json`
- `configs/quality/debt_scorecard.yaml`

Closeout result: retained public entrypoints are not ratcheted upward. Existing
entrypoints remain justified by compatibility/importer-census evidence; the
compatibility importer census artifact is current.

Verification:

- `python -m scripts.engineering.qa report-compatibility-importer-census --check`

## RF-007 - branch coverage gate promotion

Status: closed as not promoted.

Evidence:

- `reports/coverage/coverage.xml`

Current coverage snapshot:

- Branch rate: `0.829902` (`82.99%`)
- Line rate: `0.957688` (`95.77%`)

Decision: do not promote the branch coverage gate yet. The configured promotion
criterion is not met; closing this item as "not planned" avoids lowering or
papering over the branch gate.

## RF-008 - semantic DDD and use-case audit lane

Status: complete.

Evidence:

- `src/bioetl/application/services/_observability_workflow_lookup_support.py`
- `src/bioetl/application/services/_observability_workflow_traceability_support.py`
- `src/bioetl/application/services/_observability_workflow_evidence_support.py`
- `src/bioetl/application/services/_observability_workflow_next_steps_support.py`
- `src/bioetl/application/services/_observability_workflow_status_support.py`
- `src/bioetl/interfaces/http/_control_plane_selector_records.py`
- `src/bioetl/interfaces/http/_control_plane_selector_filters.py`
- `src/bioetl/interfaces/http/_control_plane_selector_payloads.py`
- `src/bioetl/application/core/_record_processor_span_support.py`

Closeout result: the refactoring preserves layer roles. HTTP selector code stays
in `interfaces`, observability dossier assembly remains in `application`, and
RecordProcessor tracing support stays in `application.core` without importing
infrastructure or interfaces.

Verification:

- `lint-imports --config .importlinter`
- `python -m scripts.engineering.qa check-naming --check`
- `python -m scripts.engineering.qa check-c901`
- `python -m scripts.docs check-links --links --specs --configs`
- `python -m scripts.docs check-drift --ports --classes`
