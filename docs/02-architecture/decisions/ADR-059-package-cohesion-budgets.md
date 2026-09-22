______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Last verified: '2026-09-22'

______________________________________________________________________

# ADR-059: Package cohesion budgets (shrink-only)

**Date:** 2026-08-25
**Status:** Accepted
**Linked issues:** #9603, #9606, #10552
**Related:** ADR-049, ADR-041

## Context

Per-file LOC caps (`test_code_metrics.py`) force horizontal splits:
`domain/aggregates` has 19 modules, several of which are mixins created to
stay under the domain 305-line cap. Package-level cohesion is a better
proxy than file count.

## Decision

1. Per-file layer LOC caps stay unchanged (no tech-debt budget growth).
2. New shrink-only package budgets live in
   `configs/quality/package_cohesion_budget.yaml`:
   `max_modules` and `max_package_loc` per package.
3. `domain/aggregates` target is ≤8 modules; live `max_modules` ratchets
   down as private mixins are consolidated without exceeding 305 LOC.
   Hold-flat at the live ceiling until a merge fits under 305 LOC (#10552).
4. `Batch` root imports go through `bioetl.domain.aggregates` (or
   `_batch_aggregate`). The `batch.Batch` compatibility `__getattr__`
   shim was removed in #10552; `batch.py` keeps value objects and mixins.

## Consequences

Mixin files that exist only to satisfy the 305 LOC cap may be merged when
the merged file stays under the cap. Helper-ratio for
`application_services_control_plane` is tracked as a shrink-only target
(0.40) and is not raised. New aggregate modules in `domain/aggregates`
require a prior private-mixin consolidation that keeps every merged file
≤305 LOC; raising `max_modules` is forbidden.
