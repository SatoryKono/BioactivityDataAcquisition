______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# BioETL Architecture & Class Diagrams

*Canonical diagram location — all `.mmd` sources live here.*

> **Governance:** [ADR-040 — Diagram Governance and Layout Policy](../decisions/ADR-040-diagram-governance.md)
> Colour scheme, linkStyle differentiation, view decomposition rules, CI validation — all defined in ADR-040.
> Supplemental working policy for diagram publication/layout hygiene lives at `docs/02-architecture/diagrams/governance/00-diagramming-policy.md`.

All diagrams are in [Mermaid](https://mermaid.js.org/) format.
Canonical sources use `.mmd`; decomposed views use `.mermaid` in `views/`.
Render them with any Mermaid-compatible viewer, IDE plugin, or the [Mermaid Live Editor](https://mermaid.live/).

______________________________________________________________________

## Source Of Truth And Publication Boundary

- Canonical architecture/class/foundation sources live in the `.mmd` trees under this directory.
- `png/`, `svg/`, `bundles/`, `descriptions/` and supplemental `INDEX.md` files are published or derived artifacts.
- `views/*.mermaid` are focused review views and should be treated as presentation-oriented slices, not as replacements for the canonical `.mmd` families.

When diagram drift is detected, the first remediation target should usually be the publication layer: stale descriptions, bundles, indexes, and rendered artifacts. Broad redraw of canonical `.mmd` sources should be the exception, not the default response.

______________________________________________________________________

## Supplementary Non-Nav Indexes

These artifacts are intentionally outside primary nav but linked here for discoverability.

- `architecture/svg/INDEX.md`
- `architecture/png/INDEX.md`
- `class-diagrams/svg/INDEX.md`
- `class-diagrams/png/INDEX.md`
- `foundation/svg/INDEX.md`
- `foundation/png/INDEX.md`
- `views/svg/INDEX.md`
- `views/png/INDEX.md`
- [bundles/architecture.bundle.md](bundles/architecture.bundle.md)
- [bundles/class.bundle.md](bundles/class.bundle.md)
- [descriptions/INDEX.md](descriptions/INDEX.md)
- [descriptions/class-summary.md](descriptions/class-summary.md)
- [bundles/foundation.bundle.md](bundles/foundation.bundle.md)
- [bundles/views.bundle.md](bundles/views.bundle.md)

______________________________________________________________________

## Architecture Diagrams (23 core)

| #   | Diagram                                | File                                                | Description                                                                           |
| --- | -------------------------------------- | --------------------------------------------------- | ------------------------------------------------------------------------------------- |
| 1   | High-Level Hexagonal Architecture      | `architecture/01-high-level-hexagonal.mmd`          | Full system overview: layers, external systems, dependency directions                 |
| 2   | Layer Dependency Matrix                | `architecture/02-layer-dependency-matrix.mmd`       | ARCH-001 import boundary enforcement                                                  |
| 3   | Medallion Data Flow                    | `architecture/03-medallion-data-flow.mmd`           | Bronze → Silver → Gold pipeline with DQ and quarantine                                |
| 4   | Pipeline Execution Flow                | `architecture/04-pipeline-execution-flow.mmd`       | Sequence diagram: preflight → lock → execute → postrun → cleanup                      |
| 5   | Provider Adapter Hierarchy             | `architecture/05-provider-adapter-hierarchy.mmd`    | All 7 provider adapters, base classes, mixins, decorators                             |
| 6   | Storage Layer                          | `architecture/06-storage-layer.mmd`                 | Bronze/Silver/Gold writers, Delta Lake, metadata, validation                          |
| 7   | Data Quality System                    | `architecture/07-dq-system.mmd`                     | DQ monitoring, analysis, anomaly detection, reporting                                 |
| 8   | Composite Pipeline                     | `architecture/08-composite-pipeline.mmd`            | Seed → dependencies → enrichers (parallel) → merge with FSM                           |
| 9   | Observability Stack                    | `architecture/09-observability-stack.mmd`           | Logging, metrics, tracing: ports and implementations                                  |
| 10  | Resilience Patterns                    | `architecture/10-resilience-patterns.mmd`           | Circuit breaker, rate limiter, retry, health checks                                   |
| 11  | Configuration System                   | `architecture/11-configuration-system.mmd`          | YAML configs → loaders → Pydantic schemas → domain config                             |
| 12  | Bootstrap / DI Container               | `architecture/12-bootstrap-di-container.mmd`        | Composition root: entrypoints, bootstrap seams, runtime/admin assembly                |
| 13  | Port/Protocol Contracts                | `architecture/13-port-protocol-contracts.mmd`       | All 29 domain ports mapped to their implementations                                   |
| 14  | CLI / Interface Layer                  | `architecture/14-cli-interface-layer.mmd`           | CLI routing through registry helpers, composition entrypoints, and bootstrap services |
| 15  | BatchExecutor Internals                | `architecture/15-batch-executor-internals.mmd`      | Executor composition: transformer, writer, memory, metrics                            |
| 16  | Transformer Hierarchy                  | `architecture/16-transformer-hierarchy.mmd`         | Template Method pattern, all provider transformers, extractors                        |
| 17  | Security, PII & Audit                  | `architecture/17-security-pii-audit.mmd`            | PII hashing, salt rotation, audit trail                                               |
| 18  | Lock, Checkpoint & Shutdown            | `architecture/18-lock-checkpoint-shutdown.mmd`      | General lifecycle vs composite-specific lock/checkpoint semantics                     |
| 19  | Control-Plane Artifacts & Traceability | `architecture/19-control-plane-artifacts.mmd`       | Manifest/effective-config/ledger publication and lineage inspection surface           |
| 20  | Data Traceability Runtime Path         | `architecture/20-data-traceability-runtime.mmd`     | End-to-end traceability anchors from caller to artifact inspection                    |
| 21  | Idempotent Processing Guards           | `architecture/21-idempotent-processing-guards.mmd`  | Lock ownership, checkpoint identity, resume policy, and safe rerun guards             |
| 22  | Data Operations Observability          | `architecture/22-data-operations-observability.mmd` | Logs, metrics, tracing, and low-cardinality control-plane signals                     |
| 23  | Reproducible Run Contract              | `architecture/23-reproducible-run-contract.mmd`     | Config resolution, effective-config artifacts, and execution fingerprint identity     |

## Decomposed Architecture Diagrams

Parent diagrams remain canonical references. Sub-files provide focused, low-density views for review and onboarding.

| Parent (canonical)                                               | Decomposed sub-files                                                                                                                                                                                                             |
| ---------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `architecture/01-high-level-hexagonal.mmd`                       | `architecture/01a-hexagonal-overview.mmd`, `architecture/01b-hexagonal-domain-app.mmd`, `architecture/01c-hexagonal-infra-comp.mmd`, `architecture/01d-hexagonal-overview-rounded.mmd`                                           |
| `architecture/03-medallion-data-flow.mmd`                        | `architecture/03a-medallion-layers-overview.mmd`                                                                                                                                                                                 |
| `architecture/05-provider-adapter-hierarchy.mmd`                 | `architecture/05a-adapter-hierarchy-base.mmd`, `architecture/05b-adapter-hierarchy-providers.mmd`                                                                                                                                |
| `architecture/12-bootstrap-di-container.mmd`                     | `architecture/12a-bootstrap-factories.mmd`, `architecture/12b-bootstrap-wiring.mmd`                                                                                                                                              |
| `architecture/13-port-protocol-contracts.mmd`                    | `architecture/13a-port-contracts-data-sources.mmd`, `architecture/13b-port-contracts-storage.mmd`, `architecture/13c-port-contracts-observability.mmd`, `architecture/13d-port-contracts-services.mmd`                           |
| `architecture/13-port-protocol-contracts.mmd` (alternate slices) | `architecture/13a-data-storage-ports.mmd`, `architecture/13b-operational-ports.mmd`, `architecture/13c-validation-dq-ports.mmd`, `architecture/13e-operational-ports-domain.mmd`, `architecture/13f-operational-ports-infra.mmd` |
| `architecture/06-storage-layer.mmd`                              | `architecture/06a-storage-writers.mmd`, `architecture/06b-storage-support.mmd`                                                                                                                                                   |
| `architecture/07-dq-system.mmd`                                  | `architecture/07a-dq-analysis.mmd`, `architecture/07b-dq-pipeline.mmd`                                                                                                                                                           |
| `architecture/08-composite-pipeline.mmd`                         | `architecture/08a-composite-config.mmd`, `architecture/08b-composite-execution.mmd`                                                                                                                                              |
| `architecture/09-observability-stack.mmd`                        | `architecture/09a-observability-app.mmd`, `architecture/09b-observability-infra.mmd`                                                                                                                                             |
| `architecture/11-configuration-system.mmd`                       | `architecture/11a-config-loading.mmd`, `architecture/11b-config-domain.mmd`                                                                                                                                                      |
| `architecture/14-cli-interface-layer.mmd`                        | `architecture/14a-cli-commands.mmd`, `architecture/14b-cli-routing.mmd`                                                                                                                                                          |
| `architecture/16-transformer-hierarchy.mmd`                      | `architecture/16a-transformer-base.mmd`, `architecture/16b-transformer-pub-other.mmd`                                                                                                                                            |
| `architecture/18-lock-checkpoint-shutdown.mmd`                   | `architecture/18a-lock-system.mmd`, `architecture/18b-checkpoint-shutdown.mmd`                                                                                                                                                   |
| `architecture/21-idempotent-processing-guards.mmd`               | `views/21-idempotent-processing-guards-overview.mermaid`                                                                                                                                                                         |
| `architecture/23-reproducible-run-contract.mmd`                  | `views/23-reproducible-run-contract-overview.mermaid`                                                                                                                                                                            |

> `13a/13b/13c` have two parallel decomposition tracks by design:
> `port-contracts-*` = contract-centric views, `*-ports` = operational slices.

## Class Diagrams (19 curated families + supplemental package-family coverage)

The canonical handcrafted layer still consists of the 19 curated families below.
In addition, the directory now publishes AST-derived supplemental package-family
class diagrams for every `src/bioetl/**` family with more than three top-level
classes that was not already covered by the curated set.

- Supplemental generator: `scripts/diagrams/generate_package_family_class_diagrams.py`
- Generated source naming: `class-diagrams/90-pkg-*.mmd`
- Current supplemental coverage: **66 package families / 74 density-aware slices**

| #   | Family                        | File                                                            | Description                                                                 |
| --- | ----------------------------- | --------------------------------------------------------------- | --------------------------------------------------------------------------- |
| 1   | Domain Ports                  | `class-diagrams/01-domain-ports.mmd`                            | Domain port overview with narrow storage ports plus aggregate compat facade |
| 2   | Domain Ports (L2 Methods)     | `class-diagrams/01a-domain-ports-method-catalog.mmd`            | Method-level catalog for key port protocols                                 |
| 3   | Entities & Aggregates         | `class-diagrams/02-entities-aggregates.mmd`                     | BaseEntity, Batch, PipelineRun, BatchRecord                                 |
| 4   | Value Objects                 | `class-diagrams/03-value-objects.mmd`                           | BronzeWriteResult, SilverWriteResult, FencingToken, etc.                    |
| 5   | Types & Enums                 | `class-diagrams/04-types-enums.mmd`                             | RunType, PublicationType, HealthStatus, NewTypes                            |
| 6   | Exceptions                    | `class-diagrams/05-exceptions.mmd`                              | BioETLError hierarchy: Critical, Recoverable, DataQuality                   |
| 7   | Configuration                 | `class-diagrams/06-config-classes.mmd`                          | PipelineConfig, RuntimeConfig, CompositeConfig                              |
| 8   | Application Core              | `class-diagrams/07-application-core-services.mmd`               | PipelineRunner, BatchExecutor, LockCoordinator                              |
| 9   | Application Services          | `class-diagrams/08-application-services.mmd`                    | DQ, Health, Export, Vacuum, Quarantine services                             |
| 10  | Application Services (L2 Ops) | `class-diagrams/08a-application-services-operation-catalog.mmd` | Operation-level catalog for application services                            |
| 11  | Transformers                  | `class-diagrams/09-transformers.mmd`                            | BaseTransformer → ChEMBL/Publication/UniProt/PubChem                        |
| 12  | Adapters                      | `class-diagrams/10-adapters.mmd`                                | BaseHttpAdapter, all provider adapters, resilience                          |
| 13  | Storage                       | `class-diagrams/11-storage.mmd`                                 | BronzeWriter, SilverWriter, GoldWriter, DeltaReader                         |
| 14  | Composite Pipeline            | `class-diagrams/12-composite-pipeline.mmd`                      | Runner, coordinators, merger, FSM                                           |
| 15  | Domain Services               | `class-diagrams/13-domain-services.mmd`                         | IdentityService, Normalization, UnitConverter                               |
| 16  | Observability                 | `class-diagrams/14-observability.mmd`                           | Logger, Metrics, Tracing implementations                                    |
| 17  | Observability (L2 Methods)    | `class-diagrams/14a-observability-method-catalog.mmd`           | Method-level catalog for logging/metrics/tracing                            |
| 18  | Extractors                    | `class-diagrams/15-extractors.mmd`                              | BaseFieldExtractor, PubMed & UniProt extractors                             |
| 19  | Factories & Bootstrap         | `class-diagrams/16-factories-bootstrap.mmd`                     | Current composition factories, registries, and runtime assembly seams       |

## Foundation Diagrams (55)

Historical/foundational diagrams consolidated from `docs/02-architecture/diagrams/`.

### Foundation 01–25

| #   | File                                                   | Description                                 |
| --- | ------------------------------------------------------ | ------------------------------------------- |
| 01a | `foundation/01-full-system-component.mmd`              | Full system component diagram (C4-style)    |
| 01b | `foundation/01-high-level.mmd`                         | High-level system overview                  |
| 02a | `foundation/02-full-medallion-data-flow.mmd`           | Medallion architecture data flow (detailed) |
| 03a | `foundation/03-pipeline-execution-happy-path.mmd`      | Pipeline execution sequence (happy path)    |
| 04a | `foundation/04-domain-layer-class-diagram.mmd`         | Domain layer ports, entities, config        |
| 04b | `foundation/04-error-flow.mmd`                         | Error handling flow                         |
| 05a | `foundation/05-layers-interaction.mmd`                 | Layer interaction diagram                   |
| 05c | `foundation/05-pipeline-lifecycle-states.mmd`          | Pipeline state machine                      |
| 06a | `foundation/06-application-layer-class-diagram.mmd`    | Application layer classes                   |
| 06b | `foundation/06-pipeline-execution.mmd`                 | Pipeline execution flow                     |
| 07a | `foundation/07-circuit-breaker-states.mmd`             | Circuit breaker state machine               |
| 07b | `foundation/07-medallion-flow.mmd`                     | Medallion data flow                         |
| 08a | `foundation/08-complete-etl-workflow.mmd`              | Complete ETL workflow                       |
| 08b | `foundation/08-domain-ddd.mmd`                         | Domain-driven design diagram                |
| 09  | `foundation/09-full-er-diagram.mmd`                    | Entity-relationship diagram                 |
| 10  | `foundation/10-infrastructure-layer-class-diagram.mmd` | Infrastructure layer classes                |
| 11  | `foundation/11-lock-acquisition-sequence.mmd`          | Lock acquisition sequence                   |
| 12  | `foundation/12-local-deployment-architecture.mmd`      | Local deployment architecture (ADR-010)     |
| 13  | `foundation/13-domain-models-relationship.mmd`         | Domain model relationships                  |
| 14  | `foundation/14-provider-health-states.mmd`             | Provider health states                      |
| 15  | `foundation/15-dq-check-workflow.mmd`                  | Data quality check workflow                 |
| 16  | `foundation/16-memory-lock-class.mmd`                  | MemoryLock class diagram                    |
| 17  | `foundation/17-pipeline-hierarchy.mmd`                 | Pipeline/Transformer hierarchy              |
| 18  | `foundation/18-bronze-write-sequence.mmd`              | Bronze write sequence                       |
| 19  | `foundation/19-delta-lake-write-sequence.mmd`          | Delta Lake write sequence                   |
| 20  | `foundation/20-quarantine-record-states.mmd`           | Quarantine record states                    |
| 21  | `foundation/21-activity-entity-data-flow.mmd`          | Activity entity data flow                   |
| 22  | `foundation/22-client-api-request-sequence.mmd`        | Client API request sequence                 |
| 23  | `foundation/23-silver-writer-class.mmd`                | SilverWriter class diagram                  |
| 24  | `foundation/24-hash-service-class.mmd`                 | Hash service class diagram                  |
| 25  | `foundation/25-circuit-breaker-observer-class.mmd`     | CircuitBreaker class diagram                |

### Foundation 26–50 (TOP-24 Architecture)

| #   | File                                                | Type      | Description                                                                                |
| --- | --------------------------------------------------- | --------- | ------------------------------------------------------------------------------------------ |
| 26  | `foundation/26-hexagonal-ports-adapters.mmd`        | flowchart | Hexagonal Architecture — all 24 ports mapped to adapters                                   |
| 27  | `foundation/27-import-matrix-enforcement.mmd`       | flowchart | ARCH-001 Import Matrix — 5-layer dependency rules                                          |
| 28  | `foundation/28-composition-root-di-graph.mmd`       | flowchart | Composition Root DI Graph — full DI assembly                                               |
| 29  | `foundation/29-composite-pipeline-workflow.mmd`     | sequence  | Composite Pipeline (ADR-026) — seed/deps/fan-out/merge with current checkpoint + lock path |
| 30  | `foundation/30-port-adapter-mapping.mmd`            | flowchart | Port → Adapter Reference — all 24 ports                                                    |
| 31  | `foundation/31-pipeline-run-lifecycle.mmd`          | state     | PipelineRun Aggregate FSM                                                                  |
| 32  | `foundation/32-single-record-journey.mmd`           | flowchart | Single Record Journey — API→Bronze→Transform→Silver→Gold                                   |
| 33  | `foundation/33-cli-run-interaction.mmd`             | sequence  | CLI → PipelineRunnerService interaction                                                    |
| 34  | `foundation/34-batch-processing-flow.mmd`           | sequence  | Batch Processing — BatchExecutor cycle                                                     |
| 35  | `foundation/35-bootstrap-sequence.mmd`              | sequence  | Bootstrap Sequence — composition root assembly                                             |
| 36  | `foundation/36-architecture-principles-mindmap.mmd` | mindmap   | Architecture Principles Mindmap                                                            |
| 37  | `foundation/37-cli-entry-full-chain.mmd`            | sequence  | CLI Entry → Exit Code full chain                                                           |
| 38  | `foundation/38-runtime-assembly-sequence.mmd`       | sequence  | Runtime Assembly — phases 1–8                                                              |
| 39  | `foundation/39-medallion-invariants.mmd`            | flowchart | Medallion Invariants — ARCH-007 RunType clear policy                                       |
| 40  | `foundation/40-application-core-collaboration.mmd`  | flowchart | Application Core — PipelineRunner orchestrating services                                   |
| 41  | `foundation/41-error-classification-tree.mmd`       | flowchart | Error Classification — HTTP→Domain→Actions                                                 |
| 42  | `foundation/42-pipeline-runner-class.mmd`           | class     | PipelineRunner Class — all 14 DI dependencies                                              |
| 43  | `foundation/43-fan-out-fan-in-pattern.mmd`          | sequence  | Fan-Out/Fan-In — asyncio.gather parallel enrichment                                        |
| 44  | `foundation/44-cross-provider-enrichment.mmd`       | flowchart | Cross-Provider Enrichment — 5-provider publication flow                                    |
| 46  | `foundation/46-yaml-config-resolution.mmd`          | flowchart | YAML Config Resolution — unified path plus active compatibility normalization              |
| 47  | `foundation/47-publication-merge-sources.mmd`       | sequence  | Publication Composite — optional enrichers, field priorities, alias compatibility          |
| 48  | `foundation/48-composite-phase-lifecycle.mmd`       | state     | Composite Pipeline FSM — 10-state lifecycle                                                |
| 49  | `foundation/49-composite-runner-class.mmd`          | class     | CompositePipelineRunner — component diagram                                                |
| 50  | `foundation/50-exception-hierarchy.mmd`             | flowchart | Exception Hierarchy — BioETLError full tree                                                |

______________________________________________________________________

## Colour Scheme

| Layer          | Colour | Fill      | Border    |
| -------------- | ------ | --------- | --------- |
| Domain         | Purple | `#f5f3ff` | `#7c3aed` |
| Application    | Green  | `#f0fdf4` | `#16a34a` |
| Infrastructure | Red    | `#fff1f2` | `#dc2626` |
| Interfaces     | Blue   | `#eff6ff` | `#2563eb` |
| Composition    | Orange | `#fff7ed` | `#f59e0b` |
| External       | Gray   | `#f1f5f9` | `#64748b` |

### Medallion Layers

| Layer      | Fill      | Border    |
| ---------- | --------- | --------- |
| Bronze     | `#fff7ed` | `#f59e0b` |
| Silver     | `#f8fafc` | `#475569` |
| Gold       | `#fefce8` | `#ca8a04` |
| Quarantine | `#ffe4e6` | `#e11d48` |

______________________________________________________________________

## Rendering

### Prerequisites

```bash
# Mermaid CLI (required for native/local mode)
npm install -g @mermaid-js/mermaid-cli

# Browser runtime for mmdc (required by Puppeteer in local validation)
npx puppeteer browsers install chrome-headless-shell

# svgo — SVG optimization (recommended)
npm install -g svgo

# librsvg — high-quality SVG → PNG (recommended)
# macOS:
brew install librsvg
# Ubuntu/Debian:
sudo apt-get install librsvg2-bin
```

Tooling note:

- repo scripts now use `scripts/diagrams/mmdc_wrapper.sh` as the default `mmdc` entrypoint;
- if a native `mmdc` is unavailable, the wrapper can fall back to Docker image `minlag/mermaid-cli`;
- to force Docker mode even when a local `mmdc` exists, set `MMDC_FORCE_DOCKER=1`;
- to pin an explicit binary, set `MMDC_BIN=/path/to/mmdc`.

### Quick start

```bash
# Render ALL diagrams (SVG + PNG) with custom theme
make render-diagrams

# SVG only (faster)
make render-diagrams-svg

# Smoke-check visibility for edge labels and node text in SVG baselines
make check-diagrams-visibility

# Or run the script directly
bash docs/02-architecture/diagrams/tooling/render.sh

# Single diagram with theme
mmdc -i docs/02-architecture/diagrams/architecture/01-high-level-hexagonal.mmd \
     -o output.svg \
     -c docs/02-architecture/diagrams/theme/mermaid-config.json \
     --cssFile docs/02-architecture/diagrams/theme/custom.css

# Build print-safe PDF bundles with descriptions
make render-diagrams-descriptions-pdf

# Build DOCX bundles with descriptions
make render-diagrams-descriptions-docx

# Full agent pipeline (checks + render + DOCX + PDF)
make run-diagram-docs-agent
```

Description PDF generation uses:

- `scripts/diagrams/generate_with_descriptions_pdf.py`
- `scripts/diagrams/generate_with_descriptions_docx.py`
- unified orchestrator: `scripts/diagrams/run_diagram_docs_agent.sh`
- print CSS: `docs/02-architecture/diagrams/theme/with-descriptions-print.css`
- post-check: `scripts/diagrams/check_pdf_image_bounds.py`

### Render options

```bash
# Filter by name glob
bash docs/02-architecture/diagrams/tooling/render.sh --filter "01-*"

# Single directory only
bash docs/02-architecture/diagrams/tooling/render.sh --dir docs/02-architecture/diagrams/architecture

# Adjust PNG resolution globally
bash docs/02-architecture/diagrams/tooling/render.sh --scale 4 --width 3200 --height 2400

# Auto-boost resolution for large diagrams by @nodes metadata
bash docs/02-architecture/diagrams/tooling/render.sh \
  --large-threshold 30 \
  --large-scale 4 \
  --large-png-dpi 450

# Per-diagram PNG override via source metadata:
#   %% @png-scale 6
#   %% @png-dpi   600
# (works for both .mmd and .mermaid files)

# CI mode (Puppeteer sandbox disabled)
bash docs/02-architecture/diagrams/tooling/render.sh --puppeteer /tmp/puppeteer-config.json

# Text-layer mode (recommended for Chrome/SVG export parity)
# dual          : keep foreignObject + add fallback text
# fo-only       : keep only foreignObject labels
# fallback-only : add fallback text and strip foreignObject labels
bash docs/02-architecture/diagrams/tooling/render.sh --text-layer fallback-only

# Syntax validation (shows explicit hint if Chrome runtime is missing)
bash scripts/diagrams/validate_mermaid_syntax.sh --puppeteer /tmp/puppeteer-config.json
```

### Output layout

```
docs/02-architecture/diagrams/
  architecture/
    *.mmd           # source diagrams (57)
    svg/*.svg       # rendered vector (scalable)
    png/*.png       # rendered raster (300 DPI)
  class-diagrams/
    *.mmd           # source diagrams (94 total:
                    #   19 curated families
                    #   1 frontmatter sandbox copy
                    #   74 supplemental package slices)
    svg/*.svg
    png/*.png
  foundation/
    *.mmd           # source diagrams (55)
    svg/*.svg
    png/*.png       # default 300 DPI, auto high-res for large @nodes diagrams,
                    # plus optional per-file @png-scale/@png-dpi overrides
  descriptions/
    **/*.md         # published narrative cards and family indexes
  bundles/
    *.bundle.md     # derived Markdown bundles
    *.bundle.pdf    # print-safe PDF exports
    *.bundle.docx   # editable DOCX exports
  manifests/
    *.txt           # smoke, quality-gate, and compatibility manifests
  tooling/
    render.sh       # unified renderer entrypoint
  theme/
    mermaid-config.json   # colours, fonts, spacing
    custom.css            # fine-tuned SVG styling
  README.md               # this file
```

### CI/CD

Diagrams are validated and rendered automatically in GitHub Actions
(`.github/workflows/docs.yml`). Rendered SVG/PNG are uploaded as build artifacts.
A drift check warns when `.mmd/.mermaid` sources change without re-rendering.
The workflow also validates SVG text visibility for the smoke baseline set.

### Quality Budget

Phase C adds explicit budget enforcement via
`scripts/diagrams/enforce_diagram_quality_budget.py`.

Current PR budget:

- `quality.hard_failures <= 0`
- `quality.DIAG-T022 <= 0`
- `quality.DIAG-T023 <= 0`
- `lint.errors <= 0`

Current nightly budget adds:

- `nightly.errors <= 0`
- `nightly.warnings <= 0`

Local run (PR budget):

```bash
mkdir -p reports/diagrams
uv run python -m scripts.diagrams check-quality-gates \
  --manifest docs/02-architecture/diagrams/manifests/quality-gates.txt \
  --json-out reports/diagrams/diagram-quality-report.json
uv run python scripts/diagrams/lint_diagrams.py docs/02-architecture/diagrams --json \
  > reports/diagrams/diagram-lint-report.json || true
uv run python -m scripts.diagrams lint-budget \
  --mode pr \
  --quality-report reports/diagrams/diagram-quality-report.json \
  --lint-report reports/diagrams/diagram-lint-report.json \
  --max-hard-failures 0 \
  --max-diag-t022 0 \
  --max-diag-t023 0 \
  --max-lint-errors 0
```

Local run through unified runner:

```bash
bash scripts/diagrams/run_diagram_checks.sh --profile pr --enforce-budget
bash scripts/diagrams/run_diagram_checks.sh --profile nightly --enforce-budget
```

______________________________________________________________________

## Size Normalization

Use `scripts/diagrams/uniform_diagram_sizes.py` to normalize class/flowchart object sizes:

```bash
# Check normalization drift
python3 scripts/diagrams/uniform_diagram_sizes.py --check

# Fix specific files
python3 scripts/diagrams/uniform_diagram_sizes.py --fix -f docs/02-architecture/diagrams/class-diagrams/07-application-core-services.mmd
```

Grouped diagrams support width strategy override:

- `%% @uniform-width global` (default): one shared width across groups.
- `%% @uniform-width group`: group-local widths to reduce excessive `&nbsp;` padding.

______________________________________________________________________

## Validation Rules

`scripts/diagrams/lint_diagrams.py` enforces:

| Rule       | Description                                                               | Severity |
| ---------- | ------------------------------------------------------------------------- | -------- |
| META-001   | Missing structured metadata (`@...` in `.mmd`, `%% View:` in `.mermaid`)  | WARN     |
| META-002   | Invalid date format in `%% Updated:`/`%% @date`                           | ERROR    |
| COLOUR-001 | Deprecated pre-ADR palette in `style`/`classDef`                          | ERROR    |
| COLOUR-002 | Emoji in subgraph labels                                                  | ERROR    |
| SIZE-001   | `@nodes > 35`                                                             | ERROR    |
| SIZE-002   | `@nodes > 20`                                                             | WARN     |
| SIZE-003   | `@nodes > 35`, but decomposed sibling `.mmd` slices exist (`01a/01b/...`) | WARN     |
| LAYOUT-001 | `flowchart/graph` with `@nodes > 20` without ELK init                     | WARN     |
| LAYOUT-002 | `flowchart/graph` with `@nodes > 40` without ELK init                     | ERROR    |
| LINK-001   | Dense flowchart uses only one arrow semantic style                        | WARN     |
| LINK-002   | Fragile singleton-index `linkStyle` pattern (many one-by-one index lines) | WARN     |
| GRAPH-001  | Orphan nodes (defined but not in any edge)                                | WARN     |
| NBSP-001   | `&nbsp;` padding detected in source                                       | ERROR    |

Node-size exceptions in current lint implementation:

- `*-full.mermaid` reference views are exempt from `SIZE-001`/`SIZE-002`.
- `00-legend*` files are exempt from `SIZE-001`/`SIZE-002`.

### Orphan Node Detection (GRAPH-001)

`scripts/diagrams/prune_orphan_nodes.py` detects nodes defined in a diagram but not
participating in any edge or message.

**Applies to:** `flowchart` / `graph` and `sequenceDiagram` only.
**Skipped:** `classDiagram`, `stateDiagram`, `erDiagram`, `mindmap`, legend files.

```bash
# Report orphans (CI mode)
python scripts/diagrams/prune_orphan_nodes.py --check

# Machine-readable output
python scripts/diagrams/prune_orphan_nodes.py --check --json

# Remove confirmed garbage orphans (in-place)
python scripts/diagrams/prune_orphan_nodes.py --fix

# Exempt all current orphans (one-time grandfathering)
python scripts/diagrams/prune_orphan_nodes.py --grandfather
```

**To keep an intentional "documentation" node that has no edges:**

```
%% keep-orphan: NodeId
%% keep-orphan: NodeA, NodeB, NodeC
```

Insert anywhere in the file (commonly after the diagram-type declaration).

**Lenient subgraph rule:** nodes inside a subgraph whose *name* appears in an
edge (e.g. `Bronze --> Silver`) are **not** flagged — they are considered
descriptive children of a connected subgraph container.
