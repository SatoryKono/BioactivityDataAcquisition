______________________________________________________________________

Version: 1.0.1
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# BioETL Glossary (Ubiquitous Language)

*Version 2.7.1 | Updated: 2026-04-29 | Created: 2025-12-29*

This glossary defines the canonical terminology used throughout BioETL. Following Domain-Driven Design principles, these terms form the **Ubiquitous Language** — a shared vocabulary understood by both developers and domain experts.

______________________________________________________________________

## Quick Reference

### Core Domain Terms

| Canonical Term  | Provider Variation                                           | Domain Entity                      | Description             |
| --------------- | ------------------------------------------------------------ | ---------------------------------- | ----------------------- |
| **Activity**    | ChEMBL: Activity                                             | `Activity`                         | Bioactivity measurement |
| **Molecule**    | ChEMBL: Molecule, PubChem: Compound                          | `Molecule`, `PubchemMolecule`      | Chemical compound       |
| **Target**      | ChEMBL: Target, UniProt: Protein                             | `Target`, `UniprotTarget`          | Biological target       |
| **Publication** | PubMed: Publication, ChEMBL: Document, CrossRef: Publication | `Publication`, `ChemblPublication` | Scientific document     |

> **v2.0 Migration Notes:**
>
> - ~~`Compound`~~ → `PubchemMolecule` (migration complete, old name removed)
> - ~~`Document`~~ → `ChemblPublication` (migration complete, old name removed)
> - ~~`Protein`~~ → `UniprotTarget` (migration complete, old name removed)
>
> **Note:** Deprecated aliases were removed. Use only the new names.

### Operations Terms

| Canonical Term      | Description                                         |
| ------------------- | --------------------------------------------------- |
| **Health Check**    | System component availability verification          |
| **Anomaly**         | Detected deviation from baseline                    |
| **Alert**           | Notification from anomaly detection                 |
| **Quarantine**      | Isolation of failed records                         |
| **Circuit Breaker** | Cascading failure prevention pattern                |
| **DQ**              | Data Quality — валидация и контроль качества данных |

______________________________________________________________________

## Entity Terminology

### Chemical Compounds

| Canonical Term | Definition                                                                                                     | Provider-Specific Names                                                       | Domain Entity                 | Avoid                                              |
| -------------- | -------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ----------------------------- | -------------------------------------------------- |
| **Molecule**   | A chemical entity that can be characterized by a molecular structure (small molecule, peptide, antibody, etc.) | ChEMBL: `Molecule` (API endpoint `/molecule`), **PubChem: `PubchemMolecule`** | `Molecule`, `PubchemMolecule` | `drug`, `substance`, `ligand` (in general context) |

> **Migration Note (v2.0)**: PubChem `Compound` entity renamed to `PubchemMolecule`.
> Migration complete — deprecated `Compound` alias removed.

**Note**: ChEMBL uses `Molecule` and PubChem uses `PubchemMolecule` as canonical domain entity names:

- ChEMBL API returns `molecule-chembl-id`
- PubChem API returns `cid` (Compound ID)

### Bioactivity Data

| Canonical Term     | Definition                                                               | Provider-Specific Names  | Avoid                                 |
| ------------------ | ------------------------------------------------------------------------ | ------------------------ | ------------------------------------- |
| **Activity**       | A quantitative measurement of biological activity (e.g., IC50, EC50, Ki) | ChEMBL: `Activity`       | `measurement`, `data-point`, `result` |
| **Assay**          | An experimental protocol used to measure activity                        | ChEMBL: `Assay`          | `experiment`, `test`, `study`         |
| **Standard Value** | The normalized activity value in standard units                          | ChEMBL: `standard-value` | `value`, `result`                     |
| **pChEMBL Value**  | Potency metric: -log10 of molar activity value                           | ChEMBL: `pchembl-value`  | `potency`, `logIC50`                  |

### Biological Targets

| Canonical Term       | Definition                                                                                   | Provider-Specific Names                        | Domain Entity             | Avoid                                  |
| -------------------- | -------------------------------------------------------------------------------------------- | ---------------------------------------------- | ------------------------- | -------------------------------------- |
| **Target**           | A biological entity (protein, complex, organism) that is the subject of activity measurement | ChEMBL: `Target`, **UniProt: `UniprotTarget`** | `Target`, `UniprotTarget` | `receptor`, `gene` (in target context) |
| **Target Component** | A molecular component of a multi-component target                                            | ChEMBL: `TargetComponent`                      | `TargetComponent`         | `subunit`                              |

