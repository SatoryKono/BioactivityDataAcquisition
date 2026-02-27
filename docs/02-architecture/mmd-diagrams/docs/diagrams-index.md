# BioETL Architecture Diagrams

*Updated: 2026-02-25*

> **Note:** All diagram sources live in [`docs/02-architecture/mmd-diagrams/`](../README.md).
> Canonical sources: `architecture/`, `class-diagrams/`, `foundation/` (`.mmd`).
> Decomposed views: `views/` (`.mermaid`).
> All new diagrams should be added as `.mmd` files.

В каталоге 59 исходных файлов диаграмм Mermaid, документирующих архитектуру BioETL.
Диаграммы 26–50 созданы на основе TOP-25 из 500 архитектурных предложений (см. `top-50-diagram-selection.md`).

## Diagram Views

Overloaded diagrams are decomposed into focused views in [`README.md`](./README.md)
and `./mermaid/`:

- `*-overview.mermaid` — key entities and primary relations (recommended first read)
- `*-domain.mermaid` — entities, domain services, and ports
- `*-infra.mermaid` — entities mapped to adapters and storage components
- `*-dataflow.mermaid` — Bronze → Silver → Gold data movement only
- `*-full.mermaid` — full reference source retained for traceability

Recommended onboarding order:

1. Overview views
2. Domain views
3. Infrastructure views
4. Data-flow views
5. Full reference views

## Diagram Overview

### Foundation Diagrams (01–25)

| # | File | Description |
|---|------|-------------|
| 01a | `01-full-system-component.mermaid` | Full system component diagram (C4-style) |
| 01b | `01-high-level.mermaid` | High-level system overview |
| 02a | `02-full-medallion-data-flow.mermaid` | Medallion architecture data flow (detailed) |
| 03a | `03-pipeline-execution-happy-path.mermaid` | Pipeline execution sequence (happy path) |
| 04a | `04-domain-layer-class-diagram.mermaid` | Domain layer ports, entities, config |
| 04b | `04-error-flow.mermaid` | Error handling flow |
| 05a | `05-layers-interaction.mermaid` | Layer interaction diagram |
| 05c | `05-pipeline-lifecycle-states.mermaid` | Pipeline state machine |
| 06a | `06-application-layer-class-diagram.mermaid` | Application layer classes |
| 06b | `06-pipeline-execution.mermaid` | Pipeline execution flow |
| 07a | `07-circuit-breaker-states.mermaid` | Circuit breaker state machine |
| 07b | `07-medallion-flow.mermaid` | Medallion data flow |
| 08a | `08-complete-etl-workflow.mermaid` | Complete ETL workflow |
| 08b | `08-domain-ddd.mermaid` | Domain-driven design diagram |
| 09 | `09-full-er-diagram.mermaid` | Entity-relationship diagram |
| 10 | `10-infrastructure-layer-class-diagram.mermaid` | Infrastructure layer classes |
| 11 | `11-lock-acquisition-sequence.mermaid` | Lock acquisition sequence |
| 12 | `12-local-deployment-architecture.mermaid` | Local deployment architecture (ADR-010 Local-Only) |
| 13 | `13-domain-models-relationship.mermaid` | Domain model relationships |
| 14 | `14-provider-health-states.mermaid` | Provider health states |
| 15 | `15-dq-check-workflow.mermaid` | Data quality check workflow |
| 16 | `16-memory-lock-class.mermaid` | MemoryLock class diagram |
| 17 | `17-pipeline-hierarchy.mermaid` | Pipeline/Transformer hierarchy |
| 18 | `18-bronze-write-sequence.mermaid` | Bronze write sequence |
| 19 | `19-delta-lake-write-sequence.mermaid` | Delta Lake write sequence |
| 20 | `20-quarantine-record-states.mermaid` | Quarantine record states |
| 21 | `21-activity-entity-data-flow.mermaid` | Activity entity data flow |
| 22 | `22-client-api-request-sequence.mermaid` | Client API request sequence |
| 23 | `23-silver-writer-class.mermaid` | SilverWriter class diagram |
| 24 | `24-hash-service-class.mermaid` | Hash service class diagram |
| 25 | `25-circuit-breaker-observer-class.mermaid` | CircuitBreaker class diagram |

### TOP-25 Architecture Diagrams (26–50)

Ranked by architectural importance (Priority score). PNG renderings in `png/` subdirectory.

