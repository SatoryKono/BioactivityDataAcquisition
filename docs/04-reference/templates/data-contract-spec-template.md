______________________________________________________________________

Version: 1.1.0
Status: template
Class: internal
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-01'

______________________________________________________________________

# Data Contract Specification: <Provider> <Entity> v<major>.<minor>

**Template type:** `data-contract-spec`
**Contract ID:** `<provider>_<entity>_v<major>.<minor>`
**Source of truth:** `<code path>`
**Published export:** `docs/04-reference/contracts/<subdir>/<provider>_<entity>_v<major>.<minor>.<ext>`
**Schema dialect:** `<JSON Schema Draft-07|other>`

## Purpose

- State what this contract MUST guarantee.
- State which producer surface emits it.
- State what downstream consumers MUST NOT assume.

## Identity

| Parameter     | Value                     |
| ------------- | ------------------------- |
| Provider      | `<provider>`              |
| Entity        | `<entity>`                |
| Version       | `<major>.<minor>.<patch>` |
| Status        | \`\<draft                 |
| Compatibility | \`\<backward-compatible   |

## Source Of Truth And Publication

| Artifact              | Path                                                                              |
| --------------------- | --------------------------------------------------------------------------------- |
| Domain / code source  | `<code path>`                                                                     |
| Published contract    | `docs/04-reference/contracts/<subdir>/<provider>_<entity>_v<major>.<minor>.<ext>` |
| Related provider spec | `docs/04-reference/providers/<provider>/<entity>.md`                              |
| Related pipeline spec | `docs/04-reference/pipelines/<provider>/<spec>.md`                                |

## Backward Compatibility

- MAJOR changes MUST be reserved for breaking schema or semantic changes.
- MINOR changes SHOULD be used for backward-compatible additions.
- PATCH changes MAY be used for metadata-only or documentation-only corrections.
- Breaking changes MUST link to an ADR and migration guidance.

## Field Semantics

| Field          | Type     | Nullable | Required | Description |
| -------------- | -------- | -------- | -------- | ----------- |
| `<field_name>` | `<type>` | \`\<true | false>\` | \`\<true    |
| `<field_name>` | `<type>` | \`\<true | false>\` | \`\<true    |

## Constraints

- Business primary keys MUST be explicit.
- Enum domains, ranges, patterns, and nullability MUST be listed when contractual.
- Field semantics MUST remain stable within the same major version.

## Producer Obligations

- Producers MUST validate against the canonical schema when strict validation applies.
- Producers SHOULD emit lineage or version metadata needed for traceability.
- Producers MUST keep the published export synchronized with the source of truth.

## Consumer Obligations

- Consumers MUST pin or validate the contract version they depend on.
- Consumers SHOULD treat undocumented fields as non-contractual.
- Consumers MUST NOT infer guarantees not listed in this contract.

## Validation

- List the automated checks that MUST pass.
- Link parity checks, generated export checks, and schema validation commands as applicable.

## Compliance

| Control         | Requirement                                                  | Status   | Evidence |
| --------------- | ------------------------------------------------------------ | -------- | -------- |
| Versioning      | Version MUST follow the project contract versioning policy   | \`\<pass | fail>\`  |
| Source of truth | Code and published export MUST identify the canonical source | \`\<pass | fail>\`  |
| Validation      | Validation and parity checks MUST be listed                  | \`\<pass | fail>\`  |
| Traceability    | Breaking changes SHOULD link ADR + migration evidence        | \`\<pass | fail     |
| Consumer bounds | Consumer assumptions MUST be bounded explicitly              | \`\<pass | fail>\`  |

## References

- `<related ADR>`
- `<code path>`
- `<published export path>`
- `<related provider or pipeline spec>`
