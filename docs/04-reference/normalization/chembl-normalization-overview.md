______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-06'

______________________________________________________________________

# ChEMBL Normalization Overview

This page is the published entrypoint for ChEMBL normalization governance
across the active `chembl_*` pipeline family.

Use it when you need the current rule boundary between:

- raw provider values
- canonical normalized Silver/Gold values
- DQ expectations
- content-hash / identity implications
- source-specific subset policy vs global cross-provider taxonomy

## Canonical Evidence Surfaces

- generated matrix entrypoint:
  Historical: [Normalization Plan P0-P6](../../99-archive/engineering/normalization_plan_P0_P6.md)
  with generated artifact path
  `docs/reports/generated/pipeline_normalization_field_matrix/pipeline_normalization_field_matrix.md`
- shipped profile registry:
  [registry.py](../../../src/bioetl/domain/normalization/profiles/registry.py)
- ChEMBL enum registry:
  [configs/enums/chembl.yaml](../../../configs/enums/chembl.yaml)
- ChEMBL controlled vocab registry:
  [configs/vocab/chembl_controlled.yaml](../../../configs/vocab/chembl_controlled.yaml)
- ChEMBL ontology policy registry:
  [configs/vocab/chembl_ontology.yaml](../../../configs/vocab/chembl_ontology.yaml)
- ChEMBL policy parity suite:
  [test_chembl_policy_surface_parity.py](../../../tests/integration/config/test_chembl_policy_surface_parity.py)

## Governance Categories

| Category | Meaning | Typical ChEMBL examples |
| --- | --- | --- |
| Strict enum | Closed reviewed vocabulary; unknowns fail canonicalization or validation. | `target_type`, `term_type`, `assay_type`, `relationship_type`, `confidence_description`, `standard_units` |
| Controlled vocabulary | Canonicalizer exists, but the provider boundary is not treated as a closed exhaustive enum. | selected assay parameter fields, raw unit aliases, subcellular-fraction vocabulary |
| Flag-like | Shared nullable flag semantics with reviewed lexical coercion. | `standard_flag`, `potential_duplicate`, molecule/provider flags |
| Operator | Closed relation/operator vocabulary with canonical aliases. | `relation`, `standard_relation` |
| Unit-like | Canonical unit or ontology-backed unit field; may preserve raw reviewable source value separately. | `units`, `uo_units`, `qudt_units` |
| Ontology/reference identifier | Canonical prefix or companion-bundle semantics are governed, but values are not treated as an exhaustive enum set. | `bao_*`, `bto_id`, `efo_id`, `uberon_id`, `caloha_id` |
| Structured JSON sidecar | Canonical JSON ordering and set-like semantics are governed before hashing. | `activity_properties`, `assay_parameters`, target component JSON/list fields |
| Derived vocabulary | Canonical analytical field derived from raw provider values. | `publication_type`, `publication_type_unified`, `publication_class` |

## Dual-Field Strategy

Use raw + canonical paired fields when canonicalization can lose semantic or
audit-relevant provider detail.

Current high-signal examples:

- `publication_type_raw` vs `publication_type`
- `oa_status` as a source-governed strict enum in `chembl_publication`
- `subcellular_fraction_raw` vs `subcellular_fraction`
- raw unit alias field `units` vs strict `standard_units`
- `organism` / `taxonomy_id` vs derived strict-enum `organism_class`
- ontology identifier + companion bundle fields such as
  `efo_id` / `efo_iri` / `efo_mapping_status` / `efo_ontology_version`

Rule of thumb:

1. Preserve the raw provider token when it carries provenance or future-review value.
1. Use the canonical field for Silver/Gold comparability, hashing, and DQ.
1. Do not silently collapse ontology/reference identifiers into strict enums.

## Identity And Dual-Field Map

| Pipeline | Runtime-authoritative business identity | Canonical seam | Raw/audit seam |
| --- | --- | --- | --- |
| `chembl_publication_term` | `publication_id + term_type + term` | `publication_id` through shared ChEMBL ID normalization, `term_type` through strict enum canonicalization, `term` through profile text/title cleanup before digesting `entity_id` | none beyond provider payload itself |
| `chembl_subcellular_fraction` | `subcellular_fraction` | canonical governed-vocabulary value used for hashing and SCD identity | `subcellular_fraction_raw` preserves provider lexeme |
| `chembl_tissue` | `tissue_id` | ontology IDs canonicalized to underscore forms and expanded into companion bundles before DQ/hash comparison | alias inputs such as `bto:...` are accepted only as source forms and must normalize away |

## ChEMBL-Specific Policy Notes

- `configs/enums/chembl.yaml` remains the canonical source for strict reviewed
  enum families.
- `configs/vocab/chembl_controlled.yaml` governs strict booleans, strict flags,
  controlled vocabularies, and the raw-units vs standard-units split.
- `configs/vocab/chembl_ontology.yaml` governs ontology/reference seams and
  companion-bundle behavior.
- ChEMBL publication type policy is split intentionally:
  global taxonomy stays cross-provider, while
  `configs/entities/chembl/publication.yaml` documents a source-specific ChEMBL
  subset policy.
- JSON ordering for ChEMBL is domain-authoritative and must not be redefined in
  per-entity hash-policy mirrors.

## Anti-Patterns

Do not:

- treat ontology identifiers as strict enums because current fixtures show a
  small observed set
- use raw API alias field names in authoritative content-hash selectors
- redefine source-specific ChEMBL filter subsets as if they were the global
  taxonomy
- drop raw provider fields when canonicalization can remove reviewable context
- duplicate ChEMBL JSON ordering semantics in config mirrors

## Current Published Detail

| Topic | Reference |
| --- | --- |
| Activity | [providers/chembl/activity.md](../providers/chembl/activity.md) |
| Assay | [providers/chembl/assay.md](../providers/chembl/assay.md) |
| Assay Parameters | [providers/chembl/assay-parameters.md](../providers/chembl/assay-parameters.md) |
| Publication | [providers/chembl/publication.md](../providers/chembl/publication.md) |
| Publication Term | [providers/chembl/publication-term.md](../providers/chembl/publication-term.md) |
| Subcellular Fraction | [providers/chembl/subcellular-fraction.md](../providers/chembl/subcellular-fraction.md) |
| Target | [providers/chembl/target.md](../providers/chembl/target.md) |
| Tissue | [providers/chembl/tissue.md](../providers/chembl/tissue.md) |

## Related Published References

- [Reference Index](../index.md)
- [Data Providers Documentation](../providers/README.md)
- [Non-ChEMBL Normalization Overview](non-chembl-normalization-overview.md)
- [Publication Normalization](publication-normalization.md)
- [Reference Identifiers](reference-identifiers.md)
