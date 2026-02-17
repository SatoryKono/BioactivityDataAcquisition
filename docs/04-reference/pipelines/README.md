# BioETL Pipeline Documentation

*Updated: 2026-02-04 | Aligned with RULES.md v5.20*

This directory contains documentation for all BioETL pipelines, including composite pipelines.

______________________________________________________________________

## Pipeline Index

### Provider Pipelines (21)

| #   | Pipeline ID                     | Provider         | Entity                 | Spec                                             |
| --- | ------------------------------- | ---------------- | ---------------------- | ------------------------------------------------ |
| 1   | `chembl_protein_class`          | ChEMBL           | protein_class          | [Spec](chembl/01-protein-class-spec.md)          |
| 2   | `chembl_cell_line`              | ChEMBL           | cell_line              | [Spec](chembl/02-cell-line-spec.md)              |
| 3   | `chembl_molecule`               | ChEMBL           | molecule               | [Spec](chembl/03-molecule-spec.md)               |
| 4   | `chembl_target`                 | ChEMBL           | target                 | [Spec](chembl/04-target-spec.md)                 |
| 5   | `chembl_activity`               | ChEMBL           | activity               | [Spec](chembl/05-activity-spec.md)               |
| 6   | `chembl_assay`                  | ChEMBL           | assay                  | [Spec](chembl/06-assay-spec.md)                  |
| 7   | `chembl_publication`            | ChEMBL           | document               | [Spec](chembl/07-publication-spec.md)            |
| 8   | `chembl_assay_parameters`       | ChEMBL           | assay_parameters       | [Spec](chembl/08-assay-parameters-spec.md)       |
| 9   | `chembl_compound_record`        | ChEMBL           | compound_record        | [Spec](chembl/09-compound-record-spec.md)        |
| 10  | `chembl_target_component`       | ChEMBL           | target_component       | [Spec](chembl/10-target-component-spec.md)       |
| 11  | `chembl_publication_term`       | ChEMBL           | publication_term       | [Spec](chembl/11-publication-term-spec.md)       |
| 12  | `chembl_publication_similarity` | ChEMBL           | publication_similarity | [Spec](chembl/12-publication-similarity-spec.md) |
| 13  | `chembl_subcellular_fraction`   | ChEMBL           | subcellular_fraction   | [Spec](chembl/13-subcellular-fraction-spec.md)   |
| 14  | `chembl_tissue`                 | ChEMBL           | tissue                 | [Spec](chembl/14-tissue-spec.md)                 |
| 15  | `uniprot_protein`               | UniProt          | protein                | [Spec](uniprot/01-protein-spec.md)               |
| 16  | `uniprot_idmapping`             | UniProt          | idmapping              | [Spec](uniprot/02-idmapping-spec.md)             |
| 17  | `pubchem_compound`              | PubChem          | compound               | [Spec](pubchem/01-compound-spec.md)              |
| 18  | `pubmed_publication`            | PubMed           | publication            | [Spec](pubmed/01-publication-spec.md)            |
| 19  | `crossref_publication`          | CrossRef         | publication            | [Spec](crossref/01-publication-spec.md)          |
| 20  | `openalex_publication`          | OpenAlex         | publication            | [Spec](openalex/01-publication-spec.md)          |
| 21  | `semanticscholar_publication`   | Semantic Scholar | publication            | [Spec](semanticscholar/01-publication-spec.md)   |

### Composite Pipelines (5)

| #   | Pipeline ID             | Provider  | Entity      | Spec                                     |
| --- | ----------------------- | --------- | ----------- | ---------------------------------------- |
| 22  | `composite_activity`    | Composite | activity    | [Spec](composite/01-activity-spec.md)    |
| 23  | `composite_assay`       | Composite | assay       | [Spec](composite/02-assay-spec.md)       |
| 24  | `composite_molecule`    | Composite | molecule    | [Spec](composite/03-molecule-spec.md)    |
| 25  | `composite_publication` | Composite | publication | [Spec](composite/04-publication-spec.md) |
| 26  | `composite_target`      | Composite | target      | [Spec](composite/05-target-spec.md)      |

______________________________________________________________________

## Provider Summary

| Provider             | Pipelines | Rate Limit                 | Auth               |
| -------------------- | --------- | -------------------------- | ------------------ |
| **ChEMBL**           | 14        | 3 req/sec                  | Public             |
| **UniProt**          | 2         | 100 req/sec                | API Key (optional) |
| **PubChem**          | 1         | 5 req/sec                  | Public             |
| **PubMed**           | 1         | 3 req/sec (10 with key)    | API Key            |
| **CrossRef**         | 1         | Polite pool                | mailto header      |
| **OpenAlex**         | 1         | ~10 req/sec                | email-based        |
| **Semantic Scholar** | 1         | 0.1 req/sec (1.0 with key) | API Key            |
| **Composite**        | 5         | N/A (local merge)          | N/A                |

______________________________________________________________________

## Documentation Structure

Each pipeline specification includes:

1. **Identification** - API endpoints, libraries, rate limits
1. **Business Context** - Purpose, use cases, relationships
1. **Extraction (Bronze)** - Complete API fields, nested structures
1. **Transformation** - Normalization rules, flattening strategy
1. **Validation** - Schema and DQ thresholds
1. **Output Schemas** - Bronze/Silver/Gold structure
1. **Dependencies** - Upstream/downstream, cross-provider mapping
1. **Configuration** - YAML pipeline config
1. **Testing** - Required test coverage

