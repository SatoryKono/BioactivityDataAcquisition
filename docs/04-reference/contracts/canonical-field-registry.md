______________________________________________________________________

Version: 1.1.0
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

It documents canonical field names for active BioETL runtime surfaces where
semantic identity is proven by a registry, mapping module, or composite alias
configuration. Generic same-name fields are intentionally excluded until owner
review classifies them as real semantic identity rather than lexical overlap.

## Governance Basis

- `ADR-039` defines the unified entity-config format that carries canonical
  schema, filter and contract sections.
- `ADR-026` defines composite join and merge surfaces that must consume
  canonical field names.
- `ADR-018` requires Gold validation to bind to stable canonical schema fields.
- `ADR-045` requires DQ policies to bind to the same stable canonical fields.

## Active Clusters

| Cluster | Legacy / Provider-Native Names | Canonical Name | Active Pipelines | Runtime Status |
| ------- | ------------------------------ | -------------- | ---------------- | -------------- |
| ChEMBL assay business identifier | `assay_chembl_id` | `assay_id` | `chembl_assay`, `chembl_activity`, `composite_assay`, `composite_activity` | canonical_internal_with_legacy_input_filter |
| ChEMBL molecule business identifier | `molecule_chembl_id` | `molecule_id` | `chembl_molecule`, `chembl_activity`, `chembl_compound_record`, `composite_molecule`, `composite_activity` | canonical_internal_with_legacy_input_filter |
| PubMed publication identifier | `pubmed_id` | `pmid` | `pubmed_publication`, `chembl_publication`, `crossref_publication`, `openalex_publication`, `semanticscholar_publication`, `composite_publication` | canonical_internal_with_legacy_input_filter |
| Digital Object Identifier | `doi` | `doi` | `chembl_publication`, `crossref_publication`, `openalex_publication`, `pubmed_publication`, `semanticscholar_publication`, `composite_publication` | canonical_internal_and_external |
| Publication display title | `pubmed_title`, `openalex_title` | `title` | `pubmed_publication`, `openalex_publication`, `crossref_publication`, `semanticscholar_publication`, `chembl_publication`, `composite_publication` | canonical_internal_with_legacy_aliases_retired |
| Publication type classification | `doc_type`, `source_type` | `publication_type` | `chembl_publication`, `crossref_publication`, `openalex_publication`, `semanticscholar_publication`, `composite_publication` | canonical_internal_with_provider_aliases |
| Publication year | `year` | `publication_year` | `chembl_publication`, `crossref_publication`, `openalex_publication`, `pubmed_publication`, `semanticscholar_publication`, `composite_publication` | canonical_internal_with_provider_aliases |
| Publication journal title | `journal_title` | `journal` | `chembl_publication`, `pubmed_publication`, `composite_publication` | canonical_internal_with_provider_aliases |
| Abbreviated journal title | `journal_abbrev`, `short_container_title` | `journal_name_short` | `crossref_publication`, `pubmed_publication`, `composite_publication` | canonical_internal_with_provider_aliases |
| First publication page | `first_page` | `page_first` | `crossref_publication`, `openalex_publication`, `pubmed_publication`, `semanticscholar_publication`, `composite_publication` | canonical_internal_with_provider_aliases |
| Last publication page | `last_page` | `page_last` | `crossref_publication`, `openalex_publication`, `pubmed_publication`, `semanticscholar_publication`, `composite_publication` | canonical_internal_with_provider_aliases |
| Publication page range | `pages` | `page_range` | `pubmed_publication`, `semanticscholar_publication`, `composite_publication` | canonical_internal_with_provider_aliases |
| Inbound citation count | `citation_count` | `citations_received` | `crossref_publication`, `openalex_publication`, `semanticscholar_publication`, `composite_publication` | canonical_internal_with_provider_aliases |
| Outbound reference count | `reference_count` | `citations_made` | `crossref_publication`, `openalex_publication`, `pubmed_publication`, `semanticscholar_publication`, `composite_publication` | canonical_internal_with_provider_aliases |
| Publication subject keywords | `keywords`, `subjects` | `subject_keywords` | `crossref_publication`, `openalex_publication`, `pubmed_publication`, `composite_publication` | canonical_internal_with_provider_aliases |
| Publication topic taxonomy payload | `topics` | `subject_topics` | `openalex_publication`, `composite_publication` | canonical_internal_with_provider_aliases |
| Publication MeSH subject terms | `mesh_terms` | `subject_mesh` | `pubmed_publication`, `composite_publication` | canonical_internal_with_provider_aliases |
| Publication field-of-study labels | `fields_of_study` | `subject_fields` | `semanticscholar_publication`, `composite_publication` | canonical_internal_with_provider_aliases |
| Publication author affiliation list | `affiliations` | `affiliation_list` | `openalex_publication`, `pubmed_publication`, `semanticscholar_publication`, `composite_publication` | canonical_internal_with_provider_aliases |
| Structured publication affiliation payload | `structured_affiliations` | `affiliation_structured` | `pubmed_publication`, `composite_publication` | canonical_internal_with_provider_aliases |
| Hydrogen bond acceptor count | `h_bond_acceptor_count`, `hba` | `hba_count` | `chembl_molecule`, `pubchem_compound`, `composite_molecule` | canonical_internal_with_provider_aliases |
| Hydrogen bond donor count | `h_bond_donor_count` | `hbd_count` | `chembl_molecule`, `pubchem_compound`, `composite_molecule` | canonical_internal_with_provider_aliases |
| Topological polar surface area | `tpsa` | `polar_surface_area` | `chembl_molecule`, `pubchem_compound`, `composite_molecule` | canonical_internal_with_provider_aliases |
| Octanol-water partition coefficient | `xlogp` | `logp` | `chembl_molecule`, `pubchem_compound`, `composite_molecule` | canonical_internal_with_provider_aliases |
| Standard IUPAC InChI identifier | `inchi` | `standard_inchi` | `chembl_molecule`, `pubchem_compound`, `composite_molecule` | canonical_internal_with_provider_aliases |
| Standard InChIKey identifier | `inchi_key` | `inchi_key` | `chembl_molecule`, `pubchem_compound`, `composite_molecule` | canonical_internal_with_provider_aliases |
| Molecular weight descriptor | `molecular_weight` | `molecular_weight` | `chembl_molecule`, `pubchem_compound`, `composite_molecule` | canonical_internal_with_provider_aliases |

