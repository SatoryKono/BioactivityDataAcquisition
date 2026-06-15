______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-06-15'

______________________________________________________________________

# ADR-050: Silver Structural and Gold Semantic Filter Boundary

**Date:** 2026-06-15
**Status:** Accepted
**Decision makers:** @BioETL-Team
**Related:** ADR-002, ADR-014, ADR-017, ADR-018, ADR-028, ADR-042, ADR-044, ADR-045, ADR-046, ADR-047
**Amends:** ADR-028 (Filter Rules Externalization)
**Source issue:** [#5112](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5112)

## Context (ADR-002, ADR-018, ADR-028)

ADR-002 defines the Medallion split: Silver is normalized, cleaned data that can
feed multiple Gold outputs, while Gold is the business-facing layer. ADR-018
requires strict Gold validation for downstream guarantees. ADR-028 externalized
filter rules into the unified configuration hierarchy, but historical
`silver_filters` and `gold_filters` shared semantic operator shapes such as
`columns`, `ranges`, `list_lengths`, and `list_contains`.

That overlap left the boundary ambiguous. Some active entity configs still carry
legacy semantic rules under `filters.silver_filters`, while current
infrastructure already normalizes those rules through
`src/bioetl/infrastructure/config/silver_filter_migration.py`.

The retired working draft
`docs/filters/ADR-048-silver-filters-structural-scope.md` captured the original
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
surfaces must stay deterministic under ADR-014 and ADR-044.

## Compatibility Window (ADR-014, ADR-044, ADR-046, ADR-047)

During the compatibility window, infrastructure may accept legacy semantic keys
under `filters.silver_filters` only at configuration boundaries. The accepted
runtime mode is `structural_only_auto_promote`:

1. Semantic Silver rules are promoted into Gold filter payloads before domain
   conversion.
1. Domain Silver filter objects used by runtime code contain only structural
   rules.
1. Effective config, run manifest, execution fingerprint, and checkpoint
   compatibility payloads must record the compatibility mode.
1. Gold wins when a legacy Silver semantic rule conflicts with an explicit Gold
   semantic rule.

The compatibility window exists to support deterministic migration of current
YAML configs; it is not permission to add new semantic Silver rules.

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

Operator-facing text may retain legacy names only while it clearly describes the
narrowed structural meaning and has a cleanup path.

## Cleanup Criteria (ADR-028, ADR-042, ADR-044, ADR-047)

The compatibility window can close only after all criteria below are met:

1. Current inventory includes config, runtime, source-profile, and observability
   surfaces for the Silver/Gold filter boundary.
1. Entity configs no longer contain semantic keys under
   `filters.silver_filters`, or every remaining legacy key has an explicit
   reviewed exception.
1. A parity harness proves that promoted legacy Silver semantic rules and
   canonical Gold semantic rules produce equivalent Gold eligibility decisions
   for representative entities.
1. Run manifest, checkpoint, and effective-config identity surfaces preserve the
   filter compatibility mode.
1. Observability and CLI wording no longer imply that semantic/business rejects
   are Silver rejects.
1. CI guardrails fail new semantic keys under `filters.silver_filters`.

After cleanup, new semantic Silver rules are governance violations.

## Consequences (ADR-002, ADR-018, ADR-028, ADR-045)

### Positive

- The Medallion boundary is explicit: Silver structural quality is separate from
  Gold semantic/business eligibility.
- Existing compatibility code has a canonical ADR and a bounded cleanup path.
- `extraction_params` remain source-profile policy instead of being folded into
  Silver filtering semantics.
- Operator-facing reject categories can be cleaned up without changing Gold
  strict validation or DQ contract ownership.

### Negative

- Current YAML configs still require cleanup or reviewed exceptions for legacy
  semantic Silver keys.
- Metrics, dashboards, and CLI wording need follow-up work because historical
  names imply broader Silver reject semantics.
- The compatibility window adds temporary complexity to config identity and
  migration testing.

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

- `docs/filters/README.md` and `docs/filters/migration-plan.md` cite this ADR
  as the normative decision and treat the local ADR-048 filter draft as
  historical context only.
- Targeted search finds no stale references that cite the retired ADR-048 draft
  as accepted Silver-filter governance.
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
- [Retired Silver-filter draft](../../filters/ADR-048-silver-filters-structural-scope.md)
- [Silver-to-Gold migration plan](../../filters/migration-plan.md)