> **Migration Note (v2.0)**: UniProt `Protein` entity renamed to `UniprotTarget`.
> Migration complete — deprecated `Protein` alias removed.

### Publications

| Canonical Term  | Definition                                    | Provider-Specific Names                                                               | Domain Entity                                           | Avoid                                                                      |
| --------------- | --------------------------------------------- | ------------------------------------------------------------------------------------- | ------------------------------------------------------- | -------------------------------------------------------------------------- |
| **Publication** | A scientific document (article, patent, etc.) | PubMed: `Publication`, CrossRef: `PublicationEntity`, **ChEMBL: `ChemblPublication`** | `Publication`, `ChemblPublication`, `PublicationEntity` | `paper`, `article` (as class names), `Work` (deprecated CrossRef API term) |

> **Migration Note (v2.0)**: ChEMBL `Document` entity renamed to `ChemblPublication`.
> Migration complete — deprecated `Document` alias removed.

**Note**: CrossRef's API uses the term "Work" but our codebase uses "Publication" as the canonical term for Ubiquitous Language. The deprecated alias `Work` is kept for backward compatibility.

______________________________________________________________________

## ETL Process Terminology

### Pipeline Execution

| Canonical Term             | Definition                                                                                                                                                 | Avoid                                                  |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| **Pipeline**               | A complete data processing sequence from extraction to loading                                                                                             | `workflow`, `job`, `flow`                              |
| **Stage**                  | A discrete phase of pipeline execution (extract, transform, validate, load)                                                                                | `step`, `phase` (as generic terms)                     |
| **Run**                    | A single execution instance of a pipeline, identified by `run-id`                                                                                          | `execution`, `instance`                                |
| **Run Type**               | The mode of pipeline execution: `INCREMENTAL`, `BACKFILL`, `REBUILD`                                                                                       | `mode`                                                 |
| **Loading Strategy**       | Enum defining pipeline loading behavior: `FULL-SCAN-ONLY`, `WATERMARK-BASED` (ADR-031)                                                                     | `force-full-scan` (deprecated boolean)                 |
| **Entity Config**          | Unified YAML config combining pipeline, DQ, filter, schema, and enum settings for a single entity in `configs/entities/{provider}/{entity}.yaml` (ADR-039) | `pipeline config` (when referring to the unified file) |
| **Provider Source Config** | Provider-level API settings in `configs/providers/{provider}.yaml` (ADR-039)                                                                               | `source config`                                        |
| **Composite Config**       | Multi-source pipeline config in `configs/composites/{entity}.yaml` (ADR-039)                                                                               | `composite pipeline config`                            |

### Pipeline Execution Enums

| Canonical Term      | Definition                                                | Values                                             | Avoid                  |
| ------------------- | --------------------------------------------------------- | -------------------------------------------------- | ---------------------- |
| **RunType**         | Enum controlling pipeline execution mode and clear policy | `INCREMENTAL`, `BACKFILL`, `REBUILD`               | `mode` (as enum name)  |
| **SilverWriteMode** | Enum controlling Silver layer write strategy              | `MERGE`, `APPEND`, `DELETE`                        | `write mode` (generic) |
| **GoldWriteMode**   | Enum controlling Gold layer write strategy                | `APPEND`, `OVERWRITE`, `SCD2`                      | `write mode` (generic) |
| **HealthStatus**    | Enum representing component availability                  | `HEALTHY`, `DEGRADED`, `UNHEALTHY`                 | `status` (generic)     |
| **FSMState**        | Enum representing pipeline finite-state-machine states    | `IDLE`, `RUNNING`, `PAUSED`, `FAILED`, `COMPLETED` | `state` (generic)      |

> **Owner-doc note:** glossary is a summary surface. Canonical Medallion
> write-mode policy lives in `docs/00-project/RULES.md` §2.1.1-§2.1.2, with
> runtime enum source in `src/bioetl/domain/medallion.py`.

### Pipeline Context & Identity

