# BioETL Glossary (Ubiquitous Language)

*Version 2.0 | Updated: 2026-01-06 | Created: 2025-12-29*

This glossary defines the canonical terminology used throughout BioETL. Following Domain-Driven Design principles, these terms form the **Ubiquitous Language** — a shared vocabulary understood by both developers and domain experts.

---

## Quick Reference

### Core Domain Terms

| Canonical Term | Provider Variation | Domain Entity | Description |
|----------------|-------------------|---------------|-------------|
| **Activity** | ChEMBL: Activity | `Activity` | Bioactivity measurement |
| **Molecule** | ChEMBL: Molecule, PubChem: Compound | `Molecule`, `PubchemMolecule` | Chemical compound |
| **Target** | ChEMBL: Target, UniProt: Protein | `Target`, `UniprotTarget` | Biological target |
| **Publication** | PubMed: Publication, ChEMBL: Document, CrossRef: Publication | `Publication`, `ChemblPublication` | Scientific document |

> **v2.0 Migration Notes:**
> - `Compound` → `PubchemMolecule` (deprecated alias retained)
> - `Document` → `ChemblPublication` (deprecated alias retained)
> - `Protein` → `UniprotTarget` (deprecated alias retained)

### Operations Terms

| Canonical Term | Description |
|----------------|-------------|
| **Health Check** | System component availability verification |
| **Anomaly** | Detected deviation from baseline |
| **Alert** | Notification from anomaly detection |
| **Quarantine** | Isolation of failed records |
| **Circuit Breaker** | Cascading failure prevention pattern |

---

## Entity Terminology

### Chemical Compounds

| Canonical Term | Definition | Provider-Specific Names | Domain Entity | Avoid |
|----------------|------------|------------------------|---------------|-------|
| **Molecule** | A chemical entity that can be characterized by a molecular structure (small molecule, peptide, antibody, etc.) | ChEMBL: `Molecule` (API endpoint `/molecule`), **PubChem: `PubchemMolecule`** | `Molecule`, `PubchemMolecule` | `drug`, `substance`, `ligand` (in general context) |

> **Migration Note (v2.0)**: PubChem `Compound` entity renamed to `PubchemMolecule`.
> The deprecated `Compound` alias remains for backward compatibility.

**Note**: ChEMBL uses `Molecule` and PubChem uses `PubchemMolecule` as canonical domain entity names:
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

| Canonical Term | Definition | Provider-Specific Names | Domain Entity | Avoid |
|----------------|------------|------------------------|---------------|-------|
| **Target** | A biological entity (protein, complex, organism) that is the subject of activity measurement | ChEMBL: `Target`, **UniProt: `UniprotTarget`** | `Target`, `UniprotTarget` | `receptor`, `gene` (in target context) |
| **Target Component** | A molecular component of a multi-component target | ChEMBL: `TargetComponent` | `TargetComponent` | `subunit` |

> **Migration Note (v2.0)**: UniProt `Protein` entity renamed to `UniprotTarget`.
> The deprecated `Protein` alias remains for backward compatibility.

### Publications

| Canonical Term | Definition | Provider-Specific Names | Domain Entity | Avoid |
|----------------|------------|------------------------|---------------|-------|
| **Publication** | A scientific document (article, patent, etc.) | PubMed: `Publication`, CrossRef: `PublicationEntity`, **ChEMBL: `ChemblPublication`** | `Publication`, `ChemblPublication`, `PublicationEntity` | `paper`, `article` (as class names), `Work` (deprecated CrossRef API term) |

> **Migration Note (v2.0)**: ChEMBL `Document` entity renamed to `ChemblPublication`.
> The deprecated `Document` alias remains for backward compatibility.

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

### CLI Conventions

**Pipeline Names**: CLI uses `{provider}_{entity}` format for pipeline identifiers:
- `chembl_molecule`, `chembl_activity`, `chembl_assay`
- `pubchem_compound`
- `uniprot_protein`
- `pubmed_publications`

**Language Policy**: All CLI help texts, error messages, and user-facing output use **English** for consistency and international accessibility. Internal documentation (CLAUDE.md, RULES.md) may use Russian per project convention.

**Entity Terms in CLI**: Use provider-specific terms as defined in this glossary:
- ChEMBL pipelines use `molecule`, `activity`, `target`, etc.
- PubChem pipelines use `compound`
- Avoid generic terms like `testitem`, `drug`, `substance` in pipeline names

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

## Operations & Monitoring Terminology

### Health Checks

| Canonical Term | Definition | Avoid |
|----------------|------------|-------|
| **Health Check** | Periodic verification of system component availability | `ping`, `status check` |
| **Liveness Probe** | Check that a process is running (Kubernetes-compatible) | `alive check` |
| **Readiness Probe** | Check that a service is ready to accept traffic | `ready check` |
| **Health Status** | One of: `HEALTHY`, `DEGRADED`, `UNHEALTHY` | `up/down`, `ok/error` |
| **Health Server** | HTTP server exposing health endpoints | `status server` |

