# BioETL Pipeline Documentation

*Updated: 2026-02-04 | Aligned with RULES.md v5.17*

This directory contains documentation for all BioETL pipelines, including composite pipelines.

---

## Pipeline Index

### Provider Pipelines (19)

| # | Pipeline ID | Provider | Entity | Spec |
|---|-------------|----------|--------|------|
| 1 | `chembl_protein_class` | ChEMBL | protein_class | [Spec](chembl/01-protein-class-spec.md) |
| 2 | `chembl_cell_line` | ChEMBL | cell_line | [Spec](chembl/02-cell-line-spec.md) |
| 3 | `chembl_molecule` | ChEMBL | molecule | [Spec](chembl/03-molecule-spec.md) |
| 4 | `chembl_target` | ChEMBL | target | [Spec](chembl/04-target-spec.md) |
| 5 | `chembl_activity` | ChEMBL | activity | [Spec](chembl/05-activity-spec.md) |
| 6 | `chembl_assay` | ChEMBL | assay | [Spec](chembl/06-assay-spec.md) |
| 7 | `chembl_publication` | ChEMBL | document | [Spec](chembl/07-publication-spec.md) |
| 8 | `chembl_assay_parameters` | ChEMBL | assay_parameters | [Spec](chembl/08-assay-parameters-spec.md) |
| 9 | `chembl_compound_record` | ChEMBL | compound_record | [Spec](chembl/09-compound-record-spec.md) |
| 10 | `chembl_target_component` | ChEMBL | target_component | [Spec](chembl/10-target-component-spec.md) |
| 11 | `chembl_publication_term` | ChEMBL | publication_term | [Spec](chembl/11-publication-term-spec.md) |
| 12 | `chembl_publication_similarity` | ChEMBL | publication_similarity | [Spec](chembl/12-publication-similarity-spec.md) |
| 13 | `uniprot_protein` | UniProt | protein | [Spec](uniprot/01-protein-spec.md) |
| 14 | `uniprot_idmapping` | UniProt | idmapping | [Spec](uniprot/02-idmapping-spec.md) |
| 15 | `pubchem_compound` | PubChem | compound | [Spec](pubchem/01-compound-spec.md) |
| 16 | `pubmed_publication` | PubMed | publication | [Spec](pubmed/01-publication-spec.md) |
| 17 | `crossref_publication` | CrossRef | publication | [Spec](crossref/01-publication-spec.md) |
| 18 | `openalex_publication` | OpenAlex | publication | [Spec](openalex/01-publication-spec.md) |
| 19 | `semanticscholar_publication` | Semantic Scholar | publication | [Spec](semanticscholar/01-publication-spec.md) |

### Composite Pipelines (3)

| # | Pipeline ID | Provider | Entity | Spec |
|---|-------------|----------|--------|------|
| 20 | `composite_publication` | Composite | publication | [Spec](composite/01-publication-spec.md) |
| 21 | `composite_molecule` | Composite | molecule | [Spec](composite/02-molecule-spec.md) |
| 22 | `composite_target` | Composite | target | [Spec](composite/03-target-spec.md) |

---

## Provider Summary

| Provider | Pipelines | Rate Limit | Auth |
|----------|-----------|------------|------|
| **ChEMBL** | 12 | None | Public |
| **UniProt** | 2 | 100 req/sec | API Key (optional) |
| **PubChem** | 1 | 5 req/sec | Public |
| **PubMed** | 1 | 3 req/sec (10 with key) | API Key |
| **CrossRef** | 1 | Polite pool | mailto header |
| **OpenAlex** | 1 | ~10 req/sec | email-based |
| **Semantic Scholar** | 1 | 100 req/5min | API Key |
| **Composite** | 3 | N/A (local merge) | N/A |

---

## Documentation Structure

Each pipeline specification includes:

1. **Identification** - API endpoints, libraries, rate limits
2. **Business Context** - Purpose, use cases, relationships
3. **Extraction (Bronze)** - Complete API fields, nested structures
4. **Transformation** - Normalization rules, flattening strategy
5. **Validation** - Schema and DQ thresholds
6. **Output Schemas** - Bronze/Silver/Gold structure
7. **Dependencies** - Upstream/downstream, cross-provider mapping
8. **Configuration** - YAML pipeline config
9. **Testing** - Required test coverage

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

Provider schemas live in `src/bioetl/domain/schemas/` and Gold contracts in `src/bioetl/domain/contracts/gold/`.
JSON contract exports are in `docs/contracts/gold/`.

---

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
  - target.yaml
  - target_component.yaml
- composite/
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

---

## Related Documentation

- [RULES.md](../RULES.md) - Project governance
- [CLAUDE.md](../../CLAUDE.md) - Agent instructions
- [ADR Directory](../02-architecture/decisions/) - Architecture Decision Records
- [API Reference](../04-reference/api/) - API documentation