| Canonical Term                  | Definition                                                                                                                                         | Avoid                                                      |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| **BatchID**                     | UUID uniquely identifying a batch within a pipeline run                                                                                            | `chunk-id`, `batch number`                                 |
| **ContentHash**                 | SHA-256 hash for record deduplication: `sha256(provider + canonical_json(record))`                                                                 | `checksum`, `fingerprint`                                  |
| **PipelineRunContext**          | Launch/execution descriptor used during runtime assembly before a runner starts; carries launch options, resume flags, and identity/config anchors | `global run manifest`, `runtime payload object`            |
| **PipelineContext**             | Immutable in-run processing context carrying `run_id`, `run_type`, `LoggerPort`, and deterministic `started_at` for batch/write flows              | `run state`, `infra context object`                        |
| **RunManifest (control-plane)** | Immutable provenance/control-plane artifact describing what was launched and with which reproducibility anchors                                    | `universal runtime context`, `one manifest for everything` |
| **RunLedger (control-plane)**   | Append-only event ledger linked to a run/manifest for provenance, diagnostics, and replay inspection, but not the mutable runtime resume object | `resume state store`, `checkpoint ledger`                  |
| **Control Plane**               | Artifact family around manifests, ledgers, effective config, and related provenance/inspection surfaces                                           | `runtime context`, `execution state`                       |

### Composite Pipeline Services

| Canonical Term                | Definition                                                                                      | Avoid                                |
| ----------------------------- | ----------------------------------------------------------------------------------------------- | ------------------------------------ |
| **CompositeRunner**           | Application service orchestrating seed + enricher pipelines and merge into unified Gold         | `composite executor`, `merge runner` |
| **MedallionLifecycleService** | Application service managing Bronze→Silver→Gold lifecycle transitions with clear/write policies | `lifecycle manager`, `layer service` |

### Batch Processing

| Canonical Term | Definition                                           | Avoid                            |
| -------------- | ---------------------------------------------------- | -------------------------------- |
| **Batch**      | A collection of records processed together as a unit | `chunk`, `partition`             |
| **Record**     | A single data item within a batch                    | `entry` (for batch items), `row` |
| **Batch ID**   | Unique identifier for a batch within a run           | `chunk-id`                       |

### Data Layers (Medallion Architecture)

| Canonical Term         | Definition                                                                                                                                   | Avoid                                    |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| **Bronze**             | Raw data layer (JSONL + zstd compression)                                                                                                    | `raw`, `landing`                         |
| **Silver**             | Normalized and deduplicated data layer (Delta Lake)                                                                                          | `cleansed`, `curated`                    |
| **Gold**               | Refined and validated data layer for analytics                                                                                               | `reporting`, `presentation`              |
| **Delta Lake**         | Open-source ACID storage layer used for Silver and Gold layers. Provides time-travel, schema enforcement, and transactional writes (ADR-001) | `parquet` (for Silver/Gold)              |
| **BaseOutputMetadata** | Unified output metadata contract for all Medallion layers (ADR-029)                                                                          | layer-specific `OutputMetadata` variants |

### Composite Pipelines (ADR-026)

| Canonical Term             | Definition                                                                                                            | Avoid                                  |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------- | -------------------------------------- |
| **Composite Pipeline**     | Multi-source pipeline combining seed + enrichers into unified Gold entity                                             | `merged pipeline`, `combined workflow` |
| **Seed Pipeline**          | Primary pipeline providing base entities for enrichment                                                               | `source pipeline`, `base pipeline`     |
| **Enricher**               | Pipeline that adds supplemental data from external source                                                             | `enhancer`, `augmenter`                |
| **MergeService**           | Application service that joins seed and enricher data                                                                 | historical aliases `Joiner`, `Combiner` |
| **Preserve All Sources**   | MergeConfig flag to keep all provider-qualified columns                                                               | `keep-all-columns`                     |
| **Qualified Column**       | Column name in `{provider}.{entity}.{field}` format                                                                   | `prefixed column`, `namespaced column` |
| **Column Group**           | Semantic grouping of columns for output ordering                                                                      | `field group`                          |
| **Field Group Registry**   | Central registry (`FieldGroupRegistry`) for semantic field grouping, Gold filtering, and column ordering              | `column registry`                      |
| **Field Group Id**         | Enum identifying a semantic group (e.g., `ID-AND-STATUS`, `BIBLIOGRAPHY`, `TRASH`). Alias for `PublicationFieldGroup` | `group type`                           |
| **Field Mapping**          | Frozen dataclass mapping a base field name to its provider-qualified columns and group                                | `column mapping`                       |
| **Field Group Definition** | Frozen dataclass defining a semantic group with display name, Gold inclusion flag, and field mappings                 | `group config`                         |
| **Conflict Resolution**    | Strategy for handling field value conflicts during merge                                                              | `conflict handling`                    |
| **Coalesce**               | Merge strategy taking first non-null value                                                                            | `fill`, `combine`                      |

