______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-07-28'

______________________________________________________________________

# ADR-040 Architecture Diagram Compliance Map

Maps issue #6543 required diagram themes to **existing** ADR-040-governed sources under `docs/02-architecture/diagrams/`.

**Policy and governance:** [ADR-040](../decisions/ADR-040-diagram-governance.md) · **Index:** [README.md](README.md)

## ADR-040 requirements (summary)

| Requirement | How BioETL meets it |
| --- | --- |
| Mermaid sources | Canonical `.mmd` under `architecture/`, `foundation/`, `class-diagrams/`, `sequence/`, `state-machines/`, `providers/` |
| Location | All under `docs/02-architecture/diagrams/` |
| Lint / quality | `python -m scripts.diagrams lint` · `make render-diagrams` · CI diagram jobs |
| Rendered baselines | Tracked `svg/` / `png/` next to families |
| Registry / catalog | [README.md](README.md#architecture-diagrams-52-core-49-52-added) |
| Views | `views/*.mermaid` presentation slices (not SSOT replacements) |

## Required themes → canonical sources

### 1. System / hexagonal architecture

| Theme | Canonical source | Notes |
| --- | --- | --- |
| Five-layer / hexagonal overview | `architecture/01-high-level-hexagonal.mmd`, `architecture/01a-hexagonal-overview.mmd` | Also `foundation/01-high-level.mmd` |
| Layer interaction | `foundation/05-layers-interaction.mmd` | |
| Ports & adapters | `architecture/13-port-protocol-contracts.mmd`, `foundation/26-hexagonal-ports-adapters.mmd` (if present under foundation) | Split views `13a`–`13f` |
| Dependency matrix | `architecture/02-layer-dependency-matrix.mmd` | |

### 2. Medallion architecture

| Theme | Canonical source |
| --- | --- |
| Bronze → Silver → Gold | `architecture/03-medallion-data-flow.mmd`, `03a-medallion-layers-overview.mmd`, `foundation/02-full-medallion-data-flow.mmd` |
| Delta write path | `foundation/19-delta-lake-write-sequence.mmd` |
| Storage layer | `architecture/06-storage-layer.mmd` |
| Quarantine | `architecture/36-quarantine-entry-review-resolution-and-discard-flow.mmd`, `sequence/05-quarantine-handling-sequence.mmd` |
| Checkpoint / lock | `architecture/18-lock-checkpoint-shutdown.mmd`, `sequence` + state-machines families |

### 3. Pipeline orchestration

| Theme | Canonical source |
| --- | --- |
| Execution flow | `architecture/04-pipeline-execution-flow.mmd`, `sequence/01-pipeline-execution-sequence.mmd` |
| Composite (ADR-026) | `architecture/08-composite-pipeline.mmd`, `sequence/02-composite-pipeline-sequence.mmd` |
| Control plane | `architecture/19-control-plane-artifacts.mmd`, `31-workflow-control-plane-manifest-and-ledger-publication.mmd` |
| Resilience / retry | `architecture/10-resilience-patterns.mmd`, `foundation/07-circuit-breaker-states.mmd` |

### 4. Provider integration

| Theme | Canonical source |
| --- | --- |
| Adapter hierarchy | `architecture/05-provider-adapter-hierarchy.mmd` |
| HTTP client (ADR-032) | `sequence/03-http-request-response-flow.mmd`, adapter package class diagrams |
| Provider-specific | `architecture/38`–`44-*.mmd`, `providers/chembl/*.mmd` |
| ChEMBL activity dataflow | `architecture/49-chembl-pipeline-activity-dataflow.mmd` |

### 5. Sequence diagrams (core five)

Documented in [README.md](README.md#sequence-diagrams-5-core-issue-6544):

1. `sequence/01-pipeline-execution-sequence.mmd`
2. `sequence/02-composite-pipeline-sequence.mmd`
3. `sequence/03-http-request-response-flow.mmd`
4. `sequence/04-dq-validation-sequence.mmd`
5. `sequence/05-quarantine-handling-sequence.mmd`

### 6. State machines

Under `state-machines/` (pipeline lifecycle, retry, locks, recovery — see directory listing and foundation `05-pipeline-lifecycle-states.mmd`, `07-circuit-breaker-states.mmd`, `20-quarantine-record-states.mmd`).

## Verification commands

```bash
# Lint Mermaid sources against ADR-040 policy
python -m scripts.diagrams lint

# Optional: focused paths
python -m scripts.diagrams lint docs/02-architecture/diagrams/architecture
python -m scripts.diagrams lint docs/02-architecture/diagrams/sequence

# Render baselines (when regenerating)
make render-diagrams
# or
python -m scripts.diagrams  # see scripts.diagrams --help
```

**Acceptance posture for #6543:** required themes are covered by the existing governed catalog; this map is the navigation SSOT so contributors do not invent parallel diagram trees. Prefer updating canonical `.mmd` only when architecture changes—not for cosmetic re-homing.

## See also

- [Architecture overview](../00-overview.md)
- [ADR Decision Matrix](../../03-guides/cheatsheets/adr-matrix.md)
- [Rendering workflow](README.md#rendering)
