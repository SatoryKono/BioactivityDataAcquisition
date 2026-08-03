# ADR-055: Retain foreign-key reconciliation as a governed workflow data step

**Status:** Accepted  
**Date:** 2026-07-29  
**Owners:** BioETL Team  
**Review:** 2027-01-29

## Context

`chembl_core` and `chembl_baseline` execute `reconcile_foreign_keys` against
Gold datasets. The operation is data-plane transformation, DQ validation, and a
destructive logical mutation. Moving it to a dedicated pipeline could provide a
separate pipeline identity, but would also introduce a new compatibility and
replay boundary.

Current ADR-047 behavior already provides configuration validation,
idempotency, dry-run, quarantine, SCD2 history preservation, transform result
and debug artifacts, workflow manifest/ledger correlation, exclusive locking,
and `commit_pending_confirmation` ambiguity blocking.

## Decision

Retain `reconcile_foreign_keys` as an explicitly governed ADR-047 workflow data
step.

- Workflow passports must classify it as
  `data_plane_transformation`, `dq_validation`, and `destructive_mutation`.
- Config remains strict and names source/reference/mutation layers, datasets,
  keys, and action.
- Gold mutation must preserve SCD2 history and quarantine evidence.
- Resume after an ambiguous commit remains blocked without explicit
  repair/force intent.
- The result artifact and workflow control-plane records constitute the
  independently inspectable execution evidence.
- New workflow transforms default to `unknown` classification and cannot be
  published until classified.

A dedicated reconciliation pipeline may be reconsidered only with golden
old/new equivalence, replay-parentage, validation, lineage, and migration
evidence. No feature flag or debt exemption is introduced by this decision.

## Alternatives considered

1. Dedicated reconciliation pipeline — clearer identity, but duplicates the
   established workflow recovery surface and requires migration.
2. Generic Application data-step registry — adds another executable-unit kind
   without demonstrated need.
3. Keep the transform undocumented — rejected because it hides data semantics.

## Consequences

The workflow remains more than orchestration-only, but that fact is explicit,
versioned, and governed. Passport generation can proceed without inventing a
new runtime surface. Review is time-bounded and technical-debt budgets remain
unchanged.