______________________________________________________________________

## Data Quality Terminology

| Canonical Term            | Definition                                                                                                                | Avoid                                          |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| **Validation**            | Checking data against schema rules                                                                                        | `check`, `verification` (as nouns)             |
| **Quarantine**            | Isolation of records that failed validation                                                                               | `reject`, `dead-letter`, `error-log`           |
| **Quarantine Entry**      | A single quarantined record with error metadata                                                                           | `quarantine-record` (class name)               |
| **Schema**                | Structure definition for data validation                                                                                  | `model` (when referring to schema)             |
| **Schema Drift**          | Detection of changes in source data structure                                                                             | `schema-change`, `schema-evolution`            |
| **Base Validation**       | Level 1: Pandera schema validation (types, regex, nullable)                                                               | `schema validation`, `type checking`           |
| **Structural Validation** | Level 2: Cross-field consistency rules (page ordering, year matching)                                                     | `cross-field validation`, `field dependencies` |
| **External Verification** | Level 3: HTTP-based ID verification with upstream providers                                                               | `API validation`, `ID lookup`                  |
| **Logical Validation**    | Level 4: Range constraints and business invariants                                                                        | `business rules`, `constraint checking`        |
| **Semantic Validation**   | Level 5: NLP-based text consistency checks (similarity, language)                                                         | `text validation`, `NLP checks`                |
| **Pandera**               | DataFrame schema validation library used for Silver and Gold layer contract enforcement (`strict=True` for Gold, ADR-018) | `pydantic` (for DataFrames)                    |
| **DQ Flag**               | Data Quality flag: `-dq-error` (FAIL — blocking), `-dq-warn` (WARN — accepted)                                            | `quality flag`, `error flag`                   |
| **Validation Mode**       | Pipeline execution profile: STRICT, BALANCED, FAST                                                                        | `validation profile`, `quality mode`           |
| **Clean Record**          | Record with `-dq-warn=False` and `-dq-error=False`                                                                        | `valid record`, `passed record`                |
| **Quarantine Record**     | Record with `-dq-warn=True` (non-critical warnings)                                                                       | `warned record`, `flagged record`              |
| **Rejected Record**       | Record with `-dq-error=True` (critical errors, not written to Silver)                                                     | `failed record`, `blocked record`              |
| **Validation Level**      | One of five sequential validation stages (Base → Structural → External → Logical → Semantic)                              | `validation stage`, `check level`              |
| **Validation Result**     | Outcome of validation check: PASS, FAIL, WARN, SKIP, NOT-APPLICABLE                                                       | `check result`, `validation status`            |

______________________________________________________________________

## Identifier Terminology

| Canonical Term   | Definition                                 | Format                               | Avoid                         |
| ---------------- | ------------------------------------------ | ------------------------------------ | ----------------------------- |
| **Entity ID**    | Business identifier from the source system | Provider-specific (e.g., `CHEMBL25`) | `business-key`, `natural-key` |
| **Content Hash** | SHA256 hash for record deduplication       | `sha256(provider + canonical-json)`  | `checksum`, `version-id`      |
| **Run ID**       | UUID identifying a pipeline run            | `UUID`                               | `execution-id`, `job-id`      |
| **Batch ID**     | UUID identifying a batch within a run      | `UUID`                               | `chunk-id`                    |

### Canonical Semantic Field Clusters

| Canonical Field | Legacy / Provider-Native Variants | Scope |
| --------------- | --------------------------------- | ----- |
| `assay_id` | `assay_chembl_id` | ChEMBL assay and downstream composite/activity internal runtime surfaces |
| `molecule_id` | `molecule_chembl_id` | ChEMBL molecule and downstream composite/activity internal runtime surfaces |
| `pmid` | `pubmed_id` | PubMed and composite publication internal runtime surfaces |
| `title` | `pubmed_title`, `openalex_title` | Publication normalization and composite publication join surfaces |
| `doi` | `doi` | Publication identifier surfaces across CrossRef, OpenAlex, PubMed and Semantic Scholar |

Published source of truth:
`docs/04-reference/contracts/canonical-field-registry.md` and
`configs/field_registry/canonical_registry.json`.

