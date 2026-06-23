______________________________________________________________________

Version: 1.0.0
Status: template
Class: internal
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# Provider Specification: <Provider> <Entity>

**Pipeline ID:** `<provider_entity>`
**Provider:** `<provider>`
**Entity:** `<entity>`
**Source config:** `configs/entities/<provider>/<entity>.yaml`

## Identification

| Parameter          | Value                                                                        |
| ------------------ | ---------------------------------------------------------------------------- |
| Provider           | `<provider>`                                                                 |
| Entity             | `<entity>`                                                                   |
| Endpoint / source  | `<url-or-source>`                                                            |
| Auth mode          | \`\<public                                                                   |
| Rate limit         | `<configured limit>`                                                         |
| Canonical contract | `docs/04-reference/contracts/gold/<provider>_<entity>_v<major>.<minor>.json` |

## Source Contract

- Source-system identifiers MUST be listed.
- Pagination, filtering, and incremental strategy SHOULD be stated explicitly.
- Authentication and quota assumptions MUST be stated if access is not anonymous.

## Extraction Rules

- Request parameters MUST be reproducible from config or CLI inputs.
- Retry, timeout, and backoff behavior SHOULD reference provider config.
- Unsupported provider features MAY be listed only if clearly marked non-runtime.

## Transformation Rules

- Canonical naming MUST use `snake_case`.
- Type coercion, normalization, and deduplication rules MUST be explicit.
- Legacy aliases SHOULD be marked historical or compatibility-only.

## Load Behavior

| Layer  | Format         | Mode        | Key / path |
| ------ | -------------- | ----------- | ---------- |
| Bronze | `<jsonl+zstd>` | `<append>`  | `<path>`   |
| Silver | `<delta>`      | \`\<append  | merge>\`   |
| Gold   | \`\<delta      | disabled>\` | `<mode>`   |

## Data Quality

- Required fields MUST be identified.
- Hard-fail versus quarantine policy MUST be explicit.
- DQ rules SHOULD reference config sections or rule bundles.

## Failure Modes

- List provider-specific failure conditions that MUST trigger escalation.
- List recoverable conditions that SHOULD allow retry or resume.

## Compliance

| Control  | Requirement                                        | Status   | Evidence |
| -------- | -------------------------------------------------- | -------- | -------- |
| Metadata | YAML header MUST be complete                       | \`\<pass | fail>\`  |
| Config   | Spec MUST link active entity/provider config       | \`\<pass | fail>\`  |
| Contract | Spec MUST link canonical contract export           | \`\<pass | fail>\`  |
| Runtime  | Spec MUST align with ADR-010 local-only posture    | \`\<pass | fail     |
| Naming   | Canonical fields MUST follow project naming policy | \`\<pass | fail>\`  |

## References

- `configs/entities/<provider>/<entity>.yaml`
- `configs/providers/<provider>.yaml`
- `docs/04-reference/contracts/gold/<provider>_<entity>_v<major>.<minor>.json`
- `<related ADR or runbook>`
