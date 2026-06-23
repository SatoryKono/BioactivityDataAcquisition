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

## Publication Boundary

- This section catalogs **published** reference entrypoints that are expected to
  stay aligned with live code, configs, and supported operator workflows.
- Package maps under `src/**/README.md` are `code-navigation-only` repo
  surfaces. They help contributors read the source tree but they are not the
  canonical published reference authority.
- Repo-only supporting material such as `docs/plans/**`, `docs/reports/**`, and
  `docs/99-archive/**` remains outside MkDocs publication and should be cited as
  repository-path context, not treated as active reference guidance.
- When a published page delegates to a compact compatibility summary, the page
  must say so explicitly and point back to the current canonical spec or config
  surface.

## Reference Surfaces

| Section           | Purpose                                                                                      | Entry point                                            |
| ----------------- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| CLI               | Supported command-line surface                                                               | [cli.md](cli.md)                                       |
| Workflow Catalog  | Current declarative workflow DAG catalog                                                     | [workflow-catalog.md](workflow-catalog.md)             |
| GitHub Actions Workflows | Current CI / nightly / release workflow inventory under `.github/workflows/`        | [github-actions-workflows.md](github-actions-workflows.md) |
| Pipeline Catalog  | Current provider and composite pipeline config catalog                                       | [pipeline-catalog.md](pipeline-catalog.md)             |
| Domain            | Canonical published catalog for aggregates, value objects, events, ports, invariants, and workflow lifecycle semantics | [domain/README.md](domain/README.md) |
| Contracts         | Published contract pack for Gold, DQ, control-plane, and observability surfaces             | [contracts/README.md](contracts/README.md)             |
| Normalization     | Published normalization governance for provider fields and IDs                               | [normalization/chembl-normalization-overview.md](normalization/chembl-normalization-overview.md) |
| Providers         | Provider-specific published specs and current config-linked field surfaces                   | [providers/README.md](providers/README.md)             |
| Pipelines         | Active pipeline specs linked to `configs/entities/**`, `configs/composites/**`, and providers | [pipelines/README.md](pipelines/README.md)           |
| API               | Curated package/module API guidance mapped to the live `src/bioetl/**` tree                 | [api/index.md](api/index.md)                           |
| Templates         | Reusable templates for ADRs, contracts, specs, and runbooks                                 | [templates/index.md](templates/index.md)               |
| Internal/Extended | Published extended material that is still secondary to the canonical reference surfaces      | [internalextended/index.md](internalextended/index.md) |

## Live Canonical Sources Behind The Reference Pages

- Runtime packages: `src/bioetl/domain/`, `src/bioetl/application/`,
  `src/bioetl/infrastructure/`, `src/bioetl/composition/`, `src/bioetl/interfaces/`
- Pipeline configs: `configs/entities/**`, `configs/composites/*.yaml`,
  `configs/providers/*.yaml`
- Contract configs: `configs/contracts/**`
- Gold contract code: `src/bioetl/domain/contracts/gold/`
- Control-plane domain models and ports:
  `src/bioetl/domain/control_plane/`, `src/bioetl/domain/ports/control_plane/`

## Current High-Signal References

- [Run Manifest and Run Ledger Contract](contracts/run-manifest-ledger.md)
- [Data Contracts Current State](contracts/data-contracts-current.md)
- [Pipeline Catalog](pipeline-catalog.md)
- [Workflow Catalog](workflow-catalog.md)
- [GitHub Actions Workflows](github-actions-workflows.md)
- [Domain Reference](domain/README.md)
- [Domain Contexts](domain/contexts.md)
- [Workflow State Machine](domain/workflow-state-machine.md)
- [Observability Metrics](contracts/observability.md)
- [CLI Reference](cli.md)
- [Gold Schemas](contracts/gold-schemas.md)
- [ChEMBL Normalization Overview](normalization/chembl-normalization-overview.md)
- [Non-ChEMBL Normalization Overview](normalization/non-chembl-normalization-overview.md)
- [Non-ChEMBL Normalization Inventory](normalization/non-chembl-normalization-inventory.md)
- [Publication Normalization](normalization/publication-normalization.md)
- [PubChem Normalization](normalization/pubchem-normalization.md)
- [UniProt Normalization](normalization/uniprot-normalization.md)
- [Reference Identifiers](normalization/reference-identifiers.md)
- [Publication Validation Index](publication-validation-index.md)

## Boundary With Architecture Docs

- Use [Architecture Overview](../02-architecture/00-overview.md) for layer
  boundaries, diagrams, and ADR routing.
- Use this reference section for concrete published surfaces that operators,
  integrators, or maintainers must consult directly.
- Use the repo-only plans index for working context:
  [`../plans/README.md`](../plans/README.md).
- Historical archive material lives in the archived [`../99-archive/README.md`](../99-archive/README.md) index.
- Reports remain non-canonical and should be navigated directly through the
  `docs/reports/` tree when needed.
