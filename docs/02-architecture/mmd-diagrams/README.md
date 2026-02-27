# BioETL Architecture & Class Diagrams

*Canonical diagram location — all `.mermaid` sources live here.*

> **Governance:** [ADR-040 — Diagram Governance and Layout Policy](../decisions/ADR-040-diagram-governance.md)
> Colour scheme, linkStyle differentiation, view decomposition rules, CI validation — all defined in ADR-040.

All diagrams are in [Mermaid](https://mermaid.js.org/) format (`.mermaid` files).
Render them with any Mermaid-compatible viewer, IDE plugin, or the [Mermaid Live Editor](https://mermaid.live/).

---

## Architecture Diagrams (18)

| # | Diagram | File | Description |
|---|---------|------|-------------|
| 1 | High-Level Hexagonal Architecture | `architecture/01-high-level-hexagonal.mermaid` | Full system overview: layers, external systems, dependency directions |
| 2 | Layer Dependency Matrix | `architecture/02-layer-dependency-matrix.mermaid` | ARCH-001 import boundary enforcement |
| 3 | Medallion Data Flow | `architecture/03-medallion-data-flow.mermaid` | Bronze → Silver → Gold pipeline with DQ and quarantine |
| 4 | Pipeline Execution Flow | `architecture/04-pipeline-execution-flow.mermaid` | Sequence diagram: preflight → lock → execute → postrun → cleanup |
| 5 | Provider Adapter Hierarchy | `architecture/05-provider-adapter-hierarchy.mermaid` | All 7 provider adapters, base classes, mixins, decorators |
| 6 | Storage Layer | `architecture/06-storage-layer.mermaid` | Bronze/Silver/Gold writers, Delta Lake, metadata, validation |
| 7 | Data Quality System | `architecture/07-dq-system.mermaid` | DQ monitoring, analysis, anomaly detection, reporting |
| 8 | Composite Pipeline | `architecture/08-composite-pipeline.mermaid` | Seed → dependencies → enrichers (parallel) → merge with FSM |
| 9 | Observability Stack | `architecture/09-observability-stack.mermaid` | Logging, metrics, tracing: ports and implementations |
| 10 | Resilience Patterns | `architecture/10-resilience-patterns.mermaid` | Circuit breaker, rate limiter, retry, health checks |
| 11 | Configuration System | `architecture/11-configuration-system.mermaid` | YAML configs → loaders → Pydantic schemas → domain config |
| 12 | Bootstrap / DI Container | `architecture/12-bootstrap-di-container.mermaid` | Composition root: factories, assembly, wiring |
| 13 | Port/Protocol Contracts | `architecture/13-port-protocol-contracts.mermaid` | All 29 domain ports mapped to their implementations |
| 14 | CLI / Interface Layer | `architecture/14-cli-interface-layer.mermaid` | CLI commands, routing to application services |
| 15 | BatchExecutor Internals | `architecture/15-batch-executor-internals.mermaid` | Executor composition: transformer, writer, memory, metrics |
| 16 | Transformer Hierarchy | `architecture/16-transformer-hierarchy.mermaid` | Template Method pattern, all provider transformers, extractors |
| 17 | Security, PII & Audit | `architecture/17-security-pii-audit.mermaid` | PII hashing, salt rotation, audit trail |
| 18 | Lock, Checkpoint & Shutdown | `architecture/18-lock-checkpoint-shutdown.mermaid` | Fencing tokens, safety guard, graceful shutdown |

## Decomposed Architecture Diagrams

Parent diagrams remain canonical references. Sub-files provide focused, low-density views for review and onboarding.

| Parent (canonical) | Decomposed sub-files |
|---|---|
| `architecture/01-high-level-hexagonal.mermaid` | `architecture/01a-hexagonal-overview.mermaid`, `architecture/01b-hexagonal-domain-app.mermaid`, `architecture/01c-hexagonal-infra-comp.mermaid` |
| `architecture/05-provider-adapter-hierarchy.mermaid` | `architecture/05a-adapter-hierarchy-base.mermaid`, `architecture/05b-adapter-hierarchy-providers.mermaid` |
| `architecture/12-bootstrap-di-container.mermaid` | `architecture/12a-bootstrap-factories.mermaid`, `architecture/12b-bootstrap-wiring.mermaid` |
| `architecture/13-port-protocol-contracts.mermaid` | `architecture/13a-port-contracts-data-sources.mermaid`, `architecture/13b-port-contracts-storage.mermaid`, `architecture/13c-port-contracts-observability.mermaid`, `architecture/13d-port-contracts-services.mermaid` |

## Class Diagrams (14 families)

| # | Family | File | Description |
|---|--------|------|-------------|
| 1 | Domain Ports | `class-diagrams/01-domain-ports.mermaid` | All 29 Protocol interfaces with method signatures |
| 3 | Value Objects | `class-diagrams/03-value-objects.mermaid` | BronzeWriteResult, SilverWriteResult, FencingToken, etc. |
| 4 | Types & Enums | `class-diagrams/04-types-enums.mermaid` | RunType, PublicationType, HealthStatus, NewTypes |
| 5 | Exceptions | `class-diagrams/05-exceptions.mermaid` | BioETLError hierarchy: Critical, Recoverable, DataQuality |
| 6 | Configuration | `class-diagrams/06-config-classes.mermaid` | PipelineConfig, RuntimeConfig, CompositeConfig |
| 7 | Application Core | `class-diagrams/07-application-core-services.mermaid` | PipelineRunner, BatchExecutor, LockManager |
| 8 | Application Services | `class-diagrams/08-application-services.mermaid` | DQ, Health, Export, Vacuum, Quarantine services |
| 9 | Transformers | `class-diagrams/09-transformers.mermaid` | BaseTransformer → ChEMBL/Publication/UniProt/PubChem |
| 10 | Adapters | `class-diagrams/10-adapters.mermaid` | BaseHttpAdapter, all provider adapters, resilience |
| 11 | Storage | `class-diagrams/11-storage.mermaid` | BronzeWriter, SilverWriter, GoldWriter, DeltaReader |
| 13 | Domain Services | `class-diagrams/13-domain-services.mermaid` | IdentityService, Normalization, UnitConverter |
| 14 | Observability | `class-diagrams/14-observability.mermaid` | Logger, Metrics, Tracing implementations |
| 15 | Extractors | `class-diagrams/15-extractors.mermaid` | BaseFieldExtractor, PubMed & UniProt extractors |
| 16 | Factories & Bootstrap | `class-diagrams/16-factories-bootstrap.mermaid` | DataSourceRegistry, TransformerFactory, RunnerBuilder |

## Foundation Diagrams (55)

Historical/foundational diagrams consolidated from `docs/02-architecture/diagrams/`.

### Foundation 01–25

| # | File | Description |
|---|------|-------------|
| 01a | `foundation/01-full-system-component.mermaid` | Full system component diagram (C4-style) |
| 01b | `foundation/01-high-level.mermaid` | High-level system overview |
| 02a | `foundation/02-full-medallion-data-flow.mermaid` | Medallion architecture data flow (detailed) |
| 03a | `foundation/03-pipeline-execution-happy-path.mermaid` | Pipeline execution sequence (happy path) |
| 04a | `foundation/04-domain-layer-class-diagram.mermaid` | Domain layer ports, entities, config |
| 04b | `foundation/04-error-flow.mermaid` | Error handling flow |
| 05a | `foundation/05-layers-interaction.mermaid` | Layer interaction diagram |
| 05c | `foundation/05-pipeline-lifecycle-states.mermaid` | Pipeline state machine |
| 06a | `foundation/06-application-layer-class-diagram.mermaid` | Application layer classes |
| 06b | `foundation/06-pipeline-execution.mermaid` | Pipeline execution flow |
| 07a | `foundation/07-circuit-breaker-states.mermaid` | Circuit breaker state machine |
| 07b | `foundation/07-medallion-flow.mermaid` | Medallion data flow |
| 08a | `foundation/08-complete-etl-workflow.mermaid` | Complete ETL workflow |
| 08b | `foundation/08-domain-ddd.mermaid` | Domain-driven design diagram |
| 09 | `foundation/09-full-er-diagram.mermaid` | Entity-relationship diagram |
| 10 | `foundation/10-infrastructure-layer-class-diagram.mermaid` | Infrastructure layer classes |
| 11 | `foundation/11-lock-acquisition-sequence.mermaid` | Lock acquisition sequence |
| 12 | `foundation/12-local-deployment-architecture.mermaid` | Local deployment architecture (ADR-010) |
| 13 | `foundation/13-domain-models-relationship.mermaid` | Domain model relationships |
| 14 | `foundation/14-provider-health-states.mermaid` | Provider health states |
| 15 | `foundation/15-dq-check-workflow.mermaid` | Data quality check workflow |
| 16 | `foundation/16-memory-lock-class.mermaid` | MemoryLock class diagram |
| 17 | `foundation/17-pipeline-hierarchy.mermaid` | Pipeline/Transformer hierarchy |
| 18 | `foundation/18-bronze-write-sequence.mermaid` | Bronze write sequence |
| 19 | `foundation/19-delta-lake-write-sequence.mermaid` | Delta Lake write sequence |
| 20 | `foundation/20-quarantine-record-states.mermaid` | Quarantine record states |
| 21 | `foundation/21-activity-entity-data-flow.mermaid` | Activity entity data flow |
| 22 | `foundation/22-client-api-request-sequence.mermaid` | Client API request sequence |
| 23 | `foundation/23-silver-writer-class.mermaid` | SilverWriter class diagram |
| 24 | `foundation/24-hash-service-class.mermaid` | Hash service class diagram |
| 25 | `foundation/25-circuit-breaker-observer-class.mermaid` | CircuitBreaker class diagram |

### Foundation 26–50 (TOP-25 Architecture)

| # | File | Type | Description |
|---|------|------|-------------|
| 26 | `foundation/26-hexagonal-ports-adapters.mermaid` | flowchart | Hexagonal Architecture — all 24 ports mapped to adapters |
| 27 | `foundation/27-import-matrix-enforcement.mermaid` | flowchart | ARCH-001 Import Matrix — 5-layer dependency rules |
| 28 | `foundation/28-composition-root-di-graph.mermaid` | flowchart | Composition Root DI Graph — full DI assembly |
| 29 | `foundation/29-composite-pipeline-workflow.mermaid` | sequence | Composite Pipeline (ADR-026) — Seed→Deps→FanOut→Merge→Gold |
| 31 | `foundation/31-pipeline-run-lifecycle.mermaid` | state | PipelineRun Aggregate FSM |
| 32 | `foundation/32-single-record-journey.mermaid` | flowchart | Single Record Journey — API→Bronze→Transform→Silver→Gold |
| 33 | `foundation/33-cli-run-interaction.mermaid` | sequence | CLI → PipelineRunnerService interaction |
| 34 | `foundation/34-batch-processing-flow.mermaid` | sequence | Batch Processing — BatchExecutor cycle |
| 36 | `foundation/36-architecture-principles-mindmap.mermaid` | mindmap | Architecture Principles Mindmap |
| 37 | `foundation/37-cli-entry-full-chain.mermaid` | sequence | CLI Entry → Exit Code full chain |
| 38 | `foundation/38-runtime-assembly-sequence.mermaid` | sequence | Runtime Assembly — phases 1–8 |
| 39 | `foundation/39-medallion-invariants.mermaid` | flowchart | Medallion Invariants — ARCH-007 RunType clear policy |
| 40 | `foundation/40-application-core-collaboration.mermaid` | flowchart | Application Core — PipelineRunner orchestrating services |
| 41 | `foundation/41-error-classification-tree.mermaid` | flowchart | Error Classification — HTTP→Domain→Actions |
| 42 | `foundation/42-pipeline-runner-class.mermaid` | class | PipelineRunner Class — all 14 DI dependencies |
| 43 | `foundation/43-fan-out-fan-in-pattern.mermaid` | sequence | Fan-Out/Fan-In — asyncio.gather parallel enrichment |
| 44 | `foundation/44-cross-provider-enrichment.mermaid` | flowchart | Cross-Provider Enrichment — 5-provider publication flow |
| 46 | `foundation/46-yaml-config-resolution.mermaid` | flowchart | YAML Config Resolution — hierarchical merge |
| 47 | `foundation/47-publication-merge-sources.mermaid` | sequence | Publication Composite — multi-source merge |
| 48 | `foundation/48-composite-phase-lifecycle.mermaid` | state | Composite Pipeline FSM — 10-state lifecycle |
| 49 | `foundation/49-composite-runner-class.mermaid` | class | CompositePipelineRunner — component diagram |
| 50 | `foundation/50-exception-hierarchy.mermaid` | flowchart | Exception Hierarchy — BioETLError full tree |

---

## Colour Scheme

| Layer          | Colour | Fill      | Border    |
|----------------|--------|-----------|-----------|
| Domain         | Purple | `#f3e5f5` | `#6a1b9a` |
| Application    | Green  | `#e8f5e9` | `#2e7d32` |
| Infrastructure | Red    | `#ffcdd2` | `#c62828` |
| Interfaces     | Blue   | `#e3f2fd` | `#1565c0` |
| Composition    | Orange | `#fff3e0` | `#e65100` |
| External       | Gray   | `#eceff1` | `#455a64` |

### Medallion Layers

| Layer      | Fill      | Border    |
|------------|-----------|-----------|
| Bronze     | `#fff3e0` | `#e65100` |
| Silver     | `#eceff1` | `#607d8b` |
| Gold       | `#fff8e1` | `#f9a825` |
| Quarantine | `#ffebee` | `#d32f2f` |

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
mmdc -i docs/02-architecture/mmd-diagrams/architecture/01-high-level-hexagonal.mermaid \
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
bash scripts/validate-mermaid-syntax.sh --puppeteer /tmp/puppeteer-config.json
```

### Output layout

```
docs/02-architecture/mmd-diagrams/
  architecture/
    *.mermaid           # source diagrams (18)
    svg/*.svg       # rendered vector (scalable)
    png/*.png       # rendered raster (300 DPI)
  class-diagrams/
    *.mermaid           # source diagrams (16)
    svg/*.svg
    png/*.png
  foundation/
    *.mermaid           # source diagrams (59)
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
A drift check warns when `.mermaid` sources change without re-rendering.

---

## Size Normalization

Use `scripts/uniform-diagram-sizes.py` to normalize class/flowchart object sizes:

```bash
# Check normalization drift
python3 scripts/uniform-diagram-sizes.py --check

# Fix specific files
python3 scripts/uniform-diagram-sizes.py --fix -f docs/02-architecture/mmd-diagrams/class-diagrams/07-application-core-services.mermaid
```

Grouped diagrams support width strategy override:

- `%% @uniform-width global` (default): one shared width across groups.
- `%% @uniform-width group`: group-local widths to reduce excessive `&nbsp;` padding.

---

## Validation Rules

`scripts/lint-diagrams.py` enforces:

| Rule | Description | Severity |
|------|-------------|----------|
| META-001 | Missing `@version`/`@date`/`@type`/`@level` in `.mermaid` | WARN |
| META-002 | Missing `%% View:` in `.mermaid` view-file | WARN |
| COLOUR-001 | Deprecated pre-ADR palette in `style`/`classDef` | ERROR |
| COLOUR-002 | Emoji in subgraph labels | ERROR |
| SIZE-001 | `@nodes > 35` | ERROR |
| SIZE-002 | `@nodes > 20` | WARN |
| LAYOUT-001 | `flowchart/graph` with `@nodes > 20` without ELK init | WARN |
| LAYOUT-002 | `flowchart/graph` with `@nodes > 40` without ELK init | ERROR |
| GRAPH-001 | Orphan nodes (defined but not in any edge) | WARN |

Node-size exceptions in current lint implementation:
- `*-full.mermaid` reference views are exempt from `SIZE-001`/`SIZE-002`.
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