| # | File | Type | Priority | Description |
|---|------|------|----------|-------------|
| 26 | `26-hexagonal-ports-adapters.mermaid` | flowchart | 9.38 | Hexagonal Architecture — all 24 ports mapped to adapter implementations |
| 27 | `27-import-matrix-enforcement.mermaid` | flowchart | 9.00 | ARCH-001 Import Matrix — 5-layer dependency rules with allowed/forbidden imports |
| 28 | `28-composition-root-di-graph.mermaid` | flowchart | 9.00 | Composition Root DI Graph — full dependency injection assembly |
| 29 | `29-composite-pipeline-workflow.mermaid` | sequenceDiagram | 8.94 | Composite Pipeline (ADR-026) — Seed→Deps→FanOut→Merge→Gold |
| 31 | `31-pipeline-run-lifecycle.mermaid` | stateDiagram | 8.81 | PipelineRun Aggregate FSM — PENDING→LOCKING→PREFLIGHT→…→COMPLETED/FAILED |
| 32 | `32-single-record-journey.mermaid` | flowchart | 8.75 | Single Record Journey — API→Bronze→Transform→Validate→Silver/Quarantine→Gold |
| 33 | `33-cli-run-interaction.mermaid` | sequenceDiagram | 8.69 | CLI → PipelineRunnerService full interaction sequence |
| 34 | `34-batch-processing-flow.mermaid` | sequenceDiagram | 8.63 | Batch Processing — BatchExecutor extract→transform→validate→write cycle |
| 36 | `36-architecture-principles-mindmap.mermaid` | mindmap | 8.50 | Architecture Principles Mindmap — all ADRs and design principles |
| 37 | `37-cli-entry-full-chain.mermaid` | sequenceDiagram | 8.44 | CLI Entry → Exit Code full chain with error handling |
| 38 | `38-runtime-assembly-sequence.mermaid` | sequenceDiagram | 8.38 | Runtime Assembly — assembly.py phases 1–8 factory orchestration |
| 39 | `39-medallion-invariants.mermaid` | flowchart | 8.31 | Medallion Invariants — ARCH-007 RunType clear policy (INCREMENTAL/BACKFILL/REBUILD) |
| 40 | `40-application-core-collaboration.mermaid` | flowchart | 8.25 | Application Core — PipelineRunner orchestrating all services |
| 41 | `41-error-classification-tree.mermaid` | flowchart | 8.19 | Error Classification — HTTP errors → Domain errors → Actions (retry/abort/quarantine) |
| 42 | `42-pipeline-runner-class.mermaid` | classDiagram | 8.13 | PipelineRunner Class — all 14 DI dependencies |
| 43 | `43-fan-out-fan-in-pattern.mermaid` | sequenceDiagram | 8.06 | Fan-Out/Fan-In — asyncio.gather parallel enrichment |
| 44 | `44-cross-provider-enrichment.mermaid` | flowchart | 8.00 | Cross-Provider Enrichment — 5-provider publication flow |
| 46 | `46-yaml-config-resolution.mermaid` | flowchart | 7.38 | YAML Config Resolution — hierarchical merge (defaults→provider→entity→inline) |
| 47 | `47-publication-merge-sources.mermaid` | sequenceDiagram | 7.38 | Publication Composite — multi-source merge with field priority resolution |
| 48 | `48-composite-phase-lifecycle.mermaid` | stateDiagram | 7.31 | Composite Pipeline FSM — CompositePipelineState 10-state lifecycle |
| 49 | `49-composite-runner-class.mermaid` | classDiagram | 7.31 | CompositePipelineRunner — component diagram with all services |
| 50 | `50-exception-hierarchy.mermaid` | flowchart | 7.25 | Exception Hierarchy — BioETLError full tree (Critical/Recoverable/DataQuality) |

## Deprecated / Historical

- Historical filename: `12-full-aws-deployment.mermaid` (deprecated naming).
- Active diagram: `12-local-deployment-architecture.mermaid` in `mermaid/`.
- Context source: [ADR-010 Local-Only Deployment](../../decisions/ADR-010-local-only-deployment.md).

## Definition of Done для новой диаграммы

- [ ] Добавлен исходник `.mmd` в `docs/02-architecture/mmd-diagrams/`.
- [ ] PNG/SVG генерируются через `render.sh` (gitignored).
- [ ] Добавлена строка в `README.md` или этот индекс.
- [ ] На архитектурной странице `docs/02-architecture/*.md` есть контекстный абзац со ссылкой на диаграмму.

## Правило поддержки актуальности индекса

При добавлении/удалении `*.mermaid` файлов в `mermaid/` обязательно обновлять таблицу **Diagram Overview** в том же PR.

Полуавтоматическая проверка:

```bash
cd docs/02-architecture/diagrams
python - <<'PY'
from pathlib import Path
import re

idx = Path("diagrams-index.md").read-text(encoding="utf-8")
table-files = sorted(set(re.findall(r"`([^`]+\.mermaid)`", idx)))
disk-files = sorted(p.name for p in Path("mermaid").glob("*.mermaid"))

missing-in-index = sorted(set(disk-files) - set(table-files))
missing-on-disk = sorted(set(table-files) - set(disk-files))

print("Missing in index:", missing-in-index or "none")
print("Missing on disk:", missing-on-disk or "none")
PY
```

## Rendering to PNG

```bash
cd docs/02-architecture/diagrams
./render-diagrams.sh
```