______________________________________________________________________

## Component Terminology

### Architectural Patterns

| Canonical Term                | Definition                                                                                                                                                                                                                       | Avoid                                            |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| **Hexagonal Architecture**    | Architecture pattern (Ports & Adapters) where domain logic is isolated from external concerns via Port protocols and Adapter implementations. BioETL uses 5 layers: domain, application, infrastructure, composition, interfaces | `layered architecture`, `onion architecture`     |
| **Dependency Injection (DI)** | Design pattern where dependencies are provided to a class via constructor parameters rather than created internally. All DI wiring happens in the `composition/` layer (ADR-005)                                                 | `service locator`, `factory` (in business logic) |

### Application Layer

| Canonical Term      | Definition                                               | Avoid                                  |
| ------------------- | -------------------------------------------------------- | -------------------------------------- |
| **Transformer**     | Converts Bronze records to Silver/Gold format            | `Converter`, `Mapper` (as class names) |
| **Pipeline Runner** | Orchestrates pipeline execution                          | `Executor`, `Controller`               |
| **Service**         | Cross-cutting concern handler (e.g., `PreflightService`) | `Helper`, `Utility`                    |
| **Manager**         | Resource-specific handler (e.g., `CheckpointManager`)    | `Controller`                           |

### Infrastructure Layer

| Canonical Term     | Definition                                                                                                                              | Avoid                                 |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------- |
| **Adapter**        | Implementation of a Port for external systems                                                                                           | `Client` (as standalone), `Connector` |
| **Writer**         | Persists data to a Medallion layer                                                                                                      | `Saver`, `Persister`                  |
| **Port**           | Protocol interface defining capabilities                                                                                                | `Interface` (Python reserved)         |
| **DataSourcePort** | Core domain port (Protocol) defining the contract for data fetching from external providers. Implemented by provider-specific adapters. | `DataClient`, `FetcherInterface`      |

### Naming Patterns

| Pattern                                    | Example                                      | Usage                                                                               |
| ------------------------------------------ | -------------------------------------------- | ----------------------------------------------------------------------------------- |
| `{Entity}Transformer`                      | `ActivityTransformer`, `MoleculeTransformer` | Bronze → Silver transformation                                                      |
| `{Provider}{EntitySurfaceTerm}Transformer` | `PubChemCompoundTransformer`                 | Public pipeline surface; may intentionally differ from canonical domain entity name |
| `{Layer}Writer`                            | `BronzeWriter`, `GoldWriter`                 | Data persistence                                                                    |
| `{Provider}Adapter`                        | `ChemblAdapter`, `UniProtAdapter`            | External API access                                                                 |
| `{Resource}Manager`                        | `CheckpointManager`                          | Resource lifecycle                                                                  |
| `{Concern}Service`                         | `PreflightService`, `PostrunService`         | Cross-cutting operations                                                            |

### CLI Conventions

**Pipeline Names**: CLI uses `{provider}_{entity}` format for pipeline identifiers:

- `chembl_molecule`, `chembl_activity`, `chembl_assay`
- `pubchem_compound`
- `uniprot_protein`
- `pubmed_publication`

These pipeline IDs are **stable external identifiers**. They may intentionally
preserve provider API terms even when the canonical domain entity name differs.
Examples:

- Domain: `PubchemMolecule` → CLI/config/public pipeline ID: `pubchem_compound`
- Domain: `UniprotTarget` → CLI/config/public pipeline ID: `uniprot_protein`

**Language Policy**: All CLI help texts, error messages, and user-facing output use **English** for consistency and international accessibility. Internal documentation (CLAUDE.md, RULES.md) may use Russian per project convention.

**Entity Terms in CLI**: Use provider-specific terms as defined in this glossary:

- ChEMBL pipelines use `molecule`, `activity`, `target`, etc.
- PubChem pipelines use `compound`
- UniProt pipelines use `protein`
- Avoid generic terms like `testitem`, `drug`, `substance` in pipeline names

______________________________________________________________________

## Provider-Specific Terminology

### ChEMBL

