# BioETL Pipeline Documentation

*Generated: 2026-01-13 | Aligned with RULES.md v5.14*

This directory contains comprehensive documentation for all 17 BioETL pipelines.

---

## Pipeline Index

### Batch 1 — Reference Tables

| # | Pipeline ID | Provider | Entity | Spec |
|---|-------------|----------|--------|------|
| 1 | `chembl_protein_class` | ChEMBL | protein_class | [Spec](chembl/01-protein-class-spec.md) |
| 2 | `chembl_cell_line` | ChEMBL | cell_line | [Spec](chembl/02-cell-line-spec.md) |

### Batch 2 — Base Entities

| # | Pipeline ID | Provider | Entity | Spec |
|---|-------------|----------|--------|------|
| 3 | `chembl_molecule` | ChEMBL | molecule | [Spec](chembl/03-molecule-spec.md) |
| 4 | `chembl_target` | ChEMBL | target | [Spec](chembl/04-target-spec.md) |
| 5 | `chembl_target_component` | ChEMBL | target_component | [Spec](chembl/10-target-component-spec.md) |
| 6 | `uniprot_protein` | UniProt | protein | [Spec](uniprot/01-protein-spec.md) |
| 7 | `pubchem_compound` | PubChem | compound | [Spec](pubchem/01-compound-spec.md) |

### Batch 3 — Publications

| # | Pipeline ID | Provider | Entity | Spec |
|---|-------------|----------|--------|------|
| 8 | `chembl_publication` | ChEMBL | document | [Spec](chembl/07-publication-spec.md) |
| 9 | `pubmed_publication` | PubMed | publication | [Spec](pubmed/01-publication-spec.md) |
| 10 | `crossref_publication` | CrossRef | publication | [Spec](crossref/01-publication-spec.md) |
| 11 | `openalex_publication` | OpenAlex | publication | [Spec](openalex/01-publication-spec.md) |
| 12 | `semanticscholar_publication` | Semantic Scholar | publication | [Spec](semanticscholar/01-publication-spec.md) |

### Batch 4 — Experiments

| # | Pipeline ID | Provider | Entity | Spec |
|---|-------------|----------|--------|------|
| 13 | `chembl_assay` | ChEMBL | assay | [Spec](chembl/06-assay-spec.md) |
| 14 | `chembl_assay_parameters` | ChEMBL | assay_parameters | [Spec](chembl/08-assay-parameters-spec.md) |
| 15 | `chembl_compound_record` | ChEMBL | compound_record | [Spec](chembl/09-compound-record-spec.md) |

### Batch 5 — Measurements & Mappings

| # | Pipeline ID | Provider | Entity | Spec |
|---|-------------|----------|--------|------|
| 16 | `chembl_activity` | ChEMBL | activity | [Spec](chembl/05-activity-spec.md) |
| 17 | `uniprot_idmapping` | UniProt | idmapping | [Spec](uniprot/02-idmapping-spec.md) |

---

## Provider Summary

| Provider | Pipelines | Rate Limit | Auth |
|----------|-----------|------------|------|
| **ChEMBL** | 10 | None | Public |
| **UniProt** | 2 | 100 req/sec | API Key (optional) |
| **PubChem** | 1 | 5 req/sec | Public |
| **PubMed** | 1 | 3 req/sec (10 with key) | API Key |
| **CrossRef** | 1 | 50 req/sec (polite) | mailto header |
| **OpenAlex** | 1 | 10 req/sec | email-based |
| **Semantic Scholar** | 1 | 100 req/5min | API Key |

---

## Documentation Structure

Each pipeline specification includes:

1. **Identification** — API endpoints, libraries, rate limits
2. **Business Context** — Purpose, use cases, relationships
3. **Extraction (Bronze)** — Complete API fields, nested structures
4. **Transformation** — Normalization rules, flattening strategy
5. **Validation** — Pandera schema, DQ thresholds
6. **Output Schemas** — Bronze/Silver/Gold structure
7. **Dependencies** — Upstream/downstream, cross-provider mapping
8. **Configuration** — YAML pipeline config
9. **Testing** — Required test coverage

---

## Cross-Provider ID Mapping

| ID Type | ChEMBL | UniProt | PubChem | PubMed | CrossRef | OpenAlex | S2 |
|---------|--------|---------|---------|--------|----------|----------|-----|
| **InChI Key** | `structure_standard_inchi_key` | - | `inchi_key` | - | - | - | - |
| **DOI** | `document.doi` | - | - | `doi` | `DOI` | `doi` | `doi` |
| **PubMed ID** | `document.pubmed_id` | - | - | `pmid` | - | - | `pmid` |
| **UniProt** | `target_component.accession` | `accession` | - | - | - | - | - |
| **ChEMBL** | ID | `chembl_ids` | - | - | - | - | - |

---

## Schema Files

All Pandera schemas are located in `src/bioetl/domain/schemas/`:

```
schemas/
├── base.py                    # ETLRecordSchema base class
├── chembl/
│   ├── activity.py
│   ├── assay.py
│   ├── assay_parameters.py
│   ├── cell_line.py
│   ├── compound_record.py
│   ├── molecule.py
│   ├── protein_classification.py
│   ├── publication.py
│   ├── target.py
│   └── target_component.py
├── uniprot/
│   ├── protein.py
│   └── isoform.py
├── pubchem/
│   └── compound.py
├── pubmed/
│   └── article.py
├── crossref/
│   └── publication.py
├── openalex/
│   └── publication.py
└── semanticscholar/
    └── publication.py
```

---

## Configuration Files

All pipeline configs are in `configs/pipelines/`:

```
pipelines/
├── _base.yaml                 # Base template
├── _defaults.yaml             # Default parameters
├── _providers/
│   ├── chembl.yaml
│   ├── crossref.yaml
│   ├── openalex.yaml
│   ├── pubchem.yaml
│   ├── pubmed.yaml
│   ├── semanticscholar.yaml
│   └── uniprot.yaml
├── chembl/
│   ├── activity.yaml
│   ├── assay.yaml
│   ├── assay_parameters.yaml
│   ├── cell_line.yaml
│   ├── compound_record.yaml
│   ├── molecule.yaml
│   ├── protein_class.yaml
│   ├── publication.yaml
│   ├── target.yaml
│   └── target_component.yaml
├── crossref/
│   └── publication.yaml
├── openalex/
│   └── publication.yaml
├── pubchem/
│   └── compound.yaml
├── pubmed/
│   └── publications.yaml
├── semanticscholar/
│   └── publication.yaml
└── uniprot/
    ├── idmapping.yaml
    └── protein.yaml
```

---

## Related Documentation

- [RULES.md](../RULES.md) — Project constitution
- [CLAUDE.md](../../CLAUDE.md) — Agent instructions
- [ADR Directory](../02-architecture/decisions/) — Architecture Decision Records
- [API Reference](../04-reference/api/) — API documentation