### Anomaly Detection

| Canonical Term | Definition | Avoid |
|----------------|------------|-------|
| **Anomaly** | A detected deviation from baseline behavior | `outlier`, `exception` (in data context) |
| **Baseline** | Historical reference values for comparison | `history`, `average` |
| **Z-Score** | Number of standard deviations from mean | `sigma`, `deviation` |
| **Threshold** | Configurable limit for anomaly detection | `limit`, `bound` |
| **Anomaly Severity** | One of: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` | Custom severity names |
| **Anomaly Type** | One of: `SPIKE`, `DROP`, `THRESHOLD_EXCEEDED`, `TREND_CHANGE` | Generic descriptions |

### Alerting

| Canonical Term | Definition | Avoid |
|----------------|------------|-------|
| **Alert** | Notification generated from an anomaly | `warning`, `notification` (as class names) |
| **Alert Channel** | Destination for alert delivery (logger, webhook) | `notifier`, `sender` |
| **Alert Rule** | Configuration for when/how to send alerts | `trigger`, `condition` |
| **Alert Severity** | One of: `INFO`, `WARNING`, `ERROR`, `CRITICAL` | Custom severity names |
| **Cooldown** | Minimum time between repeated alerts | `debounce`, `throttle` |
| **Webhook** | HTTP endpoint for receiving alert payloads | `callback`, `hook` |

### Metrics & Observability

| Canonical Term | Definition | Avoid |
|----------------|------------|-------|
| **Metrics Port** | Interface for recording metrics | `MetricsClient` |
| **Logger Port** | Interface for structured logging | `LoggerClient` |
| **Tracing Port** | Interface for distributed tracing | `TracerClient` |
| **Span** | A unit of work in distributed tracing | `trace`, `segment` |
| **Counter** | Monotonically increasing metric | `incrementer` |
| **Histogram** | Distribution of values over time | `timing`, `duration` |
| **Gauge** | Point-in-time value metric | `level`, `current` |

---

## Resilience & Error Handling Terminology

### Circuit Breaker

| Canonical Term | Definition | Avoid |
|----------------|------------|-------|
| **Circuit Breaker** | Pattern to prevent cascading failures | `failsafe`, `breaker` |
| **Circuit State** | One of: `CLOSED`, `OPEN`, `HALF_OPEN` | Custom state names |
| **Trip** | Circuit breaker opening due to failures | `break`, `trigger` |
| **Recovery** | Circuit breaker closing after successful probes | `reset`, `heal` |
| **Failure Threshold** | Consecutive errors before circuit opens | `trip_count` |

### Error Recovery

| Canonical Term | Definition | Avoid |
|----------------|------------|-------|
| **Retry** | Re-attempting a failed operation | `repeat`, `redo` |
| **Backoff** | Increasing delay between retries | `delay`, `wait` |
| **Jitter** | Random variation in backoff timing | `randomization` |
| **Checkpoint** | Saved state for resumable execution | `savepoint`, `marker` |
| **Recovery Dashboard** | CLI interface for error inspection/recovery | `error console` |

### Locking

| Canonical Term | Definition | Avoid |
|----------------|------------|-------|
| **Lock** | Mutual exclusion mechanism for resources | `mutex`, `semaphore` |
| **Lock Port** | Interface for lock acquisition/release | `LockClient` |
| **TTL** | Time-to-live for automatic lock expiration | `timeout`, `expiry` |
| **Heartbeat** | Periodic lock renewal signal | `keepalive`, `refresh` |
| **Owner ID** | Identifier of lock holder | `holder`, `client_id` |

---

## Security Terminology

| Canonical Term | Definition | Avoid |
|----------------|------------|-------|
| **Secret** | Sensitive configuration value (API key, password) | `credential`, `token` (as generic terms) |
| **Secret Scanning** | Detection of accidentally committed secrets | `credential scanning` |
| **Allowlist** | Approved patterns/files exempt from checks | `whitelist` (deprecated) |
| **Baseline** | Known-good secrets for incremental scanning | `snapshot` |
| **Sanitization** | Removal of secrets from VCR cassettes | `redaction`, `masking` |

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
| `Document` | `ChemblPublication` | ChEMBL API term → Ubiquitous Language (v2.0) |
| `DocumentSchema` | `ChemblPublicationSchema` | ChEMBL schema naming (v2.0) |
| `Compound` | `PubchemMolecule` | PubChem API term → Ubiquitous Language (v2.0) |
| `CompoundSchema` | `PubchemMoleculeSchema` | PubChem schema naming (v2.0) |
| `Protein` | `UniprotTarget` | UniProt API term → Ubiquitous Language (v2.0) |
| `ProteinSchema` | `UniprotTargetSchema` | UniProt schema naming (v2.0) |

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
