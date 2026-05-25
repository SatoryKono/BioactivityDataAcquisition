______________________________________________________________________

Version: 1.1.0
Status: published
Class: reference
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-15'

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
| ChEMBL assay business identifier | `assay_chembl_id` | `assay_id` | `chembl_assay`, `chembl_activity`, `composite_assay`, `composite_activity` | canonical_internal_with_provider_native_ingestion_boundary |
| ChEMBL molecule business identifier | `molecule_chembl_id` | `molecule_id` | `chembl_molecule`, `chembl_activity`, `chembl_compound_record`, `composite_molecule`, `composite_activity` | canonical_internal_with_provider_native_ingestion_boundary |
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

## Semantic Anchor Parity Gate

`scripts/engineering/qa/check_semantic_anchor_parity.py --check` is the
targeted parity guard for join and lineage anchors where semantic identity has
runtime consequences. The gate currently covers `doi`, `pmid`, `pmc_id`,
`title`, `publication_id`, `assay_id`, `molecule_id`, `target_id`,
`canonical_smiles`, `inchi_key`, `uniprot_accession`, and UniProt protein
`accession` across entity DQ rules, Gold JSON schemas, domain join-key
normalization policies, and composite join/fallback/output-key surfaces.

The gate intentionally preserves stage-specific semantics:

- `doi`, `pmid`, `title`, `publication_id`, `assay_id`, `molecule_id`,
  `target_id`, and UniProt protein `accession` are checked as required only on
  the provider/entity Gold contracts where current DQ and filter policy already
  make them required.
- `pmc_id`, activity-level `publication_id`/`target_id`, `canonical_smiles`,
  `inchi_key`, and idmapping `uniprot_accession` are checked as nullable
  lineage, structure, fallback, or chained-join anchors when current contracts
  allow alternate anchors or staged filtering.

## Generic Field Ownership Gate

`configs/field_registry/generic_field_ownership.yaml` is the ownership registry
for generic lexical fields such as `description`, `type`, `status`, `value`,
`relation`, `source`, and `score`. These names are not allowed to become
canonical semantic clusters by lexical match alone.

`scripts/engineering/qa/check_generic_field_ownership.py --check` validates that
generic fields on governed Gold and composite surfaces have explicit owner,
semantic role, and rationale metadata. System-scoped lineage fields such as
`_source` remain separate from business semantic canonicalization.

## Semantic Registry Drift Gate

`scripts/engineering/qa/check_semantic_registry_drift.py --check` regenerates
exact alias and identity candidates from runtime mapping surfaces and verifies
that every candidate resolves through
`configs/field_registry/canonical_registry.json`.

Blocking sources:

- `src/bioetl/domain/mapping/publication_fields.py`
- `src/bioetl/domain/mapping/molecule_fields.py`
- `src/bioetl/domain/registry/field_aliases.py`
- `configs/composites/molecule.yaml#composite.field_aliases`

The gate intentionally treats `PARTIAL`, `WEAK`, or `CONFLICTING` clusters from
the exhaustive semantic audit registry as non-blocking only when they are
covered by `configs/field_registry/semantic_audit_review_registry.yaml`.
Same-name publication, ontology, unit, and generic lexical clusters must not
become canonical fields until an owner classifies them and updates the registry
with explicit migration semantics.

## Semantic Pair-Matrix Budget Gate

`configs/field_registry/semantic_pair_matrix_budget.yaml` records the reviewed
semantic pair-matrix drift budget from the exhaustive 2026-05-15 audit. The
budget currently ratchets `CRITICAL`, `HIGH`, and `MEDIUM` rows at 0, blocks
unreviewed `Normalization=DIFFERENT`, `Typing=CONFLICTING`, and
`Validation=STRICTNESS_MISMATCH` rows, and freezes growth in the reviewed
non-blocking inventories:

- `Semantic Status=PARTIAL`: maximum 67 rows, all owner-reviewed;
- `Semantic Status=WEAK`: maximum 439 rows, all owner-reviewed;
- `Semantic Status=CONFLICTING`: maximum 20 rows, all owner-reviewed;
- `Normalization=COMPATIBLE`: maximum 900 rows;
- `Validation=COMPATIBLE`: maximum 1053 rows;
- `Typing=COMPATIBLE`: maximum 664 rows.

