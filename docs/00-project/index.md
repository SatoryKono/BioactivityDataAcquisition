______________________________________________________________________

Version: 1.2.4
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-08-21'

______________________________________________________________________

# Welcome to BioETL

This is the central documentation hub for the BioETL project.

## Start Here

| Need                                        | Current entry point                                    |
| ------------------------------------------- | ------------------------------------------------------ |
| Current project rules                       | [RULES.md](RULES.md)                                   |
| Active documentation navigator              | [Project Navigator](00-map.md)                         |
| Current tool commands and placement rules   | [Tools Hub](TOOLS.md)                                  |
| Verify published docs and strict build flow | [Docs Verification](../03-guides/docs-verification.md) |
| Historical context only                     | Repository path `docs/99-archive/README.md`            |

Active guidance lives under `docs/00-05`. Materials in `docs/99-archive/`
remain useful for traceability, but they are not normative for current project
behavior.

## Documentation Surface Types

Use the repository docs with the following priority:

- **Canonical active docs**: `docs/00-05`. These pages define current project
  rules, architecture, guides, operations, and reference contracts.
- **Repo-only / extended working docs**: planning, curated evidence, AI runtime
  guidance, and other extended working materials may live outside the published
  MkDocs surface. They remain discoverable through repository-path references,
  but they do not override canonical active docs.
- **Archive docs**: `docs/99-archive/`. Historical context only.

Useful entry points for non-normative surfaces:

- Repository path `docs/plans/README.md` — indexed retained planning artifacts (repo-only working surface, not published in MkDocs)
- Repository path `docs/reports/index.md` — curated repo-only evidence and bounded internal reports
- [File Policy](governance/03-file-policy.md) — structure hygiene, retention boundaries, and sidecar topology
- Repository path `reports/README.md` — generated or working analysis outputs before curation
- Repository path `docs/00-project/ai/README.md` — top-level AI docs map for agents, memory, prompts, and skills
- Repository path `.codex/agents/ORCHESTRATION.md` — Codex source-of-truth orchestration
- Repository path `docs/00-project/ai/agents/README.md` — published agent mirror and runtime guides
- Repository path `docs/00-project/ai/skills/README.md` — skills mirror and indexes
- [Operations Archive Index](../05-operations/archive-index.md) — published archive lane for historical ops evidence and auxiliary deployment notes

## Project Mission

To build a robust, scalable, and maintainable data pipeline for acquiring and processing bioactivity data from various public sources into a unified, analysis-ready format.

## Quick Links

- [**Documentation Index**](00-map.md): Structured navigation for all documentation.
- [**Quick Reference**](rules-summary.md): Key rules at a glance.
- [**Project Navigator**](00-map.md): Full documentation map with links to all resources.
- [**Project Rules**](RULES.md): The constitution of our project (SSOT). All contributions **MUST** adhere to these rules.
- [**Tools Hub**](TOOLS.md): Current script entry points, placement rules, and docs toolchain.
- [**Docs Verification**](../03-guides/docs-verification.md): Published docs checks, drift review, mixed-environment notes, and strict build workflow.
- [**Quick Start Guide**](../03-guides/quick-start.md): Get your local development environment up and running in minutes.
- [**Architecture Overview**](../02-architecture/00-overview.md): Understand the high-level design and data flow.
- [**Reference Index**](../04-reference/index.md): Browse published CLI, contracts, provider, pipeline, API, and template reference surfaces.
- [**How-To Guides**](../03-guides/getting-started.md): Guides for common tasks (adding sources, pipelines, troubleshooting).
- [**Operations Archive Index**](../05-operations/archive-index.md): Historical ops evidence and archive-only operational material.
- Repository path `docs/99-archive/README.md`: Historical and superseded materials for traceability only.

## Supported Local Workflows

The repository currently supports three practical local execution modes:

- **CI / single-OS checkout**: use `uv run python -m ...` and maintained Make
  targets such as `make install`, `make test`, `make lint`.
- **Windows PowerShell in a mixed Windows + WSL checkout**: bootstrap with
  `.\scripts\engineering\dev\setup_env_windows.ps1`, then prefer
  `.\scripts\engineering\dev\run_pytest.ps1`, `.\scripts\engineering\dev\run_mypy.ps1`, or
  `.\.venv-win\Scripts\python.exe -m ...`.
