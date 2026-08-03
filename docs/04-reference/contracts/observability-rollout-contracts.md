# Observability Dashboard And Export Rollout Contracts

Last verified: 2026-06-30

This contract narrows the dashboard/export rollout to existing BioETL
control-plane and observability surfaces. It does not introduce a new SQL event
store, a new Bronze semantics, or a new domain state machine.

## Event Taxonomy

The authoritative occurrence log for this rollout is the append-only
RunLedger/control-plane event log. "Bronze event log" means this namespaced
control-plane event log, not BioETL data Bronze.

Stable envelope fields:

| Field | Contract |
| --- | --- |
| `event_id` | Deterministic event identity or ledger entry identity. |
| `event_type` | Bounded taxonomy value. |
| `event_version` | Additive schema version. |
| `occurred_at` | Emitted after the aggregate state change. |
| `pipeline_id` | Bounded pipeline identifier. |
| `run_id` | Payload identity used for backend drilldown; forbidden as a Prometheus label. |
| `stage_id` | Bounded stage or projection stage. |
| `correlation_id` / `trace_id` | Diagnostic correlation only, not projection truth. |
| `payload` | Immutable event facts; derived read-model fields are recomputed from governed rules. |
| `schema_version` | Contract version for replay and DLQ policy. |

Canonical event families:

| Family | Source | Projection target |
| --- | --- | --- |
| `run` | RunManifest and RunLedger | `run_summary` |
| `stage` | pipeline stage lifecycle entries | `stage_summary` |
| `batch` | batch metrics and run ledger facts | `stage_summary` |
| `record` | DQ/quarantine/read-model facts | `record_latest`, `record_history` |
| `provider` | provider health metrics and adapters | `provider_health` |
| `error` | canonical error catalog | `error_facts` |
| `export` | governed export service result and sidecars | `export_jobs` |

Malformed or unknown events are routed by policy to DLQ/triage surfaces without
mutating source payloads. Unknown fields must be additive versioned extensions
or ignored by deterministic projection rebuild.

## Projection State Machines

Projection states are read-model states unless an existing domain aggregate
already owns the lifecycle.

| Projection | Current-state key | Invariants |
| --- | --- | --- |
| `run_summary` | `(run_id)` | Terminal run state is selected by ordered ledger sequence; replay is deterministic. |
| `stage_summary` | `(run_id, stage_id)` | Stage status is derived after aggregate state changes; skipped stages remain explicit `SKIPPED` evidence. |
| `record_latest` | `(run_id, record_id)` | Exactly one latest state per key; ties fail closed by deterministic sequence ordering. |
| `record_history` | `(run_id, record_id, sequence_no)` | Full lineage is append-only and queryable. |
| `error_facts` | `(run_id, canonical_error_code, sequence_no)` | Grouping uses canonical catalog codes only. |
| `provider_health` | `(provider, observed_at_bucket)` | Low-cardinality provider status, not per-request IDs. |
| `export_jobs` | `(audit_ref)` | Export lifecycle follows `requested -> authorized -> materialized -> expired/revoked/failed`. |

Quarantine payloads remain immutable. `QUARANTINED` is not a generic DQ-failure
synonym; it means the record is preserved for governed inspection/remediation.

## Projection Strategy

Projection rebuild consumes existing ledger/control-plane evidence first:

- `src/bioetl/domain/control_plane/run_ledger.py`;
- `src/bioetl/application/services/control_plane/ledger/service.py`;
- `src/bioetl/infrastructure/control_plane/file_run_ledger_store.py`;
- HTTP-backed dashboard surfaces under `src/bioetl/interfaces/http/`.

If a future storage backend needs a different append-only adapter, it must be
introduced behind a domain/application port and wired only in the composition
root. SQL migrations are not part of this rollout.

Replay rules:

- ordering is deterministic by ledger sequence and event identity;
- duplicate delivery is idempotent;
- watermarks/checkpoints are projection facts, not domain truth;
- raw payloads are never mutated during rebuild.

## Gold And Read-Model Contracts

Dashboards and exports consume stable Gold/read-model or recording-rule sources:

| Use case | Governed source |
| --- | --- |
| run overview | RunManifest/RunLedger-backed control-plane projection |
| stage diagnostics | stage/run summary projection and recording rules |
| record explorer summary | backend drilldown and quarantine projection |
| provider health | low-cardinality provider health metrics |
| quarantine/error slices | canonical error catalog and quarantine projection |
| export job status | governed export result and sidecar manifests |

Grafana must not query raw Bronze/Silver storage directly and must not implement
business joins in panel expressions. Gold strict validation remains the default
contract for Gold tables; contract drift is enforced by schema/dashboard CI.

## Enforcement

- Domain boundary: `tests/architecture/test_strict_architecture_contracts.py`.
- Observability event mapping: `tests/unit/domain/test_observability_event_mapping.py`.
- Run ledger projection and replay: `tests/unit/application/services/test_control_plane_service_seams.py`.
- Dashboard/query governance: `tests/integration/test_grafana_dashboard_query_governance.py`.
- Metric cardinality governance: `tests/architecture/test_observability_metric_governance.py`.
- Gold contract drift: `tests/architecture/test_gold_schema_contracts.py`.
- Rollout closeout: `tests/architecture/test_observability_export_dashboard_rollout_closeout.py`.