| Term              | API Endpoint        | Description             |
| ----------------- | ------------------- | ----------------------- |
| `Molecule`        | `/molecule`         | Chemical compound       |
| `Activity`        | `/activity`         | Bioactivity measurement |
| `Assay`           | `/assay`            | Experimental protocol   |
| `Target`          | `/target`           | Biological target       |
| `Document`        | `/document`         | Publication reference   |
| `CellLine`        | `/cell-line`        | Cell line for assays    |
| `TargetComponent` | `/target-component` | Target subunit          |
| `CompoundRecord`  | `/compound-record`  | Molecule-document link  |

### PubChem

| Term       | API Resource         | Description              |
| ---------- | -------------------- | ------------------------ |
| `Compound` | PUG REST `/compound` | Chemical entity (by CID) |

### UniProt

| Term      | API Endpoint | Description                      |
| --------- | ------------ | -------------------------------- |
| `Protein` | REST API     | Protein sequence and annotations |

### PubMed

| Term          | API         | Description      |
| ------------- | ----------- | ---------------- |
| `Publication` | E-utilities | Article metadata |

### CrossRef

| Term          | API Endpoint | Description                                                                    |
| ------------- | ------------ | ------------------------------------------------------------------------------ |
| `Publication` | `/works`     | Scholarly publication metadata (API uses "works", codebase uses "publication") |

______________________________________________________________________

## Operations & Monitoring Terminology

### Health Checks

| Canonical Term      | Definition                                              | Avoid                  |
| ------------------- | ------------------------------------------------------- | ---------------------- |
| **Health Check**    | Periodic verification of system component availability  | `ping`, `status check` |
| **Liveness Probe**  | Check that a process is running (Kubernetes-compatible) | `alive check`          |
| **Readiness Probe** | Check that a service is ready to accept traffic         | `ready check`          |
| **Health Status**   | One of: `HEALTHY`, `DEGRADED`, `UNHEALTHY`              | `up/down`, `ok/error`  |
| **Health Server**   | HTTP server exposing health endpoints                   | `status server`        |

### Anomaly Detection