- **WSL/Linux in a mixed Windows + WSL checkout**: bootstrap with
  `bash scripts/engineering/dev/setup_env_wsl.sh`, then prefer
  `bash scripts/engineering/dev/run_pytest.sh`, `bash scripts/engineering/dev/run_mypy.sh`, or
  `"${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}/bin/python" -m ...`.

Do not reuse the same `.venv` between PowerShell and WSL. The maintained mixed
checkout path uses `.venv-win` in PowerShell and an external WSL venv at
`${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}` by default.

## Key Features

| Feature                    | Description                                          | ADR                                                                               |
| -------------------------- | ---------------------------------------------------- | --------------------------------------------------------------------------------- |
| **Medallion Architecture** | Bronze → Silver → Gold data flow                     | [ADR-002](../02-architecture/decisions/ADR-002-medallion-architecture.md)         |
| **Delta Lake Storage**     | ACID transactions, time travel, schema evolution     | [ADR-001](../02-architecture/decisions/ADR-001-delta-lake-vs-parquet.md)          |
| **Local-Only Deployment**  | File-based storage, no Docker/Redis required         | [ADR-010](../02-architecture/decisions/ADR-010-local-only-deployment.md)          |
| **Graceful Shutdown**      | SIGTERM/SIGINT handling with checkpoint save         | [ADR-015](../02-architecture/decisions/ADR-015-pipeline-services-lifecycle.md)     |
| **Circuit Breaker**        | Fault tolerance for API failures                     | [ADR-007](../02-architecture/decisions/ADR-007-circuit-breaker-implementation.md) |
| **Deterministic Writes**   | Reproducible SCD2 with ingestion-ts                  | [ADR-014](../02-architecture/decisions/ADR-014-deterministic-writes.md)           |
| **Gold Validation**        | Pandera strict schema validation                     | [ADR-018](../02-architecture/decisions/ADR-018-gold-strict-validation.md)         |
| **Composite Pipeline**     | Multi-source data enrichment (seed → enrich → merge) | [ADR-026](../02-architecture/decisions/ADR-026-composite-pipeline-pattern.md)     |

## Supported Providers (7)

| Provider             | Entities                                                                                                                                                               | Status     | Rate Limit                            |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ------------------------------------- |
| **ChEMBL**           | Activity, Assay, Assay Parameters, Molecule, Target, Target Component, Target Protein Classification, Protein Class, Cell Line, Compound Record, Publication, Publication Term, Publication Similarity, Subcellular Fraction, Tissue | Production | 0.1 req/sec (`chembl.yaml`; upstream courtesy is 3 req/sec) |
| **PubChem**          | Compound                                                                                                                                                               | Production | 5 req/sec                             |
| **UniProt**          | Protein, ID Mapping                                                                                                                                                    | Production | 10 req/sec (100 req/sec with API key) |
| **PubMed**           | Publication                                                                                                                                                            | Production | 3 req/sec                             |
| **CrossRef**         | Publication                                                                                                                                                            | Production | Polite pool                           |
| **OpenAlex**         | Publication                                                                                                                                                            | Production | ~10 req/sec                           |
| **Semantic Scholar** | Publication                                                                                                                                                            | Production | 0.1 req/sec (1 req/sec with API key)  |

### Composite Pipeline (ADR-026)

BioETL supports multi-source data enrichment through Composite Pipelines:

```bash
# Run composite publication pipeline (seed from ChEMBL, enrich from CrossRef, OpenAlex, PubMed)
bioetl run-composite --composite publication --seed-limit 1000
```

See [Composite Pipeline Diagram](../02-architecture/diagrams/foundation/29-composite-pipeline-workflow.mmd) for workflow visualization.

## Current Version

**v6.1.11** (governance baseline per [RULES.md](RULES.md)) — See [CHANGELOG](https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/CHANGELOG.md) for release history.

## Getting Started

```bash
# Clone and setup
git clone <repo-url>
cd BioactivityDataAcquisition
make install

# Run a pipeline
bioetl run --pipeline chembl_activity --limit 100

# Run tests
make test
```

Mixed Windows + WSL checkout shortcuts:

```powershell
.\scripts\engineering\dev\setup_env_windows.ps1
.\scripts\engineering\dev\run_pytest.ps1 tests\ --timeout=120 -n 1 --lf
```

```bash
bash scripts/engineering/dev/setup_env_wsl.sh
bash scripts/engineering/dev/run_pytest.sh tests/ --timeout=120 -n auto --lf
```

______________________________________________________________________

*Last updated: 2026-04-02*
