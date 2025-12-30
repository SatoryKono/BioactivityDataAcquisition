# BioETL Glossary (Ubiquitous Language)

*Version 1.0 | Created: 2025-12-29*

This glossary defines the canonical terminology used throughout BioETL. Following Domain-Driven Design principles, these terms form the **Ubiquitous Language** — a shared vocabulary understood by both developers and domain experts.

---

## Quick Reference

| Canonical Term | Provider Variation | Description |
|----------------|-------------------|-------------|
| **Activity** | ChEMBL: Activity | Bioactivity measurement |
| **Molecule** | ChEMBL: Molecule, PubChem: Compound | Chemical compound |
| **Target** | ChEMBL: Target, UniProt: Protein | Biological target |
| **Publication** | PubMed: Publication, ChEMBL: Document, CrossRef: Publication | Scientific document |

---

## Entity Terminology

### Chemical Compounds

| Canonical Term | Definition | Provider-Specific Names | Avoid |
|----------------|------------|------------------------|-------|
| **Molecule** | A chemical entity that can be characterized by a molecular structure (small molecule, peptide, antibody, etc.) | ChEMBL: `Molecule` (API endpoint `/molecule`) | `drug`, `substance`, `ligand` (in general context) |
| **Compound** | PubChem-specific term for chemical entities. Interchangeable with Molecule. | PubChem: `Compound` (CID-based) | Mixing with ChEMBL context |

**Note**: Both `Molecule` (ChEMBL) and `Compound` (PubChem) are correct within their respective provider contexts. The distinction reflects the source terminology:
- ChEMBL API returns `molecule_chembl_id`
- PubChem API returns `cid` (Compound ID)

### Bioactivity Data

| Canonical Term | Definition | Provider-Specific Names | Avoid |
|----------------|------------|------------------------|-------|
| **Activity** | A quantitative measurement of biological activity (e.g., IC50, EC50, Ki) | ChEMBL: `Activity` | `measurement`, `data_point`, `result` |
| **Assay** | An experimental protocol used to measure activity | ChEMBL: `Assay` | `experiment`, `test`, `study` |
| **Standard Value** | The normalized activity value in standard units | ChEMBL: `standard_value` | `value`, `result` |
| **pChEMBL Value** | Potency metric: -log10 of molar activity value | ChEMBL: `pchembl_value` | `potency`, `logIC50` |

### Biological Targets

| Canonical Term | Definition | Provider-Specific Names | Avoid |
|----------------|------------|------------------------|-------|
| **Target** | A biological entity (protein, complex, organism) that is the subject of activity measurement | ChEMBL: `Target` | `receptor`, `gene` (in target context) |
| **Protein** | A specific protein sequence from UniProt | UniProt: `Protein` | `gene_product` |
| **Target Component** | A molecular component of a multi-component target | ChEMBL: `TargetComponent` | `subunit` |

### Publications

| Canonical Term | Definition | Provider-Specific Names | Avoid |
|----------------|------------|------------------------|-------|
| **Publication** | A scientific document (article, patent, etc.) | PubMed: `Publication`, CrossRef: `PublicationEntity` | `paper`, `article` (as class names), `Work` (deprecated CrossRef API term) |
| **Document** | ChEMBL's representation of a source document | ChEMBL: `Document` | `reference`, `source` |

**Note**: CrossRef's API uses the term "Work" but our codebase uses "Publication" as the canonical term for Ubiquitous Language. The deprecated alias `Work` is kept for backward compatibility.

---

## ETL Process Terminology

### Pipeline Execution

| Canonical Term | Definition | Avoid |
|----------------|------------|-------|
| **Pipeline** | A complete data processing sequence from extraction to loading | `workflow`, `job`, `flow` |
| **Stage** | A discrete phase of pipeline execution (extract, transform, validate, load) | `step`, `phase` (as generic terms) |
| **Run** | A single execution instance of a pipeline, identified by `run_id` | `execution`, `instance` |
| **Run Type** | The mode of pipeline execution: `INCREMENTAL`, `BACKFILL`, `REBUILD` | `mode` |

### Batch Processing

| Canonical Term | Definition | Avoid |
|----------------|------------|-------|
| **Batch** | A collection of records processed together as a unit | `chunk`, `partition` |
| **Record** | A single data item within a batch | `entry` (for batch items), `row` |
| **Batch ID** | Unique identifier for a batch within a run | `chunk_id` |

### Data Layers (Medallion Architecture)

| Canonical Term | Definition | Avoid |
|----------------|------------|-------|
| **Bronze** | Raw data layer (JSONL + zstd compression) | `raw`, `landing` |
| **Silver** | Normalized and deduplicated data layer (Delta Lake) | `cleansed`, `curated` |
| **Gold** | Refined and validated data layer for analytics | `reporting`, `presentation` |

---

## Data Quality Terminology

| Canonical Term | Definition | Avoid |
|----------------|------------|-------|
| **Validation** | Checking data against schema rules | `check`, `verification` (as nouns) |
| **Quarantine** | Isolation of records that failed validation | `reject`, `dead_letter`, `error_log` |
| **Quarantine Entry** | A single quarantined record with error metadata | `quarantine_record` (class name) |
| **Schema** | Structure definition for data validation | `model` (when referring to schema) |
| **Schema Drift** | Detection of changes in source data structure | `schema_change`, `schema_evolution` |