| Canonical Term       | Definition                                                    | Avoid                                    |
| -------------------- | ------------------------------------------------------------- | ---------------------------------------- |
| **Anomaly**          | A detected deviation from baseline behavior                   | `outlier`, `exception` (in data context) |
| **Baseline**         | Historical reference values for comparison                    | `history`, `average`                     |
| **Z-Score**          | Number of standard deviations from mean                       | `sigma`, `deviation`                     |
| **Threshold**        | Configurable limit for anomaly detection                      | `limit`, `bound`                         |
| **Anomaly Severity** | One of: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`                   | Custom severity names                    |
| **Anomaly Type**     | One of: `SPIKE`, `DROP`, `THRESHOLD-EXCEEDED`, `TREND-CHANGE` | Generic descriptions                     |

### Alerting

| Canonical Term     | Definition                                       | Avoid                                      |
| ------------------ | ------------------------------------------------ | ------------------------------------------ |
| **Alert**          | Notification generated from an anomaly           | `warning`, `notification` (as class names) |
| **Alert Channel**  | Destination for alert delivery (logger, webhook) | `notifier`, `sender`                       |
| **Alert Rule**     | Configuration for when/how to send alerts        | `trigger`, `condition`                     |
| **Alert Severity** | One of: `INFO`, `WARNING`, `ERROR`, `CRITICAL`   | Custom severity names                      |
| **Cooldown**       | Minimum time between repeated alerts             | `debounce`, `throttle`                     |
| **Webhook**        | HTTP endpoint for receiving alert payloads       | `callback`, `hook`                         |

### Metrics & Observability

| Canonical Term   | Definition                            | Avoid                |
| ---------------- | ------------------------------------- | -------------------- |
| **Metrics Port** | Interface for recording metrics       | `MetricsClient`      |
| **Logger Port**  | Interface for structured logging      | `LoggerClient`       |
| **Tracing Port** | Interface for distributed tracing     | `TracerClient`       |
| **Span**         | A unit of work in distributed tracing | `trace`, `segment`   |
| **Counter**      | Monotonically increasing metric       | `incrementer`        |
| **Histogram**    | Distribution of values over time      | `timing`, `duration` |
| **Gauge**        | Point-in-time value metric            | `level`, `current`   |

______________________________________________________________________

## Resilience & Error Handling Terminology

### Circuit Breaker

| Canonical Term        | Definition                                      | Avoid                 |
| --------------------- | ----------------------------------------------- | --------------------- |
| **Circuit Breaker**   | Pattern to prevent cascading failures           | `failsafe`, `breaker` |
| **Circuit State**     | One of: `CLOSED`, `OPEN`, `HALF-OPEN`           | Custom state names    |
| **Trip**              | Circuit breaker opening due to failures         | `break`, `trigger`    |
| **Recovery**          | Circuit breaker closing after successful probes | `reset`, `heal`       |
| **Failure Threshold** | Consecutive errors before circuit opens         | `trip-count`          |

### Error Recovery

| Canonical Term         | Definition                                  | Avoid                 |
| ---------------------- | ------------------------------------------- | --------------------- |
| **Retry**              | Re-attempting a failed operation            | `repeat`, `redo`      |
| **Backoff**            | Increasing delay between retries            | `delay`, `wait`       |
| **Jitter**             | Random variation in backoff timing          | `randomization`       |
| **Checkpoint**         | Saved state for resumable execution         | `savepoint`, `marker` |
| **Recovery Dashboard** | CLI interface for error inspection/recovery | `error console`       |

### Locking

| Canonical Term | Definition                                 | Avoid                  |
| -------------- | ------------------------------------------ | ---------------------- |
| **Lock**       | Mutual exclusion mechanism for resources   | `mutex`, `semaphore`   |
| **Lock Port**  | Interface for lock acquisition/release     | `LockClient`           |
| **TTL**        | Time-to-live for automatic lock expiration | `timeout`, `expiry`    |
| **Heartbeat**  | Periodic lock renewal signal               | `keepalive`, `refresh` |
| **Owner ID**   | Identifier of lock holder                  | `holder`, `client-id`  |

______________________________________________________________________

## Testing Terminology

| Canonical Term | Definition                                                                                                                                                                                                  | Avoid                             |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------- |
| **VCR**        | Video Cassette Recorder pattern — library (VCR.py) that records HTTP interactions as YAML cassettes for deterministic replay in tests. Cassettes stored in `tests/fixtures/vcr/{provider}/` (RULES.md §4.2) | `mock HTTP`, `recorded responses` |
| **Cassette**   | A YAML file containing recorded HTTP request-response pairs for VCR replay                                                                                                                                  | `fixture`, `recording`            |

______________________________________________________________________

## Security Terminology

| Canonical Term      | Definition                                        | Avoid                                    |
| ------------------- | ------------------------------------------------- | ---------------------------------------- |
| **Secret**          | Sensitive configuration value (API key, password) | `credential`, `token` (as generic terms) |
| **Secret Scanning** | Detection of accidentally committed secrets       | `credential scanning`                    |
| **Allowlist**       | Approved patterns/files exempt from checks        | `whitelist` (deprecated)                 |
| **Baseline**        | Known-good secrets for incremental scanning       | `snapshot`                               |
| **Sanitization**    | Removal of secrets from VCR cassettes             | `redaction`, `masking`                   |

______________________________________________________________________

## Deprecated Terms

These terms should NOT be used in new code:

| Deprecated Term      | Canonical Term                               | Reason                                        |
| -------------------- | -------------------------------------------- | --------------------------------------------- |
| `workflow`           | `pipeline`                                   | Consistency with codebase                     |
| `job`                | `run`                                        | Clarity                                       |
| `chunk`              | `batch`                                      | Domain alignment                              |
| `measurement`        | `activity`                                   | ChEMBL terminology                            |
| `data-point`         | `record`                                     | Generic term                                  |
| `Loader`             | `Adapter` (for input), `Writer` (for output) | Vague technical term                          |
| `Handler`            | Specific name (e.g., `Manager`, `Service`)   | Vague technical term                          |
| `Work`               | `Publication`                                | CrossRef API term → Ubiquitous Language       |
| `WorkSchema`         | `PublicationSchema`                          | CrossRef schema naming                        |
| `CrossRefWorkRecord` | `CrossRefPublicationRecord`                  | CrossRef model naming                         |
| `Document`           | `ChemblPublication`                          | ChEMBL API term → Ubiquitous Language (v2.0)  |
| `DocumentSchema`     | `ChemblPublicationSchema`                    | ChEMBL schema naming (v2.0)                   |
| `Compound`           | `PubchemMolecule`                            | PubChem API term → Ubiquitous Language (v2.0) |
| `CompoundSchema`     | `PubchemMoleculeSchema`                      | PubChem schema naming (v2.0)                  |
| `Protein`            | `UniprotTarget`                              | UniProt API term → Ubiquitous Language (v2.0) |
| `ProteinSchema`      | `UniprotTargetSchema`                        | UniProt schema naming (v2.0)                  |

______________________________________________________________________

## Russian Terminology (Русскоязычные термины)

> **Политика**: Документация на русском языке (RULES.md, AGENT.md, архитектурные документы)
> использует канонические русские термины. Английские термины допустимы для технических
> имён классов, методов и конфигурационных ключей.

### Основные термины

| English Term    | Русский термин  | Примечание                                                                      |
| --------------- | --------------- | ------------------------------------------------------------------------------- |
| **Provider**    | **провайдер**   | НЕ "источник данных" (source). Провайдер — внешний API (ChEMBL, PubChem и т.д.) |
| **Pipeline**    | **пайплайн**    | НЕ "конвейер", НЕ "workflow"                                                    |
| **Entity**      | **сущность**    | Тип данных (Activity, Molecule, Target)                                         |
| **Record**      | **запись**      | Единица данных в батче                                                          |
| **Run**         | **запуск**      | Экземпляр выполнения пайплайна (run-id)                                         |
| **Batch**       | **батч**        | Группа записей для обработки                                                    |
| **Adapter**     | **адаптер**     | Реализация Port для провайдера                                                  |
| **Port**        | **порт**        | Protocol-интерфейс для DI                                                       |
| **Transformer** | **трансформер** | Преобразователь Bronze → Silver/Gold                                            |
| **Writer**      | **writer**      | Компонент записи в Medallion слой                                               |
| **Quarantine**  | **карантин**    | Изоляция невалидных записей                                                     |
| **Checkpoint**  | **чекпоинт**    | Точка сохранения прогресса                                                      |

### Термины Medallion Architecture

| English Term   | Русский термин  | Примечание                              |
| -------------- | --------------- | --------------------------------------- |
| **Bronze**     | **Bronze**      | Сырые данные (не переводится)           |
| **Silver**     | **Silver**      | Нормализованные данные (не переводится) |
| **Gold**       | **Gold**        | Аналитические витрины (не переводится)  |
| **Data Layer** | **слой данных** | Bronze/Silver/Gold уровни               |

### Термины DDD и архитектуры

| English Term       | Русский термин     | Примечание          |
| ------------------ | ------------------ | ------------------- |
| **Domain**         | **домен**          | Слой бизнес-логики  |
| **Application**    | **приложение**     | Слой оркестрации    |
| **Infrastructure** | **инфраструктура** | Слой адаптеров      |
| **Composition**    | **композиция**     | Слой DI/сборки      |
| **Aggregate**      | **агрегат**        | DDD-паттерн         |
| **Value Object**   | **value object**   | Неизменяемый объект |

### Избегать (Deprecated Russian Terms)

| ❌ Избегать     | ✅ Использовать | Причина                                                |
| --------------- | --------------- | ------------------------------------------------------ |
| источник данных | провайдер       | Термин "источник" зарезервирован для `src-id` в ChEMBL |
| конвейер        | пайплайн        | Согласованность с кодовой базой                        |
| задача          | запуск (run)    | Избегать путаницы с job/task                           |
| поток           | пайплайн        | Избегать путаницы с data flow                          |

______________________________________________________________________

## Terminology Enforcement

### Lint Script

A terminology linter is available at `scripts/engineering/qa/lint_terminology.py`:

```bash
# Check for deprecated terms
python scripts/engineering/qa/lint_terminology.py src/bioetl/

# Pre-commit hook (see .pre-commit-config.yaml)
```

### Verification Commands

```bash
# Find usages of deprecated terms
grep -ri "\bworkflow\b" src/bioetl/ --include="*.py"
grep -ri "\bmeasurement\b" src/bioetl/ --include="*.py" | grep -v "measurements.py"
grep -ri "class.*Loader\|class.*Handler" src/bioetl/ --include="*.py"
```

______________________________________________________________________

## References

- **ChEMBL Documentation**: https://www.ebi.ac.uk/chembl/api/data/docs
- **PubChem Documentation**: https://pubchemdocs.ncbi.nlm.nih.gov/
- **UniProt Documentation**: https://www.uniprot.org/help/api
- **DDD Ubiquitous Language**: Eric Evans, Domain-Driven Design (2003)

______________________________________________________________________

*See also: [RULES.md](RULES.md) §2.4.1 for pipeline naming conventions.*
