______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P1
  Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
  Last verified: '2026-10-15'

______________________________________________________________________

# Pipeline Failure: High DQ Rate (P1)

## Trigger

- Run this procedure for pipeline failures driven by data quality policy violations or invalid datasets.
- Escalate according to the priority declared in metadata when operator ownership is unclear.

## Impact

- Priority: P1.
- Delayed handling can extend service disruption, data correctness risk, or operator response time.

## Preconditions

- Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
- Required access: repository checkout, local shell, logs, configuration, and relevant data/control-plane artifacts.

## Procedure

### Symptoms

- Pipeline fails with `DataQualityThresholdError` / `DataQualityError`.
- Logs show hard-threshold failure or soft-threshold warning messages from transform/postrun stages.
- Quarantine volume spikes for one pipeline.
- Generated DQ report or metadata sidecar points to the affected run artifacts.

### Silver filter accounting warning

`BioETLSilverFilterRejectAccountingMismatch` compares cumulative filtered-out
records with the cumulative sum of the bounded rejection breakdown, scoped by
`pipeline` and `run_type`. The rule compares both aggregate snapshots at each
evaluation and retains the latest comparison in the 15-minute window. Equal
totals before a reset cannot mask unequal totals after it.

A nonzero counter after an idle run is not a new rejection. Do not compare its
cumulative value with `increase(...[15m])`: an idle but balanced run would warn.
For triage, compare `bioetl_silver_filter_rejects_stage_total_15m` with
`bioetl_silver_filter_rejections_breakdown_total_15m`, then inspect the raw counters
and saved run report. A missing positive counterpart or unequal totals still
raises the warning after five minutes. Both sides absent remain absent, not a
measured zero. Do not delete Pushgateway groups or edit run reports to clear it.

The Incident Workspace CURRENT `silver_filter_rejects` reason uses a recent
positive snapshot with matching Pushgateway publication time, or a counter
increase in the 15-minute window. A new publication can carry the same count
as the previous run. The CURRENT `gold_contract_exclusions` reason applies the
same test to `bioetl_stage_records_total{stage="gold",outcome="excluded_by_contract"}`.
A retained snapshot stops qualifying when its publication expires. Saved-run
Data Quality retains the original rejection and exclusion counts and verdicts.

### Empty event observations in Incident Workspace

`NO OBSERVATIONS` is not a measured zero or a healthy verdict. Labelled event
families (errors, checkpoint, replay, audit and shutdown operations) are lazy:
before a matching observation they expose metadata but no sample. The live panel
auditor accepts this state only for explicit event-panel contracts, with all
BioETL, Pushgateway and Prometheus targets up, an observed pipeline/run-type scope,
and counter/histogram metadata for every referenced event family. Missing sources,
undeclared metrics, unknown scopes and response annotations remain unaccepted.

Empty filtered signal tables additionally require their recording rules and
independent input evidence. Workflow-only panels may be empty for a verified
standalone scope when Workflow is All; selecting a concrete workflow does not get
this exemption. Standalone membership is keyed by both pipeline and run type.
Provider identity is projected from a unique observed pipeline/provider mapping
across run types; conflicting mappings remain UNKNOWN. Saved run verdicts,
including provider WARN, are not rewritten by these CURRENT projections.

### Thresholds

- **Soft Fail**: > 5% errors (Warning).
- **Hard Fail**: > 50% errors (Pipeline Failure) for hierarchical / contract-loader
  defaults; > 20% only for Silver request / pipeline-override baselines when those
  code defaults apply without an explicit override.

**Note:** DQ thresholds are multi-surface (see
[DQ Contracts — Threshold Semantics](../../04-reference/contracts/dq-contracts.md#threshold-semantics)):
- Hierarchical (`configs/base/quality.yaml` / `ThresholdsConfig`): `soft_fail: 0.05`, `hard_fail: 0.50`
- Contract-backed loader omitted thresholds: `hard_fail: 0.50`
- Silver request / pipeline-override baseline: `hard_fail: 0.20`

Hierarchical configuration takes precedence when the entity `quality:` hierarchy
is the active surface.

### Diagnosis Steps

1. **Inspect Quarantine**:
   ```bash
   bioetl quarantine inspect --pipeline <pipeline-name> --limit 20
   ```
1. **Analyze Error Types**:
   - `SCHEMA-VIOLATION`: Source data doesn't match expected schema.
   - `MISSING-REQUIRED-FIELD`: Mandatory field is null/missing.
   - `INVALID-FORMAT`: Date/Number format is incorrect.

### Recovery Actions

1. **If Source Data is Bad**:
   - Contact data provider.
   - Wait for provider to fix data.
1. **If Schema is Outdated**:
   - Update source-aligned contract/schema code in `src/bioetl/domain/contracts/gold/` or related validation/config modules.
   - Update Pandera-based validation surfaces used by the pipeline.
   - Deploy new version.
1. **If evidence indicates the governed threshold is wrong**:
   - Do not raise a threshold to make the failed run green.
   - Preserve the failed run, DQ report, quarantine distribution, effective
     config, and contract version.
   - Treat the threshold-change evidence gate in
     `docs/04-reference/contracts/dq-contracts.md` as **mandatory** (not
     optional guidance). The proposal MUST include:
     - before/after disposition impact evidence (counts and affected pipelines);
     - an explicit rollback condition if the new threshold is wrong in production.
   - Open a separate policy change with the affected pipelines, historical
     baseline, before/after disposition counts, and contract-owner approval.
   - Validate the proposed value against persisted inputs and perform a
     deterministic replay. The original failed run remains immutable evidence.

### Quarantine Management

- **Replay**: After fixing the parser/schema, replay quarantined records:
  ```bash
  bioetl quarantine replay --pipeline <pipeline-name>
  ```
- **Purge**: If data is garbage, purge quarantine:
  ```bash
  bioetl quarantine purge --pipeline <pipeline-name> --older-than-days 30
  ```

## Compliance

- This runbook MUST be executed within the priority and runtime profile declared in the YAML header.
- Operators SHOULD preserve evidence, commands, and follow-up actions in the Verification and Post-incident sections.

## Failed-run counter coverage

The health-server exporter declares the failed-run counter for each durable
pipeline/run-type scope during rehydration, using a zero increment. This begins
observation in the current registry; it neither replays historical failures nor
resets an existing counter. The failed-run panel still requires at least two
real scraped samples per selected scope. Until those samples exist it remains
UNKNOWN. Historical run reports retain their original outcome.

## Verification

- Confirm the triggering condition is cleared or understood with evidence.
- Verify logs, manifests, datasets, or alerts reflect the expected post-procedure state.

## Rollback

- Revert partial changes made during mitigation, including config overrides, restored checkpoints, or rewritten data, if they worsen the situation.
- Return to the last known good state before attempting an alternate recovery path.

## Post-incident

- Record timeline, commands executed, evidence reviewed, and follow-up owners.
- Update related alerts, dashboards, or runbooks when operator gaps or ambiguous steps are discovered.
