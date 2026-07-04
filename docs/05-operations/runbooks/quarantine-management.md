______________________________________________________________________

Version: 1.2.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P2
  Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
  Last verified: '2026-04-05'

______________________________________________________________________

# Quarantine Management

## Trigger

- Run this procedure when records enter quarantine and require review, disposition, or release.
- Escalate according to the priority declared in metadata when operator ownership is unclear.

## Impact

- Priority: P2.
- Delayed handling can extend service disruption, data correctness risk, or operator response time.

## Preconditions

- Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
- Required access: repository checkout, local shell, logs, configuration, and relevant data/control-plane artifacts.

## Procedure

### Overview

- Records that fail Data Quality (DQ) checks are sent to the Quarantine table (`common.quarantine`) instead of crashing the pipeline.
- Silver structural rejects also land in `common.quarantine` with legacy
  `error_code=FILTERED_OUT_SILVER`, `classification=filter_rejection`, and
  `quarantine_category=silver_filter`. Gold contract/semantic rejects are
  separate operator surfaces in `4. Data Quality` Gold panels and
  processed-records views; do not interpret `FILTERED_OUT_SILVER` as a Gold
  semantic reject code.

### Routine Tasks (Weekly)

### 1. Inspect Quarantine

- Review new errors to identify systemic issues.

```bash
bioetl quarantine inspect --pipeline {pipeline-name} --limit 50
```

- For Silver structural triage, prefer the explicit non-legacy error-code path:

```bash
bioetl quarantine stats --pipeline {pipeline-name} --error-code FILTERED_OUT_SILVER
bioetl quarantine stats --pipeline {pipeline-name} --error-code FILTERED_OUT_SILVER --group-by reason-code-field
bioetl quarantine inspect --pipeline {pipeline-name} --error-code FILTERED_OUT_SILVER --limit 20
```

- If you are investigating one concrete run and need a trustworthy Bronze denominator,
  use run-scoped mode:

```bash
bioetl quarantine stats --pipeline {pipeline-name} --error-code FILTERED_OUT_SILVER --run-id {run-id}
bioetl quarantine inspect --pipeline {pipeline-name} --error-code FILTERED_OUT_SILVER --run-id {run-id} --limit 20
```

- `--silver-filter-only` remains as a deprecated compatibility alias until
  2026-09-30. New runbooks and operator examples should use
  `--error-code FILTERED_OUT_SILVER` so the Silver structural reject scope is
  explicit:

  - total Silver rejects;
  - top `reason_code`;
  - top rejected `field`;
  - `rule_type` / `operator` distribution.

- `stats --error-code FILTERED_OUT_SILVER --run-id ...` additionally shows
  `Silver Rejects vs Bronze` when the control-plane ledger contains
  `records_bronze` for that run. The ratio is intentionally omitted outside
  run-scoped mode to avoid misleading cross-run denominators.

- Historical quarantine rows written before `run_id` propagation may not be
  discoverable via `--run-id`. Run-scoped triage is most reliable for new runs
  written after the provenance update.

- Если нужен один операторский pivot без визуального шума, используйте:

  - `--group-by reason-code`
  - `--group-by field`
  - `--group-by rule-type`
  - `--group-by operator`
  - `--group-by reason-code-field`
  - `--group-by reason-signature`

- `reason-signature` — это stable analytical key вида
  `reason_code | rule_type | field | operator`.
  Human-readable `Reason` / `message` остаётся display-only текстом и не должен
  использоваться как aggregation key.

- `inspect --error-code FILTERED_OUT_SILVER` is the right drilldown when you
  need the exact Silver structural reason for one record. The CLI renders `Reason`,
  `reason_code`, `rule_type`, `field`, `operator`, `expected`, `actual`, and
  the original payload. For Gold contract/semantic rejects, start from the
  `4. Data Quality` Gold reject panel/processed-records surfaces.

### 2. Triage Errors

- **Systemic Error**: Bug in parser or schema. -> **Fix Code**.
- **Data Error**: Source data is bad. -> **Contact Provider** or **Ignore**.
- **Transient Error**: Network glitch during validation. -> **Replay**.

### 3. Replay Records

- After fixing a bug, replay quarantined records.

```bash
bioetl quarantine replay --pipeline {pipeline-name}
```

- *Note: Replay targets records with `dq_status='NEW'` and marks processed records as `REPROCESSED`.*

### 4. Purge Garbage

- Remove records that cannot be recovered.

```bash
bioetl quarantine purge --pipeline {pipeline-name}
```

- *Note: Purge deletes old records from the Delta quarantine table.*

### Metrics

- `dq-records-quarantined-total`: Total records sent to quarantine.
- `dq-quarantine-size-bytes`: Storage size of quarantine table.

### Grafana

- Use Grafana first for summary/trend investigation:
  - `bioetl-overview-v2`: high-level `filtered_out` volume.
  - `bioetl-runtime`: runtime triage and warning correlation.
  - `bioetl-dq-v2`: DQ/quarantine summary for selected `$pipeline` and `$run_type`,
    включая bounded panels `Top Silver Reject Reasons` и `Top Silver Reject Fields`.
  - `bioetl-silver-reject-explorer`: record-level browsing с фильтрами
    `$pipeline/$run_type/$reason_code/$field/$run_id` и detail по `payload_hash`.
- CLI/quarantine остаётся action surface для `resolve/replay/purge`.

### Silver Structural Rejects Triage Sequence

1. Open `1. Overview` or `2. Runtime` and confirm that `Silver Filter Rejects`
   is actually spiking in the active Grafana time window. This is the Silver
   structural `FILTERED_OUT_SILVER` legacy-alias path, not Gold
   contract/semantic rejection.
1. Pivot to `4. Data Quality` and inspect `Top Silver Reject Reasons` plus
   `Top Silver Reject Fields` to reduce the issue to a bounded cause summary.
1. Open `Silver Reject Explorer` for exact record-level evidence and selected-record context.
1. Run `bioetl quarantine inspect ... --error-code FILTERED_OUT_SILVER` /
   `bioetl quarantine resolve ...` when you need operator action in CLI.
1. For Gold contract/semantic rejects, stay in `4. Data Quality` and inspect
   `Inspect: Gold Reject Outcomes by Pipeline` plus processed-records surfaces.

### Retention

- Quarantine data is retained for **30 days** by default. Cleanup is executed via explicit purge operations (`bioetl quarantine purge`).

## Compliance

- This runbook MUST be executed within the priority and runtime profile declared in the YAML header.
- Operators SHOULD preserve evidence, commands, and follow-up actions in the Verification and Post-incident sections.

## Verification

- Confirm the triggering condition is cleared or understood with evidence.
- Verify logs, manifests, datasets, or alerts reflect the expected post-procedure state.

## Rollback

- Revert partial changes made during mitigation, including config overrides, restored checkpoints, or rewritten data, if they worsen the situation.
- Return to the last known good state before attempting an alternate recovery path.

## Post-incident

- Record timeline, commands executed, evidence reviewed, and follow-up owners.
- Update related alerts, dashboards, or runbooks when operator gaps or ambiguous steps are discovered.
