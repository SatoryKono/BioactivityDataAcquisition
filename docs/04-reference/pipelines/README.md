# BioETL Pipeline Documentation

*Updated: 2026-02-21 | Aligned with RULES.md v5.22*

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
| 7   | `chembl-publication`            | ChEMBL           | publication            | [Spec](chembl/07-publication-spec.md)            |
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
| 25  | `composite-activity`    | Composite | activity    | [Spec](composite/04-activity-spec.md)    |
| 26  | `composite-assay`       | Composite | assay       | [Spec](composite/05-assay-spec.md)       |

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

For standard pipelines, schema definition is stored in the same unified entity file
(`configs/entities/{provider}/{entity}.yaml`, section `schema`).
Composite pipelines keep merge schema in `configs/composites/{entity}.yaml`
(section `composite.merge.column-groups`).

| Pipeline config                                        | Schema config                                        |
| ------------------------------------------------------ | ---------------------------------------------------- |
| `configs/entities/chembl/activity.yaml`               | `schema` section in same file                        |
| `configs/entities/chembl/assay.yaml`                  | `schema` section in same file                        |
| `configs/entities/chembl/assay-parameters.yaml`       | `schema` section in same file                        |
| `configs/entities/chembl/cell-line.yaml`              | `schema` section in same file                        |
| `configs/entities/chembl/compound-record.yaml`        | `schema` section in same file                        |
| `configs/entities/chembl/molecule.yaml`               | `schema` section in same file                        |
| `configs/entities/chembl/protein-class.yaml`          | `schema` section in same file                        |
| `configs/entities/chembl/publication.yaml`            | `schema` section in same file                        |
| `configs/entities/chembl/publication-similarity.yaml` | `schema` section in same file                        |
| `configs/entities/chembl/publication-term.yaml`       | `schema` section in same file                        |
| `configs/entities/chembl/subcellular-fraction.yaml`   | `schema` section in same file                        |
| `configs/entities/chembl/target.yaml`                 | `schema` section in same file                        |
| `configs/entities/chembl/target-component.yaml`       | `schema` section in same file                        |
| `configs/entities/chembl/tissue.yaml`                 | `schema` section in same file                        |
| `configs/entities/crossref/publication.yaml`          | `schema` section in same file                        |
| `configs/entities/openalex/publication.yaml`          | `schema` section in same file                        |
| `configs/entities/pubchem/compound.yaml`              | `schema` section in same file                        |
| `configs/entities/pubmed/publication.yaml`            | `schema` section in same file                        |
| `configs/entities/semanticscholar/publication.yaml`   | `schema` section in same file                        |
| `configs/entities/uniprot/idmapping.yaml`             | `schema` section in same file                        |
| `configs/entities/uniprot/protein.yaml`               | `schema` section in same file                        |

Domain schema contracts remain in `src/bioetl/domain/schemas/` and Gold contracts in `src/bioetl/domain/contracts/gold/`.
JSON contract exports are in `docs/04-reference/contracts/gold/`.

----------------------------------------------------------------------

## Configuration Files

Standard pipeline configs are in `configs/entities/`.
Composite pipeline configs are in `configs/composites/`.

```
configs/
├── entities/
│   ├── chembl/
│   ├── crossref/
│   ├── openalex/
│   ├── pubchem/
│   ├── pubmed/
│   ├── semanticscholar/
│   └── uniprot/
└── composites/
    ├── activity.yaml
    ├── assay.yaml
    ├── molecule.yaml
    ├── publication.yaml
    └── target.yaml
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
