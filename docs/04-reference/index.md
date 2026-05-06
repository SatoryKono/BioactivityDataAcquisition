______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-02'

______________________________________________________________________

# Reference Index

## Purpose

This page is the landing surface for published reference material in
`docs/04-reference/`.

Use reference docs when you need the current public contract, CLI surface,
provider or pipeline specs, or API/package reference. Use architecture docs for
design rationale and layer structure.

## Reference Surfaces

| Section           | Purpose                                                             | Entry point                                            |
| ----------------- | ------------------------------------------------------------------- | ------------------------------------------------------ |
| CLI               | Supported command-line surface                                      | [cli.md](cli.md)                                       |
| Contracts         | Published control-plane, observability, and gold-contract material  | [contracts/README.md](contracts/README.md)             |
| Normalization     | Published normalization governance for provider fields and IDs      | [normalization/chembl-normalization-overview.md](normalization/chembl-normalization-overview.md) |
| Providers         | Provider-specific published specs and field surfaces                | [providers/README.md](providers/README.md)             |
| Pipelines         | Pipeline-specific published specs and historical pipeline artifacts | [pipelines/README.md](pipelines/README.md)             |
| API               | Generated or curated package/module API reference                   | [api/index.md](api/index.md)                           |
| Templates         | Reusable templates for ADRs, contracts, specs, and runbooks         | [templates/index.md](templates/index.md)               |
| Internal/Extended | Internal implementation details and extended surfaces               | [internalextended/index.md](internalextended/index.md) |

## Current High-Signal References

- [Run Manifest and Run Ledger Contract](contracts/run-manifest-ledger.md)
- [Observability Metrics](contracts/observability.md)
- [CLI Reference](cli.md)
- [Gold Schemas](contracts/gold-schemas.md)
- [ChEMBL Normalization Overview](normalization/chembl-normalization-overview.md)
- [Non-ChEMBL Normalization Overview](normalization/non-chembl-normalization-overview.md)
- [Non-ChEMBL Normalization Inventory](normalization/non-chembl-normalization-inventory.md)
- [Publication Normalization](normalization/publication-normalization.md)
- [Publication Validation Index](publication-validation-index.md)

## Boundary With Architecture Docs

- Use [Architecture Overview](../02-architecture/00-overview.md) for layer
  boundaries, diagrams, and ADR routing.
- Use this reference section for concrete published surfaces that operators,
  integrators, or maintainers must consult directly.