______________________________________________________________________

## Cross-Provider ID Mapping

| ID Type       | ChEMBL                         | UniProt      | PubChem     | PubMed | CrossRef | OpenAlex | S2     |
| ------------- | ------------------------------ | ------------ | ----------- | ------ | -------- | -------- | ------ |
| **InChI Key** | `structure_standard_inchi_key` | -            | `inchi_key` | -      | -        | -        | -      |
| **DOI**       | `document.doi`                 | -            | -           | `doi`  | `DOI`    | `doi`    | `doi`  |
| **PubMed ID** | `document.pubmed_id`           | -            | -           | `pmid` | -        | -        | `pmid` |
| **UniProt**   | `target_component.accession`   | `accession`  | -           | -      | -        | -        | -      |
| **ChEMBL**    | ID                             | `chembl_ids` | -           | -      | -        | -        | -      |

______________________________________________________________________

## Schema Files

Provider schemas live in `src/bioetl/domain/schemas/` and Gold contracts in `src/bioetl/domain/contracts/gold/`.
JSON contract exports are in `docs/contracts/gold/`.

______________________________________________________________________

## Configuration Files

All pipeline configs are in `configs/pipelines/`:

```
configs/pipelines/
- chembl/
  - activity.yaml
  - assay.yaml
  - assay_parameters.yaml
  - cell_line.yaml
  - compound_record.yaml
  - molecule.yaml
  - protein_class.yaml
  - publication.yaml
  - publication_similarity.yaml
  - publication_term.yaml
  - subcellular_fraction.yaml
  - target.yaml
  - target_component.yaml
  - tissue.yaml
- composite/
  - activity.yaml
  - assay.yaml
  - molecule.yaml
  - publication.yaml
  - target.yaml
- crossref/
  - publication.yaml
- openalex/
  - publication.yaml
- pubchem/
  - compound.yaml
- pubmed/
  - publication.yaml
- semanticscholar/
  - publication.yaml
- uniprot/
  - idmapping.yaml
  - protein.yaml
```

______________________________________________________________________

______________________________________________________________________

## Canonical PK Migration Matrix

| Pipeline                  | Old PK                                                                            | New PK                                                   | Breaking                     | Migration Strategy                                                                                 |
| ------------------------- | --------------------------------------------------------------------------------- | -------------------------------------------------------- | ---------------------------- | -------------------------------------------------------------------------------------------------- |
| `chembl_publication`      | `document_chembl_id`                                                              | `publication_id`                                         | Yes (public contract rename) | Add `publication_id` → backfill from `document_chembl_id` → dual-write → drop legacy in next major |
| `chembl_publication_term` | `document_chembl_id`                                                              | `publication_id`                                         | Yes                          | Add `publication_id` → backfill from `document_chembl_id` → dual-write → drop legacy in next major |
| `chembl_target`           | `target_chembl_id`                                                                | `target_id`                                              | Yes                          | Add `target_id` → backfill from `target_chembl_id` → dual-write → drop legacy in next major        |
| `chembl_target_component` | `target_chembl_id`                                                                | `target_id`                                              | Yes                          | Add `target_id` → backfill from `target_chembl_id` → dual-write → drop legacy in next major        |
| `chembl_molecule`         | `molecule_chembl_id`                                                              | `molecule_id`                                            | Yes                          | Add `molecule_id` → backfill from `molecule_chembl_id` → dual-write → drop legacy in next major    |
| `chembl_activity`         | `molecule_chembl_id`, `target_chembl_id`, `assay_chembl_id`, `document_chembl_id` | `molecule_id`, `target_id`, `assay_id`, `publication_id` | Yes                          | Add canonical columns → backfill from legacy IDs → dual-write → drop legacy in next major          |
| `chembl_assay`            | `assay_chembl_id`, `target_chembl_id`, `document_chembl_id`, `cell_chembl_id`     | `assay_id`, `target_id`, `publication_id`, `cell_id`     | Yes                          | Add canonical columns → backfill from legacy IDs → dual-write → drop legacy in next major          |
| `chembl_assay_parameters` | `assay_chembl_id`                                                                 | `assay_id`                                               | Yes                          | Add `assay_id` → backfill from `assay_chembl_id` → dual-write → drop legacy in next major          |
| `chembl_cell_line`        | `cell_chembl_id`                                                                  | `cell_id`                                                | Yes                          | Add `cell_id` → backfill from `cell_chembl_id` → dual-write → drop legacy in next major            |
| `chembl_compound_record`  | `molecule_chembl_id`, `document_chembl_id`                                        | `molecule_id`, `publication_id`                          | Yes                          | Add canonical columns → backfill from legacy IDs → dual-write → drop legacy in next major          |
| `uniprot_idmapping`       | `target_chembl_id`                                                                | `target_id`                                              | Yes                          | Add `target_id` → backfill from `target_chembl_id` → dual-write → drop legacy in next major        |

## Related Documentation

- [RULES.md](../RULES.md) - Project governance

- [CLAUDE.md](../../CLAUDE.md) - Agent instructions

- [ADR Directory](../02-architecture/decisions/) - Architecture Decision Records

- [API Reference](../04-reference/api/) - API documentation

- Composite: activity, assay