## Affected Runtime Surfaces

- Unified entity configs in `configs/entities/**`
- Composite join, alias and merge configs in `configs/composites/**`
- Gold/Pandera schema and DQ policy surfaces bound to canonical fields
- Domain mapping registries in `src/bioetl/domain/mapping/**`
- Molecule alias registry in `src/bioetl/domain/registry/field_aliases.py`
- Migration/test guardrails enforcing no drift back to legacy internal names

## Deliberate Non-Goals

- Do not canonicalize generic lexical collisions such as `type`, `value`,
  `score`, `description`, `relation`, or `source` without owner review.
- Do not collapse related ontology/unit roles such as `standard_units`,
  `uo_*`, `qudt_*`, labels, codes and IRIs into one alias cluster.
- Do not treat stage-specific requiredness differences as resolved unless
  DQ, composite and Gold contract parity tests document the allowed behavior.

## Closure Evidence

Issue closure for semantic field unification is anchored by:

- registry asset: `configs/field_registry/canonical_registry.json`
- CSV matrix: `docs/04-reference/contracts/canonical-field-registry.csv`
- runtime loader: `src/bioetl/infrastructure/config/semantic_field_registry_loader.py`
- guardrail tests: `tests/unit/infrastructure/config/test_semantic_field_registry_loader.py`
  and `tests/integration/config/test_semantic_field_unification_contract.py`
- QA check: `python3 scripts/engineering/qa/check_semantic_field_registry.py --check`
