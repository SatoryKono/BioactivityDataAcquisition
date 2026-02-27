# BioETL Architecture & Class Diagrams

*Canonical diagram location — all `.mmd` sources live here.*

> **Governance:** [ADR-040 — Diagram Governance and Layout Policy](../decisions/ADR-040-diagram-governance.md)
> Colour scheme, linkStyle differentiation, view decomposition rules, CI validation — all defined in ADR-040.

All diagrams are in [Mermaid](https://mermaid.js.org/) format (`.mmd` files).
Render them with any Mermaid-compatible viewer, IDE plugin, or the [Mermaid Live Editor](https://mermaid.live/).

---

## Architecture Diagrams (18)

| # | Diagram | File | Description |
|---|---------|------|-------------|
| 1 | High-Level Hexagonal Architecture | `architecture/01-high-level-hexagonal.mmd` | Full system overview: layers, external systems, dependency directions |
| 2 | Layer Dependency Matrix | `architecture/02-layer-dependency-matrix.mmd` | ARCH-001 import boundary enforcement |
| 3 | Medallion Data Flow | `architecture/03-medallion-data-flow.mmd` | Bronze → Silver → Gold pipeline with DQ and quarantine |
| 4 | Pipeline Execution Flow | `architecture/04-pipeline-execution-flow.mmd` | Sequence diagram: preflight → lock → execute → postrun → cleanup |
| 5 | Provider Adapter Hierarchy | `architecture/05-provider-adapter-hierarchy.mmd` | All 7 provider adapters, base classes, mixins, decorators |
| 6 | Storage Layer | `architecture/06-storage-layer.mmd` | Bronze/Silver/Gold writers, Delta Lake, metadata, validation |
| 7 | Data Quality System | `architecture/07-dq-system.mmd` | DQ monitoring, analysis, anomaly detection, reporting |
| 8 | Composite Pipeline | `architecture/08-composite-pipeline.mmd` | Seed → dependencies → enrichers (parallel) → merge with FSM |
| 9 | Observability Stack | `architecture/09-observability-stack.mmd` | Logging, metrics, tracing: ports and implementations |
| 10 | Resilience Patterns | `architecture/10-resilience-patterns.mmd` | Circuit breaker, rate limiter, retry, health checks |
| 11 | Configuration System | `architecture/11-configuration-system.mmd` | YAML configs → loaders → Pydantic schemas → domain config |
| 12 | Bootstrap / DI Container | `architecture/12-bootstrap-di-container.mmd` | Composition root: factories, assembly, wiring |
| 13 | Port/Protocol Contracts | `architecture/13-port-protocol-contracts.mmd` | All 29 domain ports mapped to their implementations |
| 14 | CLI / Interface Layer | `architecture/14-cli-interface-layer.mmd` | CLI commands, routing to application services |
| 15 | BatchExecutor Internals | `architecture/15-batch-executor-internals.mmd` | Executor composition: transformer, writer, memory, metrics |
| 16 | Transformer Hierarchy | `architecture/16-transformer-hierarchy.mmd` | Template Method pattern, all provider transformers, extractors |
| 17 | Security, PII & Audit | `architecture/17-security-pii-audit.mmd` | PII hashing, salt rotation, audit trail |
| 18 | Lock, Checkpoint & Shutdown | `architecture/18-lock-checkpoint-shutdown.mmd` | Fencing tokens, safety guard, graceful shutdown |

## Decomposed Architecture Diagrams

Parent diagrams remain canonical references. Sub-files provide focused, low-density views for review and onboarding.

| Parent (canonical) | Decomposed sub-files |
|---|---|
| `architecture/01-high-level-hexagonal.mmd` | `architecture/01a-hexagonal-overview.mmd`, `architecture/01b-hexagonal-domain-app.mmd`, `architecture/01c-hexagonal-infra-comp.mmd` |
| `architecture/05-provider-adapter-hierarchy.mmd` | `architecture/05a-adapter-hierarchy-base.mmd`, `architecture/05b-adapter-hierarchy-providers.mmd` |
| `architecture/12-bootstrap-di-container.mmd` | `architecture/12a-bootstrap-factories.mmd`, `architecture/12b-bootstrap-wiring.mmd` |
| `architecture/13-port-protocol-contracts.mmd` | `architecture/13a-port-contracts-data-sources.mmd`, `architecture/13b-port-contracts-storage.mmd`, `architecture/13c-port-contracts-observability.mmd`, `architecture/13d-port-contracts-services.mmd` |

## Class Diagrams (14 families)

| # | Family | File | Description |
|---|--------|------|-------------|
| 1 | Domain Ports | `class-diagrams/01-domain-ports.mmd` | All 29 Protocol interfaces with method signatures |
| 3 | Value Objects | `class-diagrams/03-value-objects.mmd` | BronzeWriteResult, SilverWriteResult, FencingToken, etc. |
| 4 | Types & Enums | `class-diagrams/04-types-enums.mmd` | RunType, PublicationType, HealthStatus, NewTypes |
| 5 | Exceptions | `class-diagrams/05-exceptions.mmd` | BioETLError hierarchy: Critical, Recoverable, DataQuality |
| 6 | Configuration | `class-diagrams/06-config-classes.mmd` | PipelineConfig, RuntimeConfig, CompositeConfig |
| 7 | Application Core | `class-diagrams/07-application-core-services.mmd` | PipelineRunner, BatchExecutor, LockManager |
| 8 | Application Services | `class-diagrams/08-application-services.mmd` | DQ, Health, Export, Vacuum, Quarantine services |
| 9 | Transformers | `class-diagrams/09-transformers.mmd` | BaseTransformer → ChEMBL/Publication/UniProt/PubChem |
| 10 | Adapters | `class-diagrams/10-adapters.mmd` | BaseHttpAdapter, all provider adapters, resilience |
| 11 | Storage | `class-diagrams/11-storage.mmd` | BronzeWriter, SilverWriter, GoldWriter, DeltaReader |
| 13 | Domain Services | `class-diagrams/13-domain-services.mmd` | IdentityService, Normalization, UnitConverter |
| 14 | Observability | `class-diagrams/14-observability.mmd` | Logger, Metrics, Tracing implementations |
| 15 | Extractors | `class-diagrams/15-extractors.mmd` | BaseFieldExtractor, PubMed & UniProt extractors |
| 16 | Factories & Bootstrap | `class-diagrams/16-factories-bootstrap.mmd` | DataSourceRegistry, TransformerFactory, RunnerBuilder |

## Foundation Diagrams (55)

Historical/foundational diagrams consolidated from `docs/02-architecture/diagrams/`.

### Foundation 01–25

| # | File | Description |
|---|------|-------------|
| 01a | `foundation/01-full-system-component.mmd` | Full system component diagram (C4-style) |
| 01b | `foundation/01-high-level.mmd` | High-level system overview |
| 02a | `foundation/02-full-medallion-data-flow.mmd` | Medallion architecture data flow (detailed) |
| 03a | `foundation/03-pipeline-execution-happy-path.mmd` | Pipeline execution sequence (happy path) |
| 04a | `foundation/04-domain-layer-class-diagram.mmd` | Domain layer ports, entities, config |
| 04b | `foundation/04-error-flow.mmd` | Error handling flow |
| 05a | `foundation/05-layers-interaction.mmd` | Layer interaction diagram |
| 05c | `foundation/05-pipeline-lifecycle-states.mmd` | Pipeline state machine |
| 06a | `foundation/06-application-layer-class-diagram.mmd` | Application layer classes |
| 06b | `foundation/06-pipeline-execution.mmd` | Pipeline execution flow |
| 07a | `foundation/07-circuit-breaker-states.mmd` | Circuit breaker state machine |
| 07b | `foundation/07-medallion-flow.mmd` | Medallion data flow |
| 08a | `foundation/08-complete-etl-workflow.mmd` | Complete ETL workflow |
| 08b | `foundation/08-domain-ddd.mmd` | Domain-driven design diagram |
| 09 | `foundation/09-full-er-diagram.mmd` | Entity-relationship diagram |
| 10 | `foundation/10-infrastructure-layer-class-diagram.mmd` | Infrastructure layer classes |
| 11 | `foundation/11-lock-acquisition-sequence.mmd` | Lock acquisition sequence |
| 12 | `foundation/12-local-deployment-architecture.mmd` | Local deployment architecture (ADR-010) |
| 13 | `foundation/13-domain-models-relationship.mmd` | Domain model relationships |
| 14 | `foundation/14-provider-health-states.mmd` | Provider health states |
| 15 | `foundation/15-dq-check-workflow.mmd` | Data quality check workflow |
| 16 | `foundation/16-memory-lock-class.mmd` | MemoryLock class diagram |
| 17 | `foundation/17-pipeline-hierarchy.mmd` | Pipeline/Transformer hierarchy |
| 18 | `foundation/18-bronze-write-sequence.mmd` | Bronze write sequence |
| 19 | `foundation/19-delta-lake-write-sequence.mmd` | Delta Lake write sequence |
| 20 | `foundation/20-quarantine-record-states.mmd` | Quarantine record states |
| 21 | `foundation/21-activity-entity-data-flow.mmd` | Activity entity data flow |
| 22 | `foundation/22-client-api-request-sequence.mmd` | Client API request sequence |
| 23 | `foundation/23-silver-writer-class.mmd` | SilverWriter class diagram |
| 24 | `foundation/24-hash-service-class.mmd` | Hash service class diagram |
| 25 | `foundation/25-circuit-breaker-observer-class.mmd` | CircuitBreaker class diagram |

### Foundation 26–50 (TOP-25 Architecture)

| # | File | Type | Description |
|---|------|------|-------------|
| 26 | `foundation/26-hexagonal-ports-adapters.mmd` | flowchart | Hexagonal Architecture — all 24 ports mapped to adapters |
| 27 | `foundation/27-import-matrix-enforcement.mmd` | flowchart | ARCH-001 Import Matrix — 5-layer dependency rules |
| 28 | `foundation/28-composition-root-di-graph.mmd` | flowchart | Composition Root DI Graph — full DI assembly |
| 29 | `foundation/29-composite-pipeline-workflow.mmd` | sequence | Composite Pipeline (ADR-026) — Seed→Deps→FanOut→Merge→Gold |
| 31 | `foundation/31-pipeline-run-lifecycle.mmd` | state | PipelineRun Aggregate FSM |
| 32 | `foundation/32-single-record-journey.mmd` | flowchart | Single Record Journey — API→Bronze→Transform→Silver→Gold |
| 33 | `foundation/33-cli-run-interaction.mmd` | sequence | CLI → PipelineRunnerService interaction |
| 34 | `foundation/34-batch-processing-flow.mmd` | sequence | Batch Processing — BatchExecutor cycle |
| 36 | `foundation/36-architecture-principles-mindmap.mmd` | mindmap | Architecture Principles Mindmap |
| 37 | `foundation/37-cli-entry-full-chain.mmd` | sequence | CLI Entry → Exit Code full chain |
| 38 | `foundation/38-runtime-assembly-sequence.mmd` | sequence | Runtime Assembly — phases 1–8 |
| 39 | `foundation/39-medallion-invariants.mmd` | flowchart | Medallion Invariants — ARCH-007 RunType clear policy |
| 40 | `foundation/40-application-core-collaboration.mmd` | flowchart | Application Core — PipelineRunner orchestrating services |
| 41 | `foundation/41-error-classification-tree.mmd` | flowchart | Error Classification — HTTP→Domain→Actions |
| 42 | `foundation/42-pipeline-runner-class.mmd` | class | PipelineRunner Class — all 14 DI dependencies |
| 43 | `foundation/43-fan-out-fan-in-pattern.mmd` | sequence | Fan-Out/Fan-In — asyncio.gather parallel enrichment |
| 44 | `foundation/44-cross-provider-enrichment.mmd` | flowchart | Cross-Provider Enrichment — 5-provider publication flow |
| 46 | `foundation/46-yaml-config-resolution.mmd` | flowchart | YAML Config Resolution — hierarchical merge |
| 47 | `foundation/47-publication-merge-sources.mmd` | sequence | Publication Composite — multi-source merge |
| 48 | `foundation/48-composite-phase-lifecycle.mmd` | state | Composite Pipeline FSM — 10-state lifecycle |
| 49 | `foundation/49-composite-runner-class.mmd` | class | CompositePipelineRunner — component diagram |
| 50 | `foundation/50-exception-hierarchy.mmd` | flowchart | Exception Hierarchy — BioETLError full tree |

---

## Colour Scheme

| Layer          | Colour | Fill      | Border    |
|----------------|--------|-----------|-----------|
| Domain         | Lavender | `#F5F3FF` | `#7C3AED` |
| Application    | Mint     | `#F0FDF4` | `#16A34A` |
| Infrastructure | Rose     | `#FFF1F2` | `#DC2626` |
| Interfaces     | Blue     | `#EFF6FF` | `#2563EB` |
| Composition    | Orange   | `#FFF7ED` | `#EA580C` |
| External       | Slate    | `#F8FAFC` | `#475569` |

### Medallion Layers

| Layer      | Fill      | Border    |
|------------|-----------|-----------|
| Bronze     | `#FFF7ED` | `#EA580C` |
| Silver     | `#F8FAFC` | `#475569` |
| Gold       | `#FEFCE8` | `#CA8A04` |
| Quarantine | `#FFF1F2` | `#DC2626` |

---

## Rendering

### Prerequisites

```bash
# Mermaid CLI (required)
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

### Quick start

```bash
# Render ALL diagrams (SVG + PNG) with custom theme
make render-diagrams

# SVG only (faster)
make render-diagrams-svg

# Or run the script directly
bash docs/02-architecture/mmd-diagrams/render.sh

# Single diagram with theme
mmdc -i docs/02-architecture/mmd-diagrams/architecture/01-high-level-hexagonal.mmd \
     -o output.svg \
     -c docs/02-architecture/mmd-diagrams/theme/mermaid-config.json \
     --cssFile docs/02-architecture/mmd-diagrams/theme/custom.css
```

### Render options

```bash
# Filter by name glob
bash docs/02-architecture/mmd-diagrams/render.sh --filter "01-*"

# Single directory only
bash docs/02-architecture/mmd-diagrams/render.sh --dir docs/02-architecture/mmd-diagrams/architecture

# Adjust PNG resolution
bash docs/02-architecture/mmd-diagrams/render.sh --scale 4 --width 3200 --height 2400

# CI mode (Puppeteer sandbox disabled)
bash docs/02-architecture/mmd-diagrams/render.sh --puppeteer /tmp/puppeteer-config.json

# Syntax validation (shows explicit hint if Chrome runtime is missing)
bash scripts/validate_mermaid_syntax.sh --puppeteer /tmp/puppeteer-config.json
```

### Output layout

```
docs/02-architecture/mmd-diagrams/
  architecture/
    *.mmd           # source diagrams (18)
    svg/*.svg       # rendered vector (scalable)
    png/*.png       # rendered raster (300 DPI)
  class-diagrams/
    *.mmd           # source diagrams (16)
    svg/*.svg
    png/*.png
  foundation/
    *.mmd           # source diagrams (59)
    svg/*.svg
    png/*.png
  theme/
    mermaid-config.json   # colours, fonts, spacing
    custom.css            # fine-tuned SVG styling
  render.sh               # unified render script
  README.md               # this file
```

### CI/CD

Diagrams are validated and rendered automatically in GitHub Actions
(`.github/workflows/docs.yml`). Rendered SVG/PNG are uploaded as build artifacts.
A drift check warns when `.mmd` sources change without re-rendering.

---

## Size Normalization

Use `scripts/uniform_diagram_sizes.py` to normalize class/flowchart object sizes:

```bash
# Check normalization drift
python3 scripts/uniform_diagram_sizes.py --check

# Fix specific files
python3 scripts/uniform_diagram_sizes.py --fix -f docs/02-architecture/mmd-diagrams/class-diagrams/07-application-core-services.mmd
```

Grouped diagrams support width strategy override:

- `%% @uniform-width global` (default): one shared width across groups.
- `%% @uniform-width group`: group-local widths to reduce excessive `&nbsp;` padding.

---

## Validation Rules

`scripts/lint_diagrams.py` enforces:

| Rule | Description | Severity |
|------|-------------|----------|
| META-001 | Missing `@version`/`@date`/`@type`/`@level` in `.mmd` | WARN |
| META-002 | Missing `%% View:` in `.mmd` view-file | WARN |
| COLOUR-001 | Deprecated pre-ADR palette in `style`/`classDef` | ERROR |
| COLOUR-002 | Emoji in subgraph labels | ERROR |
| SIZE-001 | `@nodes > 35` | ERROR |
| SIZE-002 | `@nodes > 20` | WARN |
| LAYOUT-001 | `flowchart/graph` with `@nodes > 20` without ELK init | WARN |
| LAYOUT-002 | `flowchart/graph` with `@nodes > 40` without ELK init | ERROR |
| GRAPH-001 | Orphan nodes (defined but not in any edge) | WARN |

Node-size exceptions in current lint implementation:
- `*-full.mmd` reference views are exempt from `SIZE-001`/`SIZE-002`.
- `00-legend*` files are exempt from `SIZE-001`/`SIZE-002`.

### Orphan Node Detection (GRAPH-001)

`scripts/prune-orphan-nodes.py` detects nodes defined in a diagram but not
participating in any edge or message.

**Applies to:** `flowchart` / `graph` and `sequenceDiagram` only.
**Skipped:** `classDiagram`, `stateDiagram`, `erDiagram`, `mindmap`, legend files.

```bash
# Report orphans (CI mode)
python scripts/prune-orphan-nodes.py --check

# Machine-readable output
python scripts/prune-orphan-nodes.py --check --json

# Remove confirmed garbage orphans (in-place)
python scripts/prune-orphan-nodes.py --fix

# Exempt all current orphans (one-time grandfathering)
python scripts/prune-orphan-nodes.py --grandfather
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
