# BioETL Pipeline Documentation

*Updated: 2026-02-17 | Aligned with RULES.md v5.20*

This directory contains documentation for all BioETL pipelines, including composite pipelines.

----------------------------------------------------------------------

## Pipeline Index

### Provider Pipelines (21)

| #   | Pipeline ID                     | Provider         | Entity                 | Spec                                             |
| --- | ------------------------------- | ---------------- | ---------------------- | ------------------------------------------------ |
| 1   | `chembl-protein-class`          | ChEMBL           | protein-class          | [Spec](chembl/01-protein-class-spec.md)          |
| 2   | `chembl-cell-line`              | ChEMBL           | cell-line              | [Spec](chembl/02-cell-line-spec.md)              |
| 3   | `chembl-molecule`               | ChEMBL           | molecule               | [Spec](chembl/03-molecule-spec.md)               |
| 4   | `chembl-target`                 | ChEMBL           | target                 | [Spec](chembl/04-target-spec.md)                 |
| 5   | `chembl-activity`               | ChEMBL           | activity               | [Spec](chembl/05-activity-spec.md)               |
| 6   | `chembl-assay`                  | ChEMBL           | assay                  | [Spec](chembl/06-assay-spec.md)                  |
| 7   | `chembl-publication`            | ChEMBL           | document               | [Spec](chembl/07-publication-spec.md)            |
| 8   | `chembl-assay-parameters`       | ChEMBL           | assay-parameters       | [Spec](chembl/08-assay-parameters-spec.md)       |
| 9   | `chembl-compound-record`        | ChEMBL           | compound-record        | [Spec](chembl/09-compound-record-spec.md)        |
| 10  | `chembl-target-component`       | ChEMBL           | target-component       | [Spec](chembl/10-target-component-spec.md)       |
| 11  | `chembl-publication-term`       | ChEMBL           | publication-term       | [Spec](chembl/11-publication-term-spec.md)       |
| 12  | `chembl-publication-similarity` | ChEMBL           | publication-similarity | [Spec](chembl/12-publication-similarity-spec.md) |
| 13  | `chembl-subcellular-fraction`   | ChEMBL           | subcellular-fraction   | [Spec](chembl/14-subcellular-fraction-spec.md)   |
| 14  | `chembl-tissue`                 | ChEMBL           | tissue                 | [Spec](chembl/15-tissue-spec.md)                 |
| 15  | `uniprot-protein`               | UniProt          | protein                | [Spec](uniprot/01-protein-spec.md)               |
| 16  | `uniprot-idmapping`             | UniProt          | idmapping              | [Spec](uniprot/02-idmapping-spec.md)             |
| 17  | `pubchem-compound`              | PubChem          | compound               | [Spec](pubchem/01-compound-spec.md)              |
| 18  | `pubmed-publication`            | PubMed           | publication            | [Spec](pubmed/01-publication-spec.md)            |
| 19  | `crossref-publication`          | CrossRef         | publication            | [Spec](crossref/01-publication-spec.md)          |
| 20  | `openalex-publication`          | OpenAlex         | publication            | [Spec](openalex/01-publication-spec.md)          |
| 21  | `semanticscholar-publication`   | Semantic Scholar | publication            | [Spec](semanticscholar/01-publication-spec.md)   |

### Composite Pipelines (5)

| #   | Pipeline ID             | Provider  | Entity      | Spec                                     |
| --- | ----------------------- | --------- | ----------- | ---------------------------------------- |
| 22  | `composite-publication` | Composite | publication | [Spec](composite/01-publication-spec.md) |
| 23  | `composite-molecule`    | Composite | molecule    | [Spec](composite/02-molecule-spec.md)    |
| 24  | `composite-target`      | Composite | target      | [Spec](composite/03-target-spec.md)      |
| 25  | `composite-activity`    | Composite | activity    | *Spec pending*                           |
| 26  | `composite-assay`       | Composite | assay       | *Spec pending*                           |

----------------------------------------------------------------------

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

----------------------------------------------------------------------

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

----------------------------------------------------------------------

## Cross-Provider ID Mapping

| ID Type       | ChEMBL                         | UniProt      | PubChem     | PubMed | CrossRef | OpenAlex | S2     |
| ------------- | ------------------------------ | ------------ | ----------- | ------ | -------- | -------- | ------ |
| **InChI Key** | `structure-standard-inchi-key` | -            | `inchi-key` | -      | -        | -        | -      |
| **DOI**       | `document.doi`                 | -            | -           | `doi`  | `DOI`    | `doi`    | `doi`  |
| **PubMed ID** | `document.pubmed-id`           | -            | -           | `pmid` | -        | -        | `pmid` |
| **UniProt**   | `target-component.accession`   | `accession`  | -           | -      | -        | -        | -      |
| **ChEMBL**    | ID                             | `chembl-ids` | -           | -      | -        | -        | -      |

