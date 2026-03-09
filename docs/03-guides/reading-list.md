# Curated Reading List

*Updated: 2026-03-09 | For new team members and contributors*

This reading list supports onboarding to BioETL. It is organised by topic
and difficulty. Completing the **Essential** tier gives enough background to
run, debug, and extend pipelines within a typical working day.

> **Tip:** Start with [Getting Started](getting-started.md) to set up your local
> environment first, then come back here for deeper background reading.

---

## Contents

1. [Essential (start here)](#1-essential-start-here)
2. [Architecture & Design Patterns](#2-architecture--design-patterns)
3. [Data Engineering](#3-data-engineering)
4. [Bioactivity & Cheminformatics Domain](#4-bioactivity--cheminformatics-domain)
5. [Python Ecosystem](#5-python-ecosystem)
6. [BioETL-specific Docs](#6-bioetl-specific-docs)

---

## 1. Essential (start here)

These resources are required reading before making any code changes.

### Internal Docs

| Document | Time | What you will learn |
|----------|------|---------------------|
| [Getting Started](getting-started.md) | 30 min | Local environment setup and first pipeline run |
| [Project Rules](../00-project/RULES.md) | 45 min | Governance, architecture constraints, mandatory conventions |
| [Architecture Overview](../02-architecture/00-overview.md) | 20 min | Hexagonal architecture and Medallion layers |
| [Running Pipelines](running-pipelines.md) | 20 min | CLI commands, run types, flags |
| [Glossary](../00-project/glossary.md) | 15 min | Domain terminology (targets, compounds, assays, etc.) |

### External References

| Resource | URL | What you will learn |
|----------|-----|---------------------|
| ChEMBL web interface | https://www.ebi.ac.uk/chembl/ | What data looks like before it enters BioETL |
| PubChem web interface | https://pubchem.ncbi.nlm.nih.gov/ | Chemical compound browsing |
| UniProt entry example | https://www.uniprot.org/uniprotkb/P53_HUMAN | Protein data structure |

---

## 2. Architecture & Design Patterns

### Hexagonal Architecture (Ports & Adapters)

The cornerstone of BioETL's design. Understanding this pattern is essential
before reading any source code.

| Resource | Format | Notes |
|----------|--------|-------|
| *"Hexagonal Architecture"* — Alistair Cockburn (original article) | Article | https://alistair.cockburn.us/hexagonal-architecture/ |
| *"Get Your Hands Dirty on Clean Architecture"* — Tom Hombergs | Book | Concise practical guide; chapters 1–4 are directly applicable |
| BioETL [Domain Layer](../02-architecture/01-domain-layer.md) | Internal doc | How domain ports are defined in this project |
| BioETL [Composition Layer](../02-architecture/05-composition-layer.md) | Internal doc | How adapters are wired together |

### Domain-Driven Design (DDD)

BioETL uses DDD aggregates, value objects, and entities.
See [ADR-021](../02-architecture/decisions/ADR-021-ddd-aggregates-adoption.md).

| Resource | Format | Notes |
|----------|--------|-------|
| *"Domain-Driven Design Distilled"* — Vaughn Vernon | Book | Chapters 1–5 cover aggregates, entities, and value objects |
| DDD Reference (free PDF) — Eric Evans | Book | https://www.domainlanguage.com/ddd/reference/ |

### Medallion Architecture (Bronze / Silver / Gold)

| Resource | Format | Notes |
|----------|--------|-------|
| Databricks Medallion Architecture guide | Article | https://docs.databricks.com/lakehouse/medallion.html |
| BioETL [ADR-002](../02-architecture/decisions/ADR-002-medallion-architecture.md) | ADR | Why BioETL uses this pattern |
| BioETL [Data Layers](../02-architecture/data-layers.md) | Internal doc | Layer-specific rules and storage formats |

### Architecture Decision Records (ADRs)

| Resource | Format | Notes |
|----------|--------|-------|
| ADR format overview — Michael Nygard | Article | https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions |
| BioETL [ADR Index](../02-architecture/decisions/README.md) | Internal doc | All 41 BioETL ADRs |

---

## 3. Data Engineering

### Delta Lake

Delta Lake is the mandatory storage format for Silver and Gold layers
([ADR-001](../02-architecture/decisions/ADR-001-delta-lake-vs-parquet.md)).

| Resource | Format | Notes |
|----------|--------|-------|
| Delta Lake documentation | Docs | https://delta.io/learn/ |
| `delta-rs` Python bindings | Docs | https://delta-io.github.io/delta-rs/ |
| BioETL [ADR-001](../02-architecture/decisions/ADR-001-delta-lake-vs-parquet.md) | ADR | Why Delta Lake over raw Parquet |

### Apache Parquet & Arrow

| Resource | Format | Notes |
|----------|--------|-------|
| Apache Parquet format overview | Docs | https://parquet.apache.org/docs/ |
| PyArrow documentation | Docs | https://arrow.apache.org/docs/python/ |

### Polars

| Resource | Format | Notes |
|----------|--------|-------|
| Polars user guide | Docs | https://docs.pola.rs/user-guide/getting-started/ |
| Polars vs pandas comparison | Article | https://docs.pola.rs/user-guide/migration/pandas/ |

### Data Quality

| Resource | Format | Notes |
|----------|--------|-------|
| Pandera documentation | Docs | https://pandera.readthedocs.io/ |
| BioETL [DQ Configuration](dq-configuration.md) | Internal doc | How DQ rules are defined in YAML |

---

## 4. Bioactivity & Cheminformatics Domain

These resources help you understand what the data *means* — not just how it
flows through the pipeline.

### Core Domain References

| Resource | URL / Info | Notes |
|----------|-----------|-------|
| ChEMBL documentation | https://chembl.gitbook.io/chembl-interface-documentation/ | Data model, API, and field definitions |
| ChEMBL paper (Mendez et al. 2019) | https://doi.org/10.1093/nar/gkz1094 | Peer-reviewed overview of ChEMBL |
| PubChem documentation | https://pubchem.ncbi.nlm.nih.gov/docs/programmatic-access | API and data model |
| UniProt help | https://www.uniprot.org/help | Annotation guidelines and field meanings |
| OpenAlex documentation | https://docs.openalex.org/ | Entity schema and API |
| Semantic Scholar API | https://api.semanticscholar.org/api-docs/ | API reference |

### Key Concepts

| Concept | Brief definition | Where to read more |
|---------|-----------------|-------------------|
| **IC50** | Concentration that inhibits 50 % of biological activity | ChEMBL docs, activity table |
| **pChEMBL** | −log₁₀(IC50 in molar); enables cross-assay comparison | [ADR-002](../02-architecture/decisions/ADR-002-medallion-architecture.md) |
| **InChI / InChI Key** | International Chemical Identifier; `InChI Key` is the hashed 27-char form used as a compound join key | https://iupac.org/who-we-are/divisions/division-details/inchi/ |
| **SMILES** | Line notation for chemical structures (Simplified Molecular-Input Line-Entry System) | https://www.daylight.com/dayhtml/doc/theory/theory.smiles.html |
| **UniProt accession** | Stable protein identifier (e.g. `P53_HUMAN`) | https://www.uniprot.org/help/accession_numbers |
| **DOI** | Digital Object Identifier; the primary join key for cross-provider publication data | https://www.doi.org/ |
| **Assay** | Experimental protocol measuring a biological activity | ChEMBL assay docs |
| **Target** | Biological macromolecule (protein, DNA, etc.) that a compound interacts with | ChEMBL target docs |
| **Medallion** | Three-layer data architecture (Bronze/Silver/Gold) | [ADR-002](../02-architecture/decisions/ADR-002-medallion-architecture.md) |

### Background Papers

| Paper | DOI | Relevance |
|-------|-----|-----------|
| Gaulton et al. *ChEMBL: a large-scale bioactivity database for drug discovery* (2012) | 10.1093/nar/gkr777 | Original ChEMBL description |
| Kim et al. *PubChem in 2021* (2021) | 10.1093/nar/gkaa971 | PubChem scope and data model |
| The UniProt Consortium *UniProt: the universal protein knowledgebase* (2021) | 10.1093/nar/gkaa1100 | UniProt data model |
| Prykhodko et al. *A de novo molecular generation method using latent vector based generative adversarial network* (2019) | 10.1186/s13321-019-0396-x | Background on molecular representations |

---

## 5. Python Ecosystem

### Core Libraries Used in BioETL

| Library | Docs | Purpose in BioETL |
|---------|------|-------------------|
| `httpx` | https://www.python-httpx.org/ | Async HTTP client for all provider APIs |
| `pydantic` v2 | https://docs.pydantic.dev/ | Data models, config validation |
| `polars` | https://docs.pola.rs/ | DataFrame transformations |
| `pandera` | https://pandera.readthedocs.io/ | DataFrame schema validation |
| `deltalake` | https://delta-io.github.io/delta-rs/ | Delta Lake reads/writes |
| `structlog` | https://www.structlog.org/ | Structured logging |
| `click` | https://click.palletsprojects.com/ | CLI framework |

### Testing

| Resource | URL | Notes |
|----------|-----|-------|
| pytest documentation | https://docs.pytest.org/ | Core testing framework |
| VCR.py | https://vcrpy.readthedocs.io/ | HTTP cassette recording for provider tests |
| Hypothesis | https://hypothesis.readthedocs.io/ | Property-based testing |
| BioETL [Testing Guide](testing.md) | Internal doc | Testing conventions and patterns |

### Type Checking

| Resource | URL | Notes |
|----------|-----|-------|
| mypy documentation | https://mypy.readthedocs.io/ | Static type checker (run with `--strict`) |
| PEP 484 (Type Hints) | https://peps.python.org/pep-0484/ | Type system specification |
| PEP 544 (Protocols) | https://peps.python.org/pep-0544/ | Structural subtyping — used extensively for ports |

---

## 6. BioETL-specific Docs

### Must-read internal documents (beyond the Essential tier)

| Document | When to read | Notes |
|----------|-------------|-------|
| [Pipeline Configuration](pipeline-configuration.md) | Before writing YAML | Full YAML config schema reference |
| [Add New Source](add-new-source.md) | When integrating a new provider | Step-by-step guide |
| [Data Dictionary](../04-reference/data-dictionary.md) | When working with field names | All entity schemas |
| [Data Lineage](../04-reference/data-lineage.md) | When debugging field values | Source-to-output tracing |
| [Technology Radar](../02-architecture/technology-radar.md) | Before proposing new libraries | Tool selection rationale |
| [Runbooks Index](../05-operations/runbooks/index.md) | When a pipeline fails | Incident response procedures |
| [REQUIREMENTS.md](../01-requirements/REQUIREMENTS.md) | Before proposing major changes | Formalized requirements with IDs |

### ADRs to read first

Start with these five ADRs to understand the key architectural choices:

| ADR | Title | Why it matters |
|-----|-------|---------------|
| [ADR-001](../02-architecture/decisions/ADR-001-delta-lake-vs-parquet.md) | Delta Lake vs Parquet | Storage layer choice |
| [ADR-002](../02-architecture/decisions/ADR-002-medallion-architecture.md) | Medallion Architecture | Data layer design |
| [ADR-005](../02-architecture/decisions/ADR-005-composition-layer-separation.md) | Composition Layer | Dependency injection wiring |
| [ADR-010](../02-architecture/decisions/ADR-010-local-only-deployment.md) | Local-Only Deployment | Why no external services |
| [ADR-016](../02-architecture/decisions/ADR-016-error-handling-strategy.md) | Error Handling Strategy | How failures are managed |

---

## Quick-Start Learning Path

For new team members, we recommend this sequence:

```
Day 1 (onboarding):
  1. getting-started.md            (30 min) — set up environment, run first pipeline
  2. Architecture overview          (20 min) — understand the layers
  3. Glossary                       (15 min) — learn the domain terminology
  4. Browse ChEMBL web interface    (15 min) — understand what data looks like

Day 2 (going deeper):
  1. RULES.md (§1-3)               (45 min) — architecture constraints
  2. ADR-001, ADR-002, ADR-010     (30 min) — key technology decisions
  3. pipeline-configuration.md     (30 min) — how pipelines are configured
  4. running-pipelines.md          (20 min) — full CLI reference

Week 1:
  - Read remaining Essential-tier docs
  - Complete the "Add Pipeline (Existing Source)" guide
  - Review the testing guide and run the test suite
  - Read ADR-005 and ADR-016 for architecture depth
```
