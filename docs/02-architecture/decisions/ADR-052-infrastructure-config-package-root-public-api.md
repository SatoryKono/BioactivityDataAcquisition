______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Last verified: '2026-08-09'

______________________________________________________________________

# ADR-052: infrastructure.config package-root as permanent external public API

**Date:** 2026-07-28  
**Status:** Accepted  
**Linked issues:** #6790, #6624 (TD-08 design), #6682 (decision note)  
**Related:** `docs/02-architecture/compatibility/infrastructure-config-package-root-sunset.md`  
**Related note (archived):** [decision note](../../99-archive/decisions/notes/2026-07-27-infrastructure-config-public-api-decision.md)

## Context

Among public lazy facades, `bioetl.infrastructure.config` (package root at
`src/bioetl/infrastructure/config/__init__.py`) was still classified as
`compatibility_debt` while first-party `src/` importers are already zero and
transition/sunset/expired compatibility metrics are `0/0/0`.

Two end-states were open:

1. External deprecation window then removal of package-root convenience.
2. Promote package-root to permanent external public API with hard first-party
   import ban.

## Decision

**Promote `bioetl.infrastructure.config` to permanent external public API.**

1. Classification in `public_lazy_facade_inventory.yaml` is
   `external_public_api` (not `compatibility_debt`).
2. First-party production code **MUST** import owner modules
   (`_base`, loaders, `*_api`) — `max_src_importer_count = 0` for the package root.
3. External consumers **MAY** continue package-root imports of sanctioned
   symbols; growth of the export surface requires inventory review.
4. Transition/twin/sunset metrics remain zero; this surface is **not** counted
   as residual transition-compat debt.
5. The design doc
   `infrastructure-config-package-root-sunset.md` is retained as historical
   analysis; the terminal choice for product policy is this ADR (permanence).

## Consequences

- Issue #6790 closes by reclassification + inventory sync, not by deleting the root.
- Compatibility census continues to fail-fast if first-party src importers reappear.
- Future removal would require a new ADR and external breaking-change process.

## Migration

1. First-party code **MUST** already import owner modules under
   `bioetl.infrastructure.config.*` (not the package root). Census gates enforce
   `max_src_importer_count = 0` for the root facade.
2. External consumers may keep package-root imports of sanctioned symbols listed
   in `public_lazy_facade_inventory.yaml`.
3. New exports on the package root require inventory review in the same change.

## Rollback

1. Rollback of this permanence decision requires a **new ADR** that supersedes
   ADR-052 and an external breaking-change process for consumers.
2. Short-term incident rollback (bad export surface): restore previous
   `__init__.py` export set from git and re-run facade importer census +
   architecture tests.
3. Do not reclassify as `compatibility_debt` without updating scorecard
   semantics — that confuses transition burn-down metrics.

## Alternatives considered

- Hard sunset after 2026-10-21: rejected for now — zero product benefit vs
  external break risk while owner modules remain available for first-party code.
- Leave classification as `compatibility_debt`: rejected — confuses transition
  burn-down metrics with permanent public seams.