----------------------------------------------------------------------

## Schema Files

Each provider pipeline references an explicit schema config via `schema-file` in `configs/pipelines/*/*.yaml`.

| Pipeline config                                        | Schema config                                        |
| ------------------------------------------------------ | ---------------------------------------------------- |
| `configs/pipelines/chembl/activity.yaml`               | `configs/schemas/chembl/activity.yaml`               |
| `configs/pipelines/chembl/assay.yaml`                  | `configs/schemas/chembl/assay.yaml`                  |
| `configs/pipelines/chembl/assay-parameters.yaml`       | `configs/schemas/chembl/assay-parameters.yaml`       |
| `configs/pipelines/chembl/cell-line.yaml`              | `configs/schemas/chembl/cell-line.yaml`              |
| `configs/pipelines/chembl/compound-record.yaml`        | `configs/schemas/chembl/compound-record.yaml`        |
| `configs/pipelines/chembl/molecule.yaml`               | `configs/schemas/chembl/molecule.yaml`               |
| `configs/pipelines/chembl/protein-class.yaml`          | `configs/schemas/chembl/protein-class.yaml`          |
| `configs/pipelines/chembl/publication.yaml`            | `configs/schemas/chembl/publication.yaml`            |
| `configs/pipelines/chembl/publication-similarity.yaml` | `configs/schemas/chembl/publication-similarity.yaml` |
| `configs/pipelines/chembl/publication-term.yaml`       | `configs/schemas/chembl/publication-term.yaml`       |
| `configs/pipelines/chembl/subcellular-fraction.yaml`   | `configs/schemas/chembl/subcellular-fraction.yaml`   |
| `configs/pipelines/chembl/target.yaml`                 | `configs/schemas/chembl/target.yaml`                 |
| `configs/pipelines/chembl/target-component.yaml`       | `configs/schemas/chembl/target-component.yaml`       |
| `configs/pipelines/chembl/tissue.yaml`                 | `configs/schemas/chembl/tissue.yaml`                 |
| `configs/pipelines/crossref/publication.yaml`          | `configs/schemas/crossref/publication.yaml`          |
| `configs/pipelines/openalex/publication.yaml`          | `configs/schemas/openalex/publication.yaml`          |
| `configs/pipelines/pubchem/compound.yaml`              | `configs/schemas/pubchem/compound.yaml`              |
| `configs/pipelines/pubmed/publication.yaml`            | `configs/schemas/pubmed/publication.yaml`            |
| `configs/pipelines/semanticscholar/publication.yaml`   | `configs/schemas/semanticscholar/publication.yaml`   |
| `configs/pipelines/uniprot/idmapping.yaml`             | `configs/schemas/uniprot/idmapping.yaml`             |
| `configs/pipelines/uniprot/protein.yaml`               | `configs/schemas/uniprot/protein.yaml`               |

Domain schema contracts remain in `src/bioetl/domain/schemas/` and Gold contracts in `src/bioetl/domain/contracts/gold/`.
JSON contract exports are in `docs/contracts/gold/`.

----------------------------------------------------------------------

## Configuration Files

All pipeline configs are in `configs/pipelines/`:

```
configs/pipelines/
- chembl/
  - activity.yaml
  - assay.yaml
  - assay-parameters.yaml
  - cell-line.yaml
  - compound-record.yaml
  - molecule.yaml
  - protein-class.yaml
  - publication.yaml
  - publication-similarity.yaml
  - publication-term.yaml
  - subcellular-fraction.yaml
  - target.yaml
  - target-component.yaml
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

----------------------------------------------------------------------

## Related Documentation

- [RULES.md](../../00-project/RULES.md) - Project governance
- [ADR-025: Pipeline Config Unification](../../02-architecture/decisions/ADR-025-pipeline-config-unification.md)
- [ADR-026: Composite Pipeline Pattern](../../02-architecture/decisions/ADR-026-composite-pipeline-pattern.md)
- [ADR-027: DQ Rules Externalization](../../02-architecture/decisions/ADR-027-dq-rules-externalization.md)
- [ADR-028: Filter Rules Externalization](../../02-architecture/decisions/ADR-028-filter-rules-externalization.md)
- [Pipeline Configuration Guide](../../03-guides/pipeline-configuration.md)
- [DQ Configuration Guide](../../03-guides/dq-configuration.md)
