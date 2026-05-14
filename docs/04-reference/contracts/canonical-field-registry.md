______________________________________________________________________

Version: 1.0.0
Status: published
Class: reference
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-14'

______________________________________________________________________

# Canonical Field Registry

This document is the published companion to
`configs/field_registry/canonical_registry.json`.

It closes the semantic-field-unification wave by documenting one canonical
field name per business identifier cluster for active BioETL runtime surfaces.

## Governance Basis

- `ADR-039` defines the unified entity-config format that carries canonical
  schema, filter and contract sections.
- `ADR-026` defines composite join and merge surfaces that must consume
  canonical field names.
- `ADR-018` requires Gold validation to bind to stable canonical schema fields.
- `ADR-045` requires DQ policies to bind to the same stable canonical fields.

## Active Clusters

| Cluster | Legacy / Provider-Native Name | Canonical Name | Active Pipelines | Runtime Status |
| ------- | ----------------------------- | -------------- | ---------------- | -------------- |
| ChEMBL assay identifier | `assay_chembl_id` | `assay_id` | `chembl_assay`, `chembl_activity`, `composite_assay`, `composite_activity` | Canonical internal field; legacy provider column retained only at input filter boundary |
| ChEMBL molecule identifier | `molecule_chembl_id` | `molecule_id` | `chembl_molecule`, `chembl_activity`, `composite_molecule`, `composite_activity` | Canonical internal field; legacy provider column retained only at input filter boundary |
| PubMed identifier | `pubmed_id` | `pmid` | `pubmed_publication`, `composite_publication` | Canonical internal field; legacy provider column retained only at input filter boundary |
| DOI | `doi` | `doi` | `crossref_publication`, `openalex_publication`, `pubmed_publication`, `semanticscholar_publication`, `composite_publication` | Canonical both externally and internally |
| Publication title | `pubmed_title`, `openalex_title` | `title` | `pubmed_publication`, `openalex_publication`, `crossref_publication`, `semanticscholar_publication`, `composite_publication` | Canonical internal field; historical prefixed aliases retired into registry-only references |

## Affected Runtime Surfaces

- Unified entity configs in `configs/entities/**`
- Composite join and merge configs in `configs/composites/**`
- Gold/Pandera schema and DQ policy surfaces bound to canonical key fields
- Migration/test guardrails enforcing no drift back to legacy internal names

## Closure Evidence

Issue closure for `#4087`-`#4092` is anchored by:

- registry asset: `configs/field_registry/canonical_registry.json`
- CSV matrix: `docs/04-reference/contracts/canonical-field-registry.csv`
- migration runbook: `docs/migration.md`
- runtime loader: `src/bioetl/infrastructure/config/semantic_field_registry_loader.py`
- guardrail tests: `tests/unit/infrastructure/config/test_semantic_field_registry_loader.py`
  and `tests/integration/config/test_semantic_field_unification_contract.py`
