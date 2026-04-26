______________________________________________________________________

Version: 1.0.0
Status: template
Class: internal
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: \<P0|P1|P2|P3|Informational>
  Runtime profile: \<Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.>
  Last verified: '2026-03-30'

______________________________________________________________________

# <Runbook Title>

## Trigger

- State exactly when this runbook MUST be used.
- State the alert, symptom, or maintenance condition that SHOULD route the operator here.

## Impact

- State the expected severity and operational risk.
- State what data, runtime surface, or user outcome MAY be degraded.

## Preconditions

- Required access MUST be listed.
- Required tools, commands, and repository paths MUST be listed.
- Preconditions SHOULD include safety checks before any write or delete action.

## Procedure

### 1. Triage

1. `<command or inspection step>`
1. `<decision point>`

### 2. Mitigation

1. `<safe mitigation step>`
1. `<safe mitigation step>`

### 3. Recovery

1. `<restore / resume / rebuild step>`
1. `<post-recovery validation step>`

## Verification

- List the logs, metrics, manifests, tables, or files that MUST confirm success.
- Include exact commands when verification SHOULD be reproducible by another operator.

## Rollback

- Rollback trigger MUST be explicit.
- Rollback steps MUST revert partial changes when mitigation makes the incident worse.
- Any destructive rollback SHOULD require a backup, snapshot, or prior-state reference.

## Post-incident

- Record timeline, commands, evidence, and owner.
- Capture follow-up work items that SHOULD update alerts, tests, or docs.

## Compliance

| Control      | Requirement                                            | Status   | Evidence |
| ------------ | ------------------------------------------------------ | -------- | -------- |
| Sections     | All mandatory runbook sections MUST exist              | \`\<pass | fail>\`  |
| Runtime      | Runtime profile MUST match ADR-010 posture             | \`\<pass | fail     |
| Safety       | Destructive actions MUST include guardrails or backups | \`\<pass | fail     |
| Verification | Success criteria MUST be executable                    | \`\<pass | fail>\`  |
| Ownership    | Escalation or owner path SHOULD be explicit            | \`\<pass | fail     |

## References

- `<related ADR>`
- `<related config>`
- `<related pipeline / contract / dashboard>`
