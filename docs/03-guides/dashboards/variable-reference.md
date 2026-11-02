______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-08-05'

______________________________________________________________________

# Grafana Dashboard Variable Reference

Дата сверки: **2026-10-02**. Five-dashboard cutover approved in ADR-053.

Machine-readable selector SSOT: `docs/03-guides/dashboards/contracts/selector-contracts.yaml`.

Primary operator dashboards expose the shared context shell: `$workflow`, `$pipeline`, `$run_type`, `$run_id`.
`$workflow` is Single-select with Include All. It remains single-select with Include All across primary dashboards.
`$pipeline` is single-select with Include All; native defaults browse All.
`$run_id` is HTTP-backed control-plane identity context, never a Prometheus label.
Exact-run handoffs retain workflow, pipeline, run type, Run ID and time; the global Run Explorer bus resets the selection.

$stage` belongs to Data Quality only. Live provider filtering belongs to Incident Workspace; saved Provider Evidence in Overview needs no provider/adapter selector.

| Dashboard | Variable | Selection / visibility | Default | Description |
| --- | --- | --- | --- | --- |
| `bioetl-control-plane-v1` | `$workflow` | Single + Include All | `$__all` | Shared operator context: workflow evidence selector. This selector does not imply exact current-status intersection unless the dashboard explicitly documents that semantics. |
| `bioetl-control-plane-v1` | `$pipeline` | Single + Include All | `$__all` | Core scope: pipeline option list from the local control-plane catalog (/ops/control-plane/filter-options?dimension=pipeline), not the Prometheus universe. PromQL current-state panels still match $pipeline against the shared universe metrics. Single-select unless this board documents All. Default selection is All pipelines until the operator narrows to a concrete pipeline. A pasted var-pipeline value that exists in the catalog remains selectable even when Prometheus has no series. |
| `bioetl-control-plane-v1` | `$run_type` | Multi + Include All | `backfill` | Core scope: run_type selector bounded by the active control-plane pipeline universe. Default All is intentional; missing run-type context must be represented as All, not unknown. Default run_type is backfill (SEL-P0 fallback); Include All remains available for aggregate diagnostics. |
| `bioetl-control-plane-v1` | `$run_id` | Single | `-` | Shared operator identity context sourced from the local control-plane run-manifest catalog. The selector defaults to - and affects only local HTTP identity panels; it MUST NOT be used in Prometheus labels or cross-dashboard handoffs. Run ID options are ordered by start time descending from the control-plane catalog; Grafana sort is disabled so backend order is preserved. |
| `bioetl-control-plane-v1` | `$read_latency_quantile` | Single | `0.95` | Select one control-plane global read-latency quantile. Default p95 keeps a single series per store/operation instead of overlaying p50/p95/p99. Track Global Read Latency shows last and max for the selected quantile. |
| `bioetl-control-plane-v1` | `$provider_for_pipeline` | Hidden | `` | Hidden selector: resolves the provider owning the selected pipeline so cross-dashboard handoffs can prefill $provider without operator input. |
| `bioetl-dq-v2` | `$workflow` | Single + Include All | `$__all` | Shared operator context: workflow evidence selector. This selector does not imply exact current-status intersection unless the dashboard explicitly documents that semantics. |
| `bioetl-dq-v2` | `$pipeline` | Single + Include All | `$__all` | Core scope: pipeline option list from the local control-plane catalog (/ops/control-plane/filter-options?dimension=pipeline), not the Prometheus universe. PromQL current-state panels still match $pipeline against the shared universe metrics. Single-select unless this board documents All. Default selection is All pipelines until the operator narrows to a concrete pipeline. A pasted var-pipeline value that exists in the catalog remains selectable even when Prometheus has no series. |
| `bioetl-dq-v2` | `$run_type` | Multi + Include All | `backfill` | Core scope: run_type selector bounded by pipeline; fallback: All run types for selected pipeline. Default run_type is backfill (SEL-P0 fallback); Include All remains available for aggregate diagnostics. |
| `bioetl-dq-v2` | `$run_id` | Single | `-` | Shared operator identity context sourced from the local control-plane run-manifest catalog. The selector defaults to - and affects only local HTTP identity panels; it MUST NOT be used in Prometheus labels or cross-dashboard handoffs. Run ID options are ordered by start time descending from the control-plane catalog; Grafana sort is disabled so backend order is preserved. |
| `bioetl-dq-v2` | `$stage` | Multi + Include All | `$__all` | Core scope: stage selector (only where stage-level analysis exists); fallback: All stages for selected pipeline/run_type. Default selection is All stages.  |
| `bioetl-dq-v2` | `$provider_for_pipeline` | Hidden | `` | Hidden selector: resolves the provider owning the selected pipeline so cross-dashboard handoffs can prefill $provider without operator input. |
| `bioetl-incident-v1` | `$workflow` | Single + Include All | `$__all` | Optional workflow evidence context and workflow-dashboard handoff selector. Overview remains pipeline-summary-first: workflow does not yet drive exact intersection filtering for the current-status PromQL surfaces. |
| `bioetl-incident-v1` | `$pipeline` | Single + Include All | `$__all` | Core scope: pipeline option list from the local control-plane catalog (/ops/control-plane/filter-options?dimension=pipeline), not the Prometheus universe. PromQL current-state panels still match $pipeline against the shared universe metrics. Single-select unless this board documents All. Default selection is All pipelines until the operator narrows to a concrete pipeline. A pasted var-pipeline value that exists in the catalog remains selectable even when Prometheus has no series. |
| `bioetl-incident-v1` | `$run_type` | Multi + Include All | `backfill` | Core scope: run_type selector bounded by pipeline; fallback: All run types for selected pipeline. Default run_type is backfill (SEL-P0 fallback); Include All remains available for aggregate diagnostics. |
| `bioetl-incident-v1` | `$run_id` | Single | `-` | Shared operator identity context sourced from the local control-plane run-manifest catalog. The selector defaults to - and affects only local HTTP identity panels; it MUST NOT be used in Prometheus labels or cross-dashboard handoffs. Run ID options are ordered by start time descending from the control-plane catalog; Grafana sort is disabled so backend order is preserved. |
| `bioetl-incident-v1` | `$provider` | Single | `unknown` | Provider scope: derived from Pipeline when set (first name segment, same heuristic as runtime $provider_hint), else from Workflow when set; fail-closed default is unknown when neither Pipeline nor Workflow is set. Operators may still open handoffs that pass an explicit provider value. |
| `bioetl-incident-v1` | `$read_latency_quantile` | Visible | `0.95` | Quantile for global read latency; p95 default. |
| `bioetl-incident-v1` | `$provider_for_pipeline` | Hidden | `` | Hidden selector: resolves the provider owning the selected pipeline so cross-dashboard handoffs can prefill $provider without operator input. |
| `bioetl-overview-v2` | `$workflow` | Single + Include All | `$__all` | Optional workflow evidence context and workflow-dashboard handoff selector. Overview remains pipeline-summary-first: workflow does not yet drive exact intersection filtering for the current-status PromQL surfaces. |
| `bioetl-overview-v2` | `$pipeline` | Single + Include All | `$__all` | Overview landing keeps Include All / default All so L0 fleet state renders. Option list comes from the control-plane catalog, not the Prometheus universe, so a concrete pipeline remains selectable when Prom is empty. |
| `bioetl-overview-v2` | `$run_type` | Multi + Include All | `$__all` | Core scope: run_type selector bounded by pipeline; fallback: All run types for selected pipeline. |
| `bioetl-overview-v2` | `$run_id` | Single | `-` | Run ID selector sourced from the local control-plane run-manifest catalog for the current pipeline/run_type scope. Grafana All values are normalized to an unbounded scope, so Run Type = All no longer empties the selector; Pipeline = All exposes aggregate exact-run handoff options from the catalog. This selector remains HTTP-backed and does not reintroduce run_id into Prometheus labels. Run ID options are ordered by start time descending from the control-plane catalog; Grafana sort is disabled so backend order is preserved. |
| `bioetl-overview-v2` | `$provider_for_pipeline` | Hidden | `` | Hidden selector: resolves the provider owning the selected pipeline so cross-dashboard handoffs can prefill $provider without operator input. |
| `bioetl-run-explorer-v1` | `$workflow` | Single + Include All | `$__all` | Browse scope from the local control-plane catalog. Default All includes every workflow. Filters the recent-launches table. |
| `bioetl-run-explorer-v1` | `$pipeline` | Single + Include All | `$__all` | Browse scope from the local control-plane catalog. Default All includes every pipeline. Explicit URL selections take precedence. Select a table row to inspect its exact pipeline and Run ID. |
| `bioetl-run-explorer-v1` | `$run_type` | Single + Include All | `$__all` | Browse scope from the local control-plane catalog. Default All includes every run type. Explicit URL selections take precedence. Select a table row to inspect its exact pipeline and Run ID. |
| `bioetl-run-explorer-v1` | `$run_id` | Single | `-` | Shared operator identity context sourced from the local control-plane run-manifest catalog. The selector defaults to - and affects only local HTTP identity panels; it MUST NOT be used in Prometheus labels or cross-dashboard handoffs. Run ID options are ordered by start time descending from the control-plane catalog; Grafana sort is disabled so backend order is preserved. |
| `bioetl-run-explorer-v1` | `$lookup_run_id` | Single | `` | Exact UUID within the current Workflow/Pipeline/Run Type, including launches older than the latest ten. Does not replace Selected Run until a matching row is found. Clear to browse recent launches. |
| `bioetl-run-explorer-v1` | `$provider_for_pipeline` | Hidden | `` | Hidden selector: provider for a concrete Pipeline. Unused when Pipeline is All ($__all / .*). Table Provider handoff uses the row field. |

## Retired boards (do not reintroduce)

| Retired UID | Replacement |
| --- | --- |
| `bioetl-runtime` | Incident Workspace fleet/workflow evidence |
| `bioetl-provider-health-v2` | Run Overview selected Provider Evidence; Incident current provider metrics |
| `bioetl-workflow-overview` | Incident workflow evidence |
| `bioetl-alerts-slo` | Incident alerts |
| `bioetl-silver-reject-explorer` | CLI quarantine inspect and saved DQ evidence |

Historical `$pipeline_context`, `$adapter`, `$provider_hint`, `$status`, `$step_status`, `$step_kind`, `$workflow_context`, `$pipeline_context_exact`, `$quarantine_run_id` and `$payload_hash` are not current operator selectors.

Related: [selector-architecture.md](selector-architecture.md), [navigation-contract.md](navigation-contract.md), [design-system.md](design-system.md).
