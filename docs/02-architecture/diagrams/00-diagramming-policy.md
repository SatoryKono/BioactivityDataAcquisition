# Diagramming Policy

*Synced with RULES.md v5.10 (2026-01-05)*

## Overview

This document defines standards for creating, maintaining, and versioning architecture diagrams in the BioETL project.

---

## 1. General Principles

### 1.1 Text-First Approach (MUST)

- **Primary format**: Mermaid or PlantUML (text-based)
- **Rationale**: Version control friendly, diff-able, reviewable in PRs
- **Binary images**: Generated artifacts only, NOT committed to git

### 1.2 Single Responsibility (MUST)

- **One diagram per file**
- **One concept per diagram** (avoid overloading)
- **Clear scope** defined in diagram title

### 1.3 Consistency (SHOULD)

- Use consistent notation across all diagrams
- Follow naming conventions from RULES.md §2
- Reference RULES.md sections where applicable

---

## 2. File Organization

### 2.1 Directory Structure

```
docs/02-architecture/diagrams/
├── 00-diagramming-policy.md     # This file
├── 01-high-level.mermaid        # System overview
├── 02-medallion.mermaid         # Data flow layers
├── 03-pipeline-sequence.mermaid # Pipeline execution
├── 04-error-flow.mermaid        # Error handling
├── 05-layers-interaction.mermaid # Layer interaction
├── 05-locking.mermaid           # Concurrency
├── 06-pipeline-execution.mermaid # Detailed execution
└── 07-medallion-flow.mermaid    # Data flow through layers
```

### 2.2 Naming Convention (MUST)

- Format: `NN-<topic>.mermaid`
- Examples:
  - `01-high-level.mermaid`
  - `03-pipeline-sequence.mermaid`
- Prefix `NN-` for ordering
- Topic in kebab-case
- Extension: `.mermaid` (standardized)

---

## 3. Format Standards

### 3.1 Mermaid (Preferred)

Use for:

- Flowcharts
- Sequence diagrams (simple)
- Class diagrams
- State diagrams

```mermaid
graph TD
    A[Bronze] --> B[Silver]
    B --> C[Gold]
    B --> D[Quarantine]
```

### 3.2 PlantUML

Use for:

- Complex sequence diagrams
- Component diagrams
- Deployment diagrams

```plantuml
@startuml
actor User
participant CLI
participant Pipeline
User -> CLI: run --pipeline chembl_activity
CLI -> Pipeline: execute()
@enduml
```

### 3.3 ASCII Art

Use for:

- Inline documentation in markdown
- Quick sketches
- README visualizations

```
┌─────────┐     ┌─────────┐     ┌─────────┐
│ Bronze  │────►│ Silver  │────►│  Gold   │
└─────────┘     └─────────┘     └─────────┘
```

---

## 4. Content Guidelines

### 4.1 Required Elements

Every diagram MUST include:

- **Title**: Clear description of what's shown
- **Legend**: If using custom symbols or colors
- **RULES.md reference**: Link to relevant sections

### 4.2 Labeling (MUST)

- Use consistent terminology from Glossary (RULES.md)
- Include RULES.md section references where applicable
- Example: `Lock Acquire (§3.3)`

### 4.3 Colors (SHOULD)

Recommended color scheme:
| Element | Color | Hex |
|---------|-------|-----|
| Bronze Layer | Orange | #FFA500 |
| Silver Layer | Silver | #C0C0C0 |
| Gold Layer | Gold | #FFD700 |
| Error/Quarantine | Red | #FF6B6B |
| Success | Green | #4CAF50 |
| External | Blue | #2196F3 |

---

## 5. Maintenance

### 5.1 Update Triggers (MUST)

Update diagrams when:

- Architecture changes (new layers, components)
- Pipeline flow modifications
- New error handling patterns
- Infrastructure changes
- Breaking changes (§7.1)

### 5.2 Review Process (SHOULD)

- Include diagram updates in same PR as code changes
- Reviewer verifies diagram accuracy
- Check RULES.md compliance

### 5.3 Staleness Detection

- Review all diagrams quarterly
- Mark outdated diagrams with `<!-- NEEDS UPDATE -->`
- Track in `../../00-map.md`

---

## 6. Tools

### 6.1 Recommended Editors

| Tool                        | Format   | Notes                              |
|-----------------------------|----------|------------------------------------|
| VS Code + Mermaid Extension | Mermaid  | Live preview                       |
| PlantUML Server             | PlantUML | Docker: `plantuml/plantuml-server` |
| Mermaid Live Editor         | Mermaid  | https://mermaid.live               |

### 6.2 CI Integration (SHOULD)

```yaml
# .github/workflows/docs.yml
- name: Validate Mermaid
  run: npx @mermaid-js/mermaid-cli -i docs/**/*.mermaid
```

---

## 7. Diagram Catalog

| ID | Name                    | Format   | Covers            |
|----|-------------------------|----------|-------------------|
| 01 | High-Level Architecture | Mermaid  | §1.1 Layers       |
| 02 | Medallion Flow          | Mermaid  | §2.1 Data Flow    |
| 03 | Pipeline Sequence       | PlantUML | §3 Execution      |
| 04 | Error Handling          | Mermaid  | §3.1 Errors       |
| 05 | Locking                 | PlantUML | §3.3 Concurrency  |
| 06 | Class Diagram           | Mermaid  | Domain Objects    |
| 07 | Deployment              | Mermaid  | §5.6 Environments |

---

## 8. Examples

### 8.1 Mermaid Flowchart

```mermaid
flowchart TD
    subgraph Extract ["Extract (§2.1)"]
        A[API Client] --> B[Bronze Writer]
    end

    subgraph Transform ["Transform (§2.8)"]
        B --> C[Normalizer]
        C --> D[Hash Service]
    end

    subgraph Load ["Load (§3.3)"]
        D --> E{Lock Valid?}
        E -->|Yes| F[Delta Writer]
        E -->|No| G[Abort]
    end
```

### 8.2 PlantUML Sequence

```plantuml
@startuml
title Pipeline Lock Acquisition (§3.3)

participant Worker
participant Redis
participant DeltaLake

Worker -> Redis: SETNX lock:chembl_activity
Redis --> Worker: OK

loop Every 30s
    Worker -> Redis: EXPIRE (heartbeat)
end

Worker -> Redis: GET lock (validate owner)
Redis --> Worker: owner_id matches

Worker -> DeltaLake: write()

Worker -> Redis: DEL lock
@enduml
```

---

## Related Documents

- [00-rules-summary.md](../../00-project_rules/00-rules-summary.md) - Project rules summary
- [00-map.md](../../00-map.md) - Project navigator
