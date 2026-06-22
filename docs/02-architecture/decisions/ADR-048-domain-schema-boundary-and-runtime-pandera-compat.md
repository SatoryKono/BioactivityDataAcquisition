______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-26'

______________________________________________________________________

# ADR-048: Domain Schema Boundary and Runtime Pandera Compatibility

**Date:** 2026-05-26
**Status:** Accepted
**Decision makers:** @BioETL-Team
**Related:** ADR-004, ADR-018, ADR-033, ADR-037

## Context

BioETL intentionally keeps Pandera-backed schemas in the domain layer because
they are data contracts for Silver and Gold records, not infrastructure adapters.
That policy was documented in several places, but two boundaries needed one
accepted decision:

- where Pandera/Pandas imports are allowed inside `src/bioetl/domain`;
- where Python-version runtime validation for Pandera is applied.

Without an explicit rule, schema-contract imports can be misclassified as domain
I/O, and runtime compatibility handling can drift back into package import side
effects.

## Decision

### Domain schema boundary

Domain packages may use Pandera/Pandas only as schema-contract representation
inside:

- `src/bioetl/domain/schemas/`
- `src/bioetl/domain/contracts/`

Those classes are validation contracts, not adapter implementations, and must
not become adapters over time. They must not open files, call networks, construct concrete
infrastructure, or own runtime bootstrapping.

Schema-contract hotspot ownership is narrow by design. Large generated
registries, enum catalogs, Pandera schema modules, and Gold/Silver contract
tables under `domain/schemas` or `domain/contracts` are domain-owned contract
surfaces only. When touched for behavioral change or material growth, they must
be split on touch into smaller pure schema/catalog modules before adding more
responsibility. That split must not move schema ownership into application,
infrastructure, composition, or interface layers.

Domain behavior, services, entities, aggregates, value objects, ports, and
normalization code must stay free of direct Pandera/Pandas imports unless a
future ADR narrows and tests an explicit exception.

### Runtime compatibility validation

No import-time runtime validation is allowed for Pandera runtime support in
`bioetl.__init__` or
`bioetl.composition.bootstrap.runtime.__init__`.

The retained runtime activation seam is:

- `bioetl.composition.bootstrap.runtime.pipeline.apply_runtime_compatibility_patches`

That function now delegates to the infrastructure-owned validation surface:

- `bioetl.infrastructure.compat.pandera_compat.validate_supported_pandera_runtime`

Composition bootstrap may call the sanctioned seam before building runtime
pipelines. Infrastructure owns the third-party runtime support validation
because it is library/runtime compatibility, not domain semantics.

BioETL no longer applies runtime monkeypatches for Python 3.14+ Pandera typing
breakage. The Python 3.14 support shim carries explicit review metadata in
`bioetl.infrastructure.compat.pandera_compat.PANDERA_RUNTIME_SUPPORT_POLICY`.
If the supported Python/Pandera matrix still needs fallback monkeypatching, the
validator must fail fast with an explicit runtime error instead of mutating
third-party behavior at bootstrap time.

## Consequences

### Positive

1. Domain schema contracts remain explicit without weakening the no-I/O domain rule.
1. Pandera/Pandas imports cannot spread into domain behavior or application logic.
1. Runtime import side effects stay deterministic and testable.
1. Unsupported Python/Pandera matrices fail fast instead of mutating third-party behavior at bootstrap time.

### Negative

1. Domain schema packages remain coupled to Pandera as a contract representation.
1. Tests must distinguish schema-contract imports from forbidden runtime imports.
1. Python-version compatibility validation remains present until upstream Pandera no longer needs it.

## Compliance

- Architecture tests must fail if direct Pandera/Pandas imports appear outside
  `domain/schemas` or `domain/contracts`.
- Architecture tests must fail if domain schema-contract hotspots import runtime
  layers or perform I/O instead of remaining pure schema/catalog surfaces.
- Architecture tests must fail if package import initialization applies
  Pandera runtime validation directly.
- Runtime bootstrap tests must preserve the explicit
  `apply_runtime_compatibility_patches` activation seam and its delegation to
  `validate_supported_pandera_runtime`.
