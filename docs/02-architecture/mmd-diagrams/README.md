# BioETL Architecture & Class Diagrams

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

## Class Diagrams (16 families)

| # | Family | File | Description |
|---|--------|------|-------------|
| 1 | Domain Ports | `class-diagrams/01-domain-ports.mmd` | All 29 Protocol interfaces with method signatures |
| 2 | Entities & Aggregates | `class-diagrams/02-entities-aggregates.mmd` | BaseEntity, Batch, PipelineRun, BatchRecord |
| 3 | Value Objects | `class-diagrams/03-value-objects.mmd` | BronzeWriteResult, SilverWriteResult, FencingToken, etc. |
| 4 | Types & Enums | `class-diagrams/04-types-enums.mmd` | RunType, PublicationType, HealthStatus, NewTypes |
| 5 | Exceptions | `class-diagrams/05-exceptions.mmd` | BioETLError hierarchy: Critical, Recoverable, DataQuality |
| 6 | Configuration | `class-diagrams/06-config-classes.mmd` | PipelineConfig, RuntimeConfig, CompositeConfig |
| 7 | Application Core | `class-diagrams/07-application-core-services.mmd` | PipelineRunner, BatchExecutor, LockManager |
| 8 | Application Services | `class-diagrams/08-application-services.mmd` | DQ, Health, Export, Vacuum, Quarantine services |
| 9 | Transformers | `class-diagrams/09-transformers.mmd` | BaseTransformer → ChEMBL/Publication/UniProt/PubChem |
| 10 | Adapters | `class-diagrams/10-adapters.mmd` | BaseHttpAdapter, all provider adapters, resilience |
| 11 | Storage | `class-diagrams/11-storage.mmd` | BronzeWriter, SilverWriter, GoldWriter, DeltaReader |
| 12 | Composite Pipeline | `class-diagrams/12-composite-pipeline.mmd` | Runner, coordinators, merger, FSM |
| 13 | Domain Services | `class-diagrams/13-domain-services.mmd` | IdentityService, Normalization, UnitConverter |
| 14 | Observability | `class-diagrams/14-observability.mmd` | Logger, Metrics, Tracing implementations |
| 15 | Extractors | `class-diagrams/15-extractors.mmd` | BaseFieldExtractor, PubMed & UniProt extractors |
| 16 | Factories & Bootstrap | `class-diagrams/16-factories-bootstrap.mmd` | DataSourceRegistry, TransformerFactory, RunnerBuilder |

---

## Rendering

### Prerequisites

```bash
# Mermaid CLI (required)
npm install -g @mermaid-js/mermaid-cli

# librsvg — high-quality SVG → PNG (recommended)
# macOS:
brew install librsvg
# Ubuntu/Debian:
sudo apt-get install librsvg2-bin
```

### Quick start

```bash
# Render ALL diagrams (SVG + PNG) with custom theme
bash docs/02-architecture/mmd-diagrams/render.sh

# SVG only (faster)
bash docs/02-architecture/mmd-diagrams/render.sh --svg-only

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
```

### Output layout

```
docs/02-architecture/mmd-diagrams/
  architecture/
    *.mmd           # source diagrams
    svg/*.svg       # rendered vector (scalable)
    png/*.png       # rendered raster (300 DPI)
  class-diagrams/
    *.mmd
    svg/*.svg
    png/*.png
  theme/
    mermaid-config.json   # colours, fonts, spacing
    custom.css            # fine-tuned SVG styling
  render.sh               # unified render script
```

### Theme customization

The custom theme in `theme/mermaid-config.json` uses the BioETL colour palette:

| Layer          | Fill      | Border    |
|----------------|-----------|-----------|
| Domain         | `#e8f5e9` | `#2e7d32` |
| Application    | `#e3f2fd` | `#1565c0` |
| Infrastructure | `#fff3e0` | `#e65100` |
| Composition    | `#f3e5f5` | `#6a1b9a` |
| Interfaces     | `#fce4ec` | `#b71c1c` |
| Bronze         | `#fff3e0` | `#e65100` |
| Silver         | `#eceff1` | `#607d8b` |
| Gold           | `#fff8e1` | `#f9a825` |
| Quarantine     | `#ffebee` | `#c62828` |

### CI/CD

Diagrams are validated and rendered automatically in GitHub Actions
(`.github/workflows/docs.yml`). Rendered SVG/PNG are uploaded as build artifacts.
