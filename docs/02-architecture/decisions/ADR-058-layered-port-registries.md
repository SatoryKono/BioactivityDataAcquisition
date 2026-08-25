______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Last verified: '2026-08-25'

______________________________________________________________________

# ADR-058: Layered port registries (domain / application / composition contracts)

**Date:** 2026-08-25
**Status:** Accepted
**Linked issues:** #9599, #9606
**Related:** ADR-005, ADR-048

## Context

Composition declared 62 `Protocol` classes across 37 modules, parallel to
`domain/ports`. CLI and factories used these as a second contract system.
Putting application orchestration types into `domain/ports` would pollute
the domain dictionary.

## Decision

Protocols are placed by vocabulary:

1. Domain needs → `src/bioetl/domain/ports/**`
2. Application-service contracts → `src/bioetl/application/ports/**`
   (new public package; `__init__.py` is the supported entry)
3. Structural typed views of bootstrap/factory results →
   `src/bioetl/composition/contracts/**` (must not import composition
   implementation modules)

Composition modules outside `contracts/` must not *declare* `Protocol`
classes. They may re-export from the three registries. Migration is
wave-based (≤12 declarations per PR) with a shrink-only remaining-count
gate.

## Consequences

- New public surface `bioetl.application.ports` (breaking for importers
  that depended on composition-private Protocols).
- Remaining composition Protocol declarations decrease only.
- Inventory `configs/quality/composition_protocol_inventory.yaml` must
  stay complete: 62 = domain + application + composition_contracts.

## Rollback

Revert this ADR and restore Protocol class bodies in composition modules.
