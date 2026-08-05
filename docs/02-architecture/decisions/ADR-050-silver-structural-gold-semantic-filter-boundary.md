______________________________________________________________________

Version: 1.1.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-06-18'

______________________________________________________________________

# ADR-050: Silver Structural and Gold Semantic Filter Boundary

**Date:** 2026-06-15
**Amended:** 2026-06-18
**Status:** Accepted
**Decision makers:** @BioETL-Team
**Related:** ADR-002, ADR-014, ADR-017, ADR-018, ADR-028, ADR-042, ADR-044, ADR-045, ADR-046, ADR-047
**Amends:** ADR-028 (Filter Rules Externalization)
**Source issues:** [#5112](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5112),
[#5116](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5116),
[#5117](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5117),
[#5118](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5118),
[#5119](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5119),
[#5114](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5114),
[#5115](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5115),
[#5120](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5120)

## Context (ADR-002, ADR-018, ADR-028)

ADR-002 defines the Medallion split: Silver is normalized, cleaned data that can
feed multiple Gold outputs, while Gold is the business-facing layer. ADR-018
requires strict Gold validation for downstream guarantees. ADR-028 externalized
filter rules into the unified configuration hierarchy, but historical
`silver_filters` and `gold_filters` shared semantic operator shapes such as
`columns`, `ranges`, `list_lengths`, and `list_contains`.

That overlap left the boundary ambiguous. Historical entity configs carried
legacy semantic rules under `filters.silver_filters`, and earlier migration
designs kept a compatibility-window narrative around boundary normalization.
Current production infrastructure no longer accepts those semantic keys at the
config boundary: active YAML is structural-only at Silver, and semantic Silver
payloads fail closed before domain conversion.

The retired working draft
`docs/99-archive/filters/retired-silver-filters-structural-scope.md` captured the original
rationale, but it is not an accepted ADR and must not be cited as ADR-048.
Accepted ADR-048 covers the domain schema boundary and Pandera runtime
compatibility.

## Decision (ADR-002, ADR-018, ADR-028, ADR-045)

Silver owns structural validity only. Canonical `silver_filters` may express
only structural admission rules:

- `required_fields`
- `exclude_if_present`

Gold owns semantic and business eligibility. Canonical `gold_filters` own rules
that decide whether a structurally valid Silver record belongs in a Gold output:

- `required_fields` when the field is business-critical for the Gold dataset
- `columns`
- `ranges`
- `list_lengths`
- `list_contains`
- `exclude_if_present` when the exclusion is a Gold/business rule

This decision amends ADR-028 by narrowing the meaning of Silver filters without
removing the hierarchical filter configuration model.

## Source-Profile Policy (ADR-014, ADR-028, ADR-044)

`extraction_params` are source-profile policy, not Silver filters. They narrow
provider API requests during Bronze extraction and remain separate from Silver
structural admission and Gold semantic eligibility.

Any change that widens or narrows `extraction_params` is a source-profile change
and must be reviewed separately from the Silver-to-Gold semantic filter
migration. When source-profile behavior changes, execution identity and replay
surfaces must stay deterministic under ADR-014 and ADR-044. Curated source
profiles are versioned under `filters.source_profile` with an
extraction-parameter SHA-256; the metadata is part of the validated effective
configuration rather than a separate runtime identity field.

## Compatibility Identity And Historical Alias (ADR-014, ADR-044, ADR-046, ADR-047)

Current production behavior is fail-closed at the configuration boundary:
infrastructure rejects semantic keys under `filters.silver_filters` before
strict validation and before domain conversion.

The accepted runtime mode remains `structural_only_compat`, and the old
`structural_only_auto_promote` value remains only a historical persisted
identity alias:

1. Domain Silver filter runtime evaluation uses only structural rules.
1. Effective config, run manifest, execution fingerprint, and checkpoint
   compatibility payloads record the canonical compatibility mode for
   deterministic replay and historical continuity.
1. Direct-construction test doubles, historical parity tooling, or persisted
   historical artifacts may still reference compatibility helpers, but
   production config/file loaders do not accept semantic Silver payloads.
1. New semantic Silver rules under `filters.silver_filters` are governance
   violations.

The remaining cleanup scope is therefore identity, observability wording, and
historical alias retirement rather than config-boundary acceptance.

## Reject Taxonomy And Operator Surfaces (ADR-017, ADR-018, ADR-045)

`FILTERED_OUT_SILVER`, `silver_filter_rejects`, Silver reject dashboards, and
CLI shortcuts such as `--silver-filter-only` are temporary compatibility aliases
for structural Silver rejects. They are not the target taxonomy for semantic or
business rejection.

Target taxonomy must distinguish:

- Silver structural rejects: records that cannot safely enter Silver.
- Gold semantic rejects: structurally valid records that fail Gold
  business/eligibility criteria.
- Gold contract rejects: records that fail Gold strict validation or DQ
  contract enforcement.

Gold reject reason codes are canonicalized by family:

- `gold_contract_schema_failure`: strict Gold schema/type/unknown-column
  validation failure.
- `gold_contract_required_failure`: missing or null required Gold contract
  field.
- `gold_contract_reference_failure`: Gold referential integrity failure.
- `gold_semantic_business_exclusion`: Gold business eligibility exclusion.
- `gold_semantic_profile_exclusion`: source-profile or profile-governed Gold
  eligibility exclusion.

Every Gold reject payload MUST carry `contract_version` and stable rule identity
(`rule_id`). Silver records MUST NOT receive `gold_candidate_*` fields or
analysis-readiness flags; Gold eligibility is enforced only at Gold/DQ/debug
export surfaces.

Operator-facing text may retain legacy names only while it clearly describes the
narrowed structural meaning and has a cleanup path.

## Remaining Cleanup Criteria (ADR-028, ADR-042, ADR-044, ADR-047)

The semantic-YAML cleanup is complete for active entity configs. Remaining
follow-up work can close only after all criteria below are met:

1. Current inventory includes config, runtime, source-profile, and observability
   surfaces for the Silver/Gold filter boundary.
1. Active entity configs continue to carry no semantic keys under
   `filters.silver_filters`, or any temporary exception is explicitly reviewed.
1. Historical parity tooling preserves evidence that the removed semantic Silver
   rules and canonical Gold semantic rules produce equivalent Gold eligibility
   decisions for representative entities.
1. Run manifest, checkpoint, and effective-config identity surfaces preserve the
   canonical compatibility mode and historical alias handling.
1. Observability and CLI wording no longer imply that semantic/business rejects
   are Silver rejects.
1. CI guardrails continue to fail new semantic keys under
   `filters.silver_filters`.

After this cleanup, the historical alias may be retired from identity surfaces
when a separate compatibility decision approves that removal.

## Consequences (ADR-002, ADR-018, ADR-028, ADR-045)

### Positive

- The Medallion boundary is explicit: Silver structural quality is separate from
  Gold semantic/business eligibility.
- The production config boundary is unambiguous: semantic Silver keys fail
  closed before validation and domain conversion.
- Remaining compatibility concerns have a bounded cleanup path focused on
  identity and wording rather than active YAML acceptance.
- `extraction_params` remain source-profile policy instead of being folded into
  Silver filtering semantics.
- Operator-facing reject categories can be cleaned up without changing Gold
  strict validation or DQ contract ownership.

### Negative

- Metrics, dashboards, and CLI wording still need follow-up work because
  historical names imply broader Silver reject semantics.
- Historical alias handling keeps temporary complexity in config identity,
  replay, and migration verification surfaces even though production config
  boundaries already fail closed.

### Neutral

- ADR-028 still owns hierarchical filter externalization and merge mechanics.
- ADR-018 and ADR-045 continue to govern Gold strict validation and DQ contract
  enforcement.
- No technical-debt budgets or limits are increased by this decision.

## Alternatives Considered (ADR-002, ADR-018, ADR-028)

### Keep semantic rules in Silver

Rejected. It leaves business eligibility in the normalized data layer and keeps
the ambiguity that caused duplicate `silver_filters` and `gold_filters`.

### Treat `extraction_params` as Silver filters

Rejected. `extraction_params` shape provider API requests at Bronze extraction
time and are source-profile policy. Silver filters operate after extraction on
records admitted into the normalized layer.

### Remove Silver filters entirely

Rejected. Silver still needs structural admission checks and the existing
`required_fields` optionality surface.

### Use the retired ADR-048 draft

Rejected. Accepted ADR-048 is the domain schema boundary and runtime Pandera
compatibility decision. The local Silver-filter ADR-048 file remains historical
context only.

## Verification (ADR-028, ADR-042, ADR-044)

Implementation and follow-up work must verify:

- `docs/filters/README.md` and `docs/99-archive/filters/migration-plan.md` cite this ADR
  as the normative decision and treat the local ADR-048 filter draft as
  historical context only.
- Targeted search finds no stale references that cite the retired ADR-048 draft
  as accepted Silver-filter governance.
- Active entity YAML does not carry semantic buckets under
  `filters.silver_filters`, and production loaders reject semantic Silver keys
  at file/pipeline boundaries before domain conversion.
- Non-empty `extraction_params` carry matching `filters.source_profile`
  baseline metadata.
- The compatibility-surface guardrail includes this ADR.
- Documentation link checks pass or report pre-existing unrelated failures.

## References

- [ADR-002: Medallion Architecture](ADR-002-medallion-architecture.md)
- [ADR-014: Deterministic Writes and Retries](ADR-014-deterministic-writes.md)
- [ADR-017: Observability Architecture](ADR-017-observability-architecture.md)
- [ADR-018: Gold Strict Validation](ADR-018-gold-strict-validation.md)
- [ADR-028: Filter Rules Externalization](ADR-028-filter-rules-externalization.md)
- [ADR-042: Testing Strategy Matrix and Fixture Governance](ADR-042-testing-strategy-matrix.md)
- [ADR-044: Run Manifest and Run Ledger Control Plane](ADR-044-run-manifest-ledger-control-plane.md)
- [ADR-045: Data Quality Contract System](ADR-045-dq-contract-system.md)
- [ADR-046: Checkpoint Versus Ledger-Based Resume](ADR-046-checkpoint-vs-ledger-resume.md)
- [ADR-047: Workflow Control Plane for Declarative Workflows](ADR-047-workflow-control-plane.md)
- [Retired Silver-filter draft](../../99-archive/filters/retired-silver-filters-structural-scope.md) — historical draft *(archived)*
- [Silver-to-Gold migration plan](../../99-archive/filters/migration-plan.md) — historical migration context *(archived)*