---

## Identifier Terminology

| Canonical Term | Definition | Format | Avoid |
|----------------|------------|--------|-------|
| **Entity ID** | Business identifier from the source system | Provider-specific (e.g., `CHEMBL25`) | `business_key`, `natural_key` |
| **Content Hash** | SHA256 hash for record deduplication | `sha256(provider + canonical_json)` | `checksum`, `version_id` |
| **Run ID** | UUID identifying a pipeline run | `UUID` | `execution_id`, `job_id` |
| **Batch ID** | UUID identifying a batch within a run | `UUID` | `chunk_id` |

---

## Component Terminology

### Application Layer

| Canonical Term | Definition | Avoid |
|----------------|------------|-------|
| **Transformer** | Converts Bronze records to Silver/Gold format | `Converter`, `Mapper` (as class names) |
| **Pipeline Runner** | Orchestrates pipeline execution | `Executor`, `Controller` |
| **Service** | Cross-cutting concern handler (e.g., `PreflightService`) | `Helper`, `Utility` |
| **Manager** | Resource-specific handler (e.g., `LockManager`) | `Controller` |

### Infrastructure Layer

| Canonical Term | Definition | Avoid |
|----------------|------------|-------|
| **Adapter** | Implementation of a Port for external systems | `Client` (as standalone), `Connector` |
| **Writer** | Persists data to a Medallion layer | `Saver`, `Persister` |
| **Port** | Protocol interface defining capabilities | `Interface` (Python reserved) |

### Naming Patterns

| Pattern | Example | Usage |
|---------|---------|-------|
| `{Entity}Transformer` | `ActivityTransformer`, `MoleculeTransformer` | Bronze → Silver transformation |
| `{Provider}{Entity}Transformer` | `PubChemCompoundTransformer` | Cross-provider distinction |
| `{Layer}Writer` | `BronzeWriter`, `GoldWriter` | Data persistence |
| `{Provider}Adapter` | `ChemblAdapter`, `UniProtAdapter` | External API access |
| `{Resource}Manager` | `LockManager`, `CheckpointManager` | Resource lifecycle |
| `{Concern}Service` | `PreflightService`, `PostrunService` | Cross-cutting operations |

---

## Provider-Specific Terminology

### ChEMBL

| Term | API Endpoint | Description |
|------|-------------|-------------|
| `Molecule` | `/molecule` | Chemical compound |
| `Activity` | `/activity` | Bioactivity measurement |
| `Assay` | `/assay` | Experimental protocol |
| `Target` | `/target` | Biological target |
| `Document` | `/document` | Publication reference |
| `CellLine` | `/cell_line` | Cell line for assays |
| `TargetComponent` | `/target_component` | Target subunit |
| `CompoundRecord` | `/compound_record` | Molecule-document link |

### PubChem

| Term | API Resource | Description |
|------|-------------|-------------|
| `Compound` | PUG REST `/compound` | Chemical entity (by CID) |

### UniProt

| Term | API Endpoint | Description |
|------|-------------|-------------|
| `Protein` | REST API | Protein sequence and annotations |

### PubMed

| Term | API | Description |
|------|-----|-------------|
| `Publication` | E-utilities | Article metadata |

### CrossRef

| Term | API Endpoint | Description |
|------|-------------|-------------|
| `Publication` | `/works` | Scholarly publication metadata (API uses "works", codebase uses "publication") |

---

## Deprecated Terms

These terms should NOT be used in new code:

| Deprecated Term | Canonical Term | Reason |
|-----------------|----------------|--------|
| `workflow` | `pipeline` | Consistency with codebase |
| `job` | `run` | Clarity |
| `chunk` | `batch` | Domain alignment |
| `measurement` | `activity` | ChEMBL terminology |
| `data_point` | `record` | Generic term |
| `Loader` | `Adapter` (for input), `Writer` (for output) | Vague technical term |
| `Handler` | Specific name (e.g., `Manager`, `Service`) | Vague technical term |
| `Work` | `Publication` | CrossRef API term → Ubiquitous Language |
| `WorkSchema` | `PublicationSchema` | CrossRef schema naming |
| `CrossRefWorkRecord` | `CrossRefPublicationRecord` | CrossRef model naming |

---

## Terminology Enforcement

### Lint Script

A terminology linter is available at `scripts/lint_terminology.py`:

```bash
# Check for deprecated terms
python scripts/lint_terminology.py src/bioetl/

# Pre-commit hook (see .pre-commit-config.yaml)
```

### Verification Commands

```bash
# Find usages of deprecated terms
grep -ri "\bworkflow\b" src/bioetl/ --include="*.py"
grep -ri "\bmeasurement\b" src/bioetl/ --include="*.py" | grep -v "measurements.py"
grep -ri "class.*Loader\|class.*Handler" src/bioetl/ --include="*.py"
```

---

## References

- **ChEMBL Documentation**: https://www.ebi.ac.uk/chembl/api/data/docs
- **PubChem Documentation**: https://pubchemdocs.ncbi.nlm.nih.gov/
- **UniProt Documentation**: https://www.uniprot.org/help/api
- **DDD Ubiquitous Language**: Eric Evans, Domain-Driven Design (2003)

---

*See also: [RULES.md](RULES.md) §2.4.1 for pipeline naming conventions.*
