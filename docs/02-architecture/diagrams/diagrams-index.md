# BioETL Architecture Diagrams

*Updated: 2026-01-05*

This directory contains 34 Mermaid diagram source files documenting the BioETL architecture.

## Diagram Overview

| # | File | Description |
|---|------|-------------|
| 01a | `01-full-system-component.mermaid` | Full system component diagram (C4-style) |
| 01b | `01-high-level.mermaid` | High-level system overview |
| 02a | `02-full-medallion-data-flow.mermaid` | Medallion architecture data flow (detailed) |
| 02b | `02-medallion.mermaid` | Medallion architecture (simplified) |
| 03a | `03-pipeline-execution-happy-path.mermaid` | Pipeline execution sequence (happy path) |
| 03b | `03-pipeline-sequence.mermaid` | Pipeline sequence diagram |
| 04a | `04-domain-layer-class-diagram.mermaid` | Domain layer ports, entities, config |
| 04b | `04-error-flow.mermaid` | Error handling flow |
| 05a | `05-layers-interaction.mermaid` | Layer interaction diagram |
| 05b | `05-locking.mermaid` | Locking mechanism |
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
| 12 | `12-full-aws-deployment.mermaid` | AWS deployment architecture (reference) |
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
| 23 | `23-delta-lake-writer-class.mermaid` | DeltaWriter class diagram |
| 24 | `24-hash-service-class.mermaid` | Hash service class diagram |
| 25 | `25-circuit-breaker-observer-class.mermaid` | CircuitBreaker class diagram |

## Rendering to PNG

### Option 1: Mermaid CLI (Recommended)

```bash
# Install mermaid-cli
npm install -g @mermaid-js/mermaid-cli

# Render single diagram
mmdc -i 01-full-system-component.mermaid \
     -o 01-full-system-component.png \
     -w 1200 \
     -b transparent

# Render all diagrams
for f in *.mermaid; do
    mmdc -i "$f" -o "${f%.mermaid}.png" -w 1200 -b transparent
done
```

### Option 2: Python Script

Use the included `render_diagrams.py` script:

```bash
cd docs/architecture/diagrams
python render_diagrams.py
```

### Option 3: VS Code Extension

1. Install "Markdown Preview Mermaid Support" extension
2. Open any `.mermaid` file
3. Use the preview pane to view diagrams
4. Right-click to export as PNG/SVG

### Option 4: Online Viewer

1. Visit [Mermaid Live Editor](https://mermaid.live/)
2. Paste diagram content
3. Export as PNG/SVG

## Style Configuration

All diagrams use the following Mermaid theme configuration:

```
%%{init: {'theme': 'neutral', 'themeVariables': {'fontFamily': 'Inter, system-ui', 'lineWidth': '2'}}}%%
```

## Key Parameters Referenced

| Parameter | Value | Source |
|-----------|-------|--------|
| Lock TTL | 90s | RuntimeConfig |
| Heartbeat Interval | 30s | LockManager |
| Circuit Breaker Threshold | 5 failures | CircuitBreaker |
| Recovery Timeout | 300s (5 min) | CircuitBreaker |
| DQ Soft Threshold | 5% | DQConfig |
| DQ Hard Threshold | 20% | DQConfig |
| Bronze Retention | 90 days | MedallionPolicy |
| Quarantine Retention | 30 days | QuarantineWriter |
| Silver/Gold Retention | Permanent | StoragePort |

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                     INTERFACES LAYER                        │
│  CLI, Orchestration (Signal Handling)                       │
├─────────────────────────────────────────────────────────────┤
│                    APPLICATION LAYER                        │
│  PipelineRunner, PipelineExecutor, RecordProcessor,         │
│  Transformers, Services (Lock, Checkpoint, DQ)              │
├─────────────────────────────────────────────────────────────┤
│                      DOMAIN LAYER                           │
│  Ports (Protocols), Entities, Config, Types                 │
├─────────────────────────────────────────────────────────────┤
│                   INFRASTRUCTURE LAYER                      │
│  Adapters (ChEMBL, PubChem, UniProt, PubMed),               │
│  Storage (Bronze, Delta, Gold), Locking, Observability      │
├─────────────────────────────────────────────────────────────┤
│                    COMPOSITION LAYER                        │
│  Bootstrap, Factories, Registry (DI Container)              │
└─────────────────────────────────────────────────────────────┘
```

## Validation

After rendering, validate diagrams against:

- [ ] Class names match `src/bioetl/` codebase
- [ ] Lock parameters: TTL=90s, Heartbeat=30s
- [ ] Circuit Breaker: threshold=5, timeout=300s
- [ ] Retention: Bronze=90d, Silver=permanent, Quarantine=30d