The generated semantic cluster registry also attaches owner review metadata to
all remaining `PARTIAL`, `WEAK`, and `CONFLICTING` clusters. Those rows are
policy-reviewed semantic inventory, not blockers; they may decrease without a
budget change, but growth requires an intentional budget update and owner
review.

For reviewed `WEAK` clusters, the generated registry may additionally attach a
`weak_decision` block when policy has classified the cluster more precisely
than generic same-name inventory. That metadata is used for role-governed
ontology/unit companions and explicit source-owned assay metadata families so
they cannot be silently promoted from lexical overlap alone.

`scripts/engineering/qa/check_semantic_pair_matrix_budget.py --check` validates
that:

- no `CRITICAL`, `HIGH`, or `MEDIUM` rows appear in the current matrix;
- blocking status budgets remain at zero;
- reviewed non-exact and compatible-row inventories do not grow silently;
- every non-exact semantic cluster in the generated registry has owner,
  rationale, review id, and expiry metadata.

The generated audit also publishes
`reports/semantic_pipeline_audit/base_config_semantic_coverage_2026-05-15.json`
so `configs/base/**` remains visible alongside entity and composite pipeline
surfaces. That artifact tracks base DQ defaults, contract registry identity
metadata, Medallion sort/default settings, and fixture/gap governance.

The generated audit additionally publishes
`reports/semantic_pipeline_audit/semantic_residual_backlog_2026-05-15.json` and
`reports/semantic_pipeline_audit/semantic_residual_backlog_2026-05-15.md`.
Those artifacts are the canonical residual-task register for the audit. They
currently report zero blocking tasks and list the reviewed partial-identity,
weak-inventory, generic-collision, compatible-normalization,
compatible-validation, compatible-typing, and base-config-coverage ratchets.
Review entries expire on `2026-11-15` unless renewed or burned down.

## Ontology And Unit Role Gate

`configs/field_registry/ontology_unit_semantic_roles.yaml` is the role registry
for unit and ontology companion fields. It defines separate contract roles for
raw unit text (`units`), standardized unit tokens (`standard_units`),
measurement type (`standard_type`), ontology IDs (`uo_units`, `qudt_units`,
`bao_*`, `bto_*`, `efo_*`, `uberon_*`, `clo_*`), canonical IRIs, mapping
statuses, labels, and ontology version fields.

`scripts/engineering/qa/check_ontology_unit_semantics.py --check` validates
that those fields stay out of the canonical alias-cluster registry and retain
their DQ companion rules:

- code or unit field present -> mapping status required;
- mapping status `mapped` -> canonical IRI and ontology version required;
- ChEMBL activity standardized measurement fields keep enum/pattern DQ and
  Silver/Gold required-field filters aligned.
## Closure Evidence

Issue closure for semantic field unification is anchored by:

- registry asset: `configs/field_registry/canonical_registry.json`
- CSV matrix: `docs/04-reference/contracts/canonical-field-registry.csv`
- runtime loader: `src/bioetl/infrastructure/config/semantic_field_registry_loader.py`
- guardrail tests: `tests/unit/infrastructure/config/test_semantic_field_registry_loader.py`
  and `tests/integration/config/test_semantic_field_unification_contract.py`
- QA check: `python3 scripts/engineering/qa/check_semantic_field_registry.py --check`
- semantic registry drift check:
  `python3 scripts/engineering/qa/check_semantic_registry_drift.py --check`
- semantic pair-matrix budget check:
  `python3 scripts/engineering/qa/check_semantic_pair_matrix_budget.py --check`
- semantic anchor parity check:
  `python3 scripts/engineering/qa/check_semantic_anchor_parity.py --check`
- generic field ownership check:
  `python3 scripts/engineering/qa/check_generic_field_ownership.py --check`
- ontology/unit role separation check:
  `python3 scripts/engineering/qa/check_ontology_unit_semantics.py --check`
