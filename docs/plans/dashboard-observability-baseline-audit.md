# Dashboard Observability Baseline Audit

Last verified: 2026-06-30

Linked rollout: GitHub issues `#5716-#5728`.

## Scope

This audit covers the governed dashboard, RunLedger/control-plane projection,
Gold/read-model, metrics, RBAC, and export rollout. It is a baseline and
architecture gate; it intentionally avoids new production storage/event-store
surfaces.

## Discovered Existing Surfaces

| Surface | Evidence | Finding |
| --- | --- | --- |
| ADRs | `docs/02-architecture/decisions/ADR-017-observability-architecture.md`, `docs/02-architecture/decisions/ADR-019-observability-port-enforcement.md` | Existing observability architecture and port enforcement govern dependency direction. |
| Run ledger | `src/bioetl/domain/control_plane/run_ledger.py`, `src/bioetl/application/services/control_plane/ledger/service.py`, `src/bioetl/infrastructure/control_plane/file_run_ledger_store.py` | Existing append-only control-plane ledger is the rollout event source; no new SQL event store is needed. |
| Dashboard JSON | `grafana/dashboards/*.json` | Existing dashboards cover control-plane, overview, runtime, provider health, DQ, workflow, alerts/SLO, and Silver Reject Explorer. |
| Dashboard docs | `docs/03-guides/dashboards/README.md`, `grafana/README.md` | Extension-first model and selector contracts are already documented. |
| Prometheus rules | `grafana/prometheus-rules/bioetl_observability.yml`, `grafana/prometheus-rules/tests/bioetl_observability.test.yml` | Recording/alert rules exist and are test-governed. |
| Metric governance | `configs/quality/observability_metric_governance.yaml`, `configs/quality/observability_metric_declarations.yaml` | Low-cardinality inventory and runtime cardinality review gates exist. |
| Export surface | `src/bioetl/application/services/export_service.py`, `src/bioetl/domain/ports/export.py`, `src/bioetl/interfaces/cli/commands/export.py` | Governed export is implemented through ports and CLI composition root lookup. |
| Gold contracts | `docs/04-reference/contracts/gold-schemas.md`, `docs/04-reference/contracts/gold/*.json`, `tests/architecture/test_gold_schema_contracts.py` | Gold strict schema surfaces exist and are drift-governed. |
| Quarantine/drilldown | `src/bioetl/interfaces/http/`, `grafana/provisioning/datasources-core/quarantine-explorer.yml` | Run/record drilldown is backend-backed; forensic IDs are not Prometheus labels. |

## Gap Matrix

| Area | Status | Evidence | Resolution |
| --- | --- | --- | --- |
| Baseline discovery | Existing | this file | Recorded real source paths and narrowed rollout assumptions. |
| Event taxonomy | Partial | `docs/04-reference/contracts/observability.md`, `src/bioetl/domain/observability_contract.py` | Added `docs/04-reference/contracts/observability-rollout-contracts.md`. |
| Projection state machines | Partial | RunLedger and HTTP processed-records support | Added rollout projection invariants in `observability-rollout-contracts.md`. |
| Error catalog | Missing | `src/bioetl/domain/error_classifier.py`, `src/bioetl/infrastructure/errors/exception_mapper.py` | Added `configs/contracts/errors/error_catalog.yaml`. |
| Projection strategy | Existing | RunLedger domain/application/infrastructure files | Explicitly selected existing run ledger; no SQL migrations. |
| Metrics | Existing | metric governance configs, dashboards, Prometheus rules | Reused existing low-cardinality governance/tests. |
| Gold/read-model contracts | Existing | Gold schema docs/contracts/tests | Linked dashboard/export use cases to governed sources. |
| Governed export | Partial | export service, writer, CLI | Added audit/ref, checksum path, expiry metadata, role-sensitive redaction. |
| Dashboard validation CI | Existing | `.github/workflows/tests.yml`, Grafana integration tests | Reused existing dashboard/query/provisioning/rule governance gates. |
| Dashboard extension | Existing | shipped dashboard JSON and docs | Extension-first policy preserved; no new top-level dashboard. |
| RBAC/security | Partial | dashboard docs and datasource provisioning | Added `docs/security/rbac-matrix.md` and `docs/security/export-policy.md`. |
| Final verification | Missing | existing architecture/integration tests | Added closeout artifact and architecture closeout gate. |

## Candidate File Changes

- `src/bioetl/domain/ports/export.py`
- `src/bioetl/application/services/export_models.py`
- `src/bioetl/application/services/export_manifests.py`
- `src/bioetl/application/services/export_service.py`
- `src/bioetl/interfaces/cli/commands/export.py`
- `src/bioetl/interfaces/cli/commands/export_support.py`
- `src/bioetl/interfaces/cli/formatters.py`
- `configs/contracts/errors/error_catalog.yaml`
- `docs/04-reference/contracts/observability-rollout-contracts.md`
- `docs/security/rbac-matrix.md`
- `docs/security/export-policy.md`
- `reports/quality/observability-export-dashboard-rollout-closeout.json`
- `tests/architecture/test_observability_export_dashboard_rollout_closeout.py`
- targeted unit tests under `tests/unit/application/services/` and
  `tests/unit/interfaces/cli/commands/`

## Surfaces Not To Create Without Separate Approval

- New SQL event-store migrations.
- A new top-level dashboard family duplicating existing shipped dashboards.
- Prometheus labels for `run_id`, `record_id`, `payload_hash`, manifest IDs,
  execution fingerprints, file paths, or raw payload identifiers.
- Grafana datasources that query raw Bronze/Silver payload storage.
- Domain filesystem/database writes.
- Application imports from infrastructure.

## Prompt Narrowing

- "Bronze event log" means append-only RunLedger/control-plane event log, not
  BioETL data Bronze.
- Row-level drilldown belongs to backend HTTP/control-plane surfaces, not
  Prometheus labels.
- Grafana inspector export is not a governed export surface.
- Gold strict validation stays enabled; dashboards consume stable read models or
  recording rules, not ad-hoc raw joins.

## Verification Commands

- `python3 -m pytest tests/unit/application/services/test_export_models.py tests/unit/application/services/test_export_manifests.py tests/unit/application/services/test_export_service.py -q`
- `python3 -m pytest tests/unit/interfaces/cli/commands/test_export_support.py tests/unit/interfaces/cli/commands/test_export.py -q`
- `python3 -m pytest tests/architecture/test_observability_export_dashboard_rollout_closeout.py -q`
- `python3 -m pytest tests/architecture/test_observability_metric_governance.py tests/architecture/test_observability_dashboard_contracts.py -q`
- `python3 -m pytest tests/integration/test_grafana_config.py tests/integration/test_grafana_dashboard_query_governance.py tests/integration/test_prometheus_rules_config.py -q`
