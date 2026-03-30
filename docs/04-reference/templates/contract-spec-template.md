---
Version: 1.0.0
Status: template
Class: internal
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-30'
---

# Contract Specification: <Provider> <Entity> v<major>.<minor>

**Contract ID:** `<provider>_<entity>_v<major>.<minor>`  
**Layer:** `<gold|control-plane|other>`  
**Source of truth:** `<code path>`  
**Published export:** `docs/04-reference/contracts/<subdir>/<provider>_<entity>_v<major>.<minor>.<ext>`

## Identity

| Parameter | Value |
|---|---|
| Provider | `<provider>` |
| Entity | `<entity>` |
| Version | `<major>.<minor>` |
| Status | `<draft|active|deprecated|superseded>` |
| Compatibility | `<backward-compatible|breaking>` |

## Scope

- State what this contract MUST guarantee.
- State what consumers MUST NOT assume.
- State which producer surfaces MUST emit this contract.

## Versioning Policy

- Contract versions MUST follow `major.minor` semantics per ADR-036.
- Breaking changes MUST increment `major`.
- Backward-compatible additions SHOULD increment `minor`.
- Documentation-only edits MAY keep the same contract version if the export is unchanged.

## Schema Summary

| Field | Type | Nullable | Required | Description |
|---|---|---|---|---|
| `<field_name>` | `<type>` | `<true|false>` | `<true|false>` | `<meaning>` |
| `<field_name>` | `<type>` | `<true|false>` | `<true|false>` | `<meaning>` |

## Constraints

- Primary keys MUST be explicit.
- Enum domains, ranges, and pattern constraints SHOULD be listed.
- Field semantics MUST remain stable within the same `major` version.

## Producer Obligations

- Producers MUST validate against the canonical schema before publication when strict validation applies.
- Producers SHOULD emit lineage or version metadata needed for downstream traceability.

## Consumer Obligations

- Consumers MUST pin or validate the contract version they depend on.
- Consumers SHOULD treat undocumented fields as non-contractual.

## Change Management

- Breaking changes MUST link to an ADR and migration plan.
- Dual-service or compatibility windows SHOULD be documented when required.
- Rollback criteria MUST be stated for breaking migrations.

## Validation

- State the automated checks that MUST pass.
- Link parity checks, generated export checks, and schema validation commands as applicable.

## Compliance

| Control | Requirement | Status | Evidence |
|---|---|---|---|
| Versioning | Version MUST follow ADR-036 `major.minor` policy | `<pass|fail>` | `<version field>` |
| Source of truth | Code and published export MUST identify the canonical source | `<pass|fail>` | `<paths>` |
| Validation | Validation and parity checks MUST be listed | `<pass|fail>` | `<check refs>` |
| Traceability | Breaking changes SHOULD link ADR + migration evidence | `<pass|fail|n/a>` | `<ADR / changelog>` |
| Consumers | Consumer assumptions MUST be bounded explicitly | `<pass|fail>` | `<scope / obligations>` |

## References

- `docs/02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md`
- `<code path>`
- `<generated export path>`
- `<related provider or pipeline spec>`
