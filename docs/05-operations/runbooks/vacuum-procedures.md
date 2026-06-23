______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P2
  Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
  Last verified: '2026-04-03'

______________________________________________________________________

# VACUUM Procedures Runbook

## Trigger

- Run this procedure when Delta maintenance requires manual VACUUM execution or
  explicit validation of retention behavior.
- Escalate according to the priority declared in metadata when operator
  ownership is unclear.

## Impact

- Priority: P2.
- Delayed handling can extend storage growth, retention-policy drift, or
  operator response time.

## Preconditions

- Runtime profile: Local-Only single-instance (ADR-010), local filesystem
  storage, MemoryLock.
- Required access: repository checkout, local shell, logs, configuration, and
  relevant data/control-plane artifacts.
- No active pipeline run should be mutating the target tables.

## Procedure

### 1. Use the guide for policy, use this page for actions

- Policy, retention defaults, and scheduled maintenance guidance live in
  [VACUUM & Retention](../vacuum-retention.md).
- This runbook is the operator action path for manual execution.

### 2. Confirm the target and retention window

Decide whether you are vacuuming:

- one table
- all Silver tables
- all Gold tables

Use the retention value from the guide unless an incident or forensic need
requires an override.

### 3. Start with a dry run

Single table:

```bash
bioetl maintenance vacuum <provider>.<entity> --dry-run
```

Layer-wide:

```bash
bioetl maintenance vacuum-all --layer silver --dry-run
bioetl maintenance vacuum-all --layer gold --dry-run
```

Review what would be removed before executing the real operation.

### 4. Execute manual VACUUM

Single table:

```bash
bioetl maintenance vacuum <provider>.<entity>
bioetl maintenance vacuum <provider>.<entity> --retention-days 30
```

All tables:

```bash
bioetl maintenance vacuum-all
bioetl maintenance vacuum-all --layer silver
bioetl maintenance vacuum-all --layer gold
```

### 5. Enable run-triggered VACUUM only when intentional

Pipeline-integrated VACUUM is supported but disabled by default. For a single
run, enable it explicitly:

```bash
bioetl run --pipeline <pipeline-name> --vacuum-after-run --vacuum-retention-days 7
```

For persistent enablement, use the YAML/runtime policy documented in
[VACUUM & Retention](../vacuum-retention.md).

### 6. Validate the result

After execution, verify:

- the command completed without storage errors
- expected files were removed
- no active investigation still depends on older time-travel versions
- logs contain the expected `vacuum_completed` or corresponding failure signal

### 7. Troubleshooting shortcuts

If VACUUM does not behave as expected:

- files not removed: retention window has not elapsed yet
- storage not freed: verify the command actually completed and targeted the
  intended table/layer
- operation too slow: split by layer or run during a quieter maintenance window

Use [VACUUM & Retention](../vacuum-retention.md) for the full retention
strategy and scheduling guidance.

## Compliance

- This runbook MUST be executed within the priority and runtime profile
  declared in the YAML header.
- Operators SHOULD preserve evidence, commands, and follow-up actions in the
  Verification and Post-incident sections.

## Verification

- Confirm the chosen table/layer and retention values were the intended ones.
- Verify logs, manifests, datasets, or alerts reflect the expected
  post-procedure state.

## Rollback

- Do not immediately rerun with a lower retention window unless the operator
  intent is explicit and documented.
- If the wrong table/layer was targeted, stop and escalate rather than broadening
  the cleanup action.

## Post-incident

- Record timeline, commands executed, evidence reviewed, and follow-up owners.
- Update retention policy or scheduling docs if repeated manual VACUUM work is
  becoming the norm.
