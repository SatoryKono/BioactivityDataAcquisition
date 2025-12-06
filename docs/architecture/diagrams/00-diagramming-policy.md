# Diagramming Policy

## 1. Purpose

This document defines how to create, update, and store diagrams used to document BioETL architecture and pipeline operation. Diagrams are part of the architecture and must be kept in sync with code changes.

---

## 2. General Requirements

### 2.1 Storage

Diagrams live in the repository:

- `docs/architecture/diagrams/`
- `docs/pipelines/<provider>/<entity>/diagrams/`

Images (PNG/SVG) are mirrors only. Primary source must be text: **Mermaid** or **PlantUML**.

### 2.2 Format and Tools

- Primary format: **Mermaid**.  
- Allowed alternative: **PlantUML**.  
- PRs must include the text source (`*.mmd`, `*.puml`).

### 2.3 Freshness

- Any change to architecture, protocols, pipelines, or API clients requires diagram updates.  
- Missing or stale diagrams for architecture changes is a PR blocker.

### 2.4 Filenames

Use kebab-case:

- `activity-chembl-class.mmd`
- `activity-chembl-sequence-full-run.mmd`
- `pipeline-run-error-flowchart.mmd`

One file — one diagram.

### 2.5 Level of Detail

- Show components, interactions, and structure, not every line of code.
- Diagrams must be understandable to a new developer.

### 2.6 Style and Readability (all Mermaid/PlantUML)

- Fonts: primary elements ≥ 22 pt; secondary elements/labels ≥ 18 pt.
- Palette: neutral light grays/pastels with readable contrast; no neon/acid colors.
- Lines: stroke ≥ 1.5 px, single arrow style; no decorative waves/dashes without meaning.
- Layout: main flow vertical or horizontal; avoid spirals/chaos; keep even spacing.
- Text: short labels, no obscure abbreviations; comments go into notes, not shapes.
- Export: PNG/SVG must stay readable on a 13–15" screen without zoom; avoid endless 5000 px widths.
- Pre-merge check: readability, no eye-burning colors, font sizes respected.

### 2.7 Base reusable palette (Mermaid)

```mermaid
%% Shared palette
classDef primary   fill:#f5f5f5,stroke:#444,stroke-width:1.5px,color:#111,font-size:22px;
classDef secondary fill:#e3e7ec,stroke:#555,stroke-width:1.2px,color:#111,font-size:18px;
classDef group     fill:#e6ecef,stroke:#333,stroke-width:1.5px,color:#111,font-size:22px;

linkStyle default stroke:#666,stroke-width:1.2px,color:#111;
```

Reuse this block across diagrams to keep palette and typography uniform.

### 2.8 Type-specific Mermaid templates

#### Component diagram (flowchart)

```mermaid
classDef componentPrimary   fill:#f5f5f5,stroke:#444,stroke-width:1.5px,color:#111,font-size:22px;
classDef componentSecondary fill:#e3e7ec,stroke:#555,stroke-width:1.2px,color:#111,font-size:18px;
classDef external           fill:#dde7f2,stroke:#44546a,stroke-width:1.5px,color:#111,font-size:22px;
linkStyle default stroke:#666,stroke-width:1.2px,color:#111;
```

- componentPrimary: ключевые компоненты приложения.
- componentSecondary: вспомогательные/внутренние сервисы.
- external: внешние системы с мягким синим оттенком.

#### Class diagram

```mermaid
classDef domainPrimary   fill:#f5f5f5,stroke:#444,stroke-width:1.5px,color:#111,font-size:22px;
classDef domainSecondary fill:#e3e7ec,stroke:#555,stroke-width:1.2px,color:#111,font-size:18px;
classDef interface       fill:#dde7f2,stroke:#44546a,stroke-width:1.5px,color:#111,font-size:22px;
```

- domainPrimary: ключевые доменные сущности.
- domainSecondary: сервисы, репозитории, валидаторы.
- interface: ABC/Protocol/интерфейсы.

#### Sequence diagram

```mermaid
classDef actorPrimary   fill:#f5f5f5,stroke:#444,stroke-width:1.5px,color:#111,font-size:22px;
classDef actorSecondary fill:#e3e7ec,stroke:#555,stroke-width:1.2px,color:#111,font-size:18px;
classDef actorExternal  fill:#dde7f2,stroke:#44546a,stroke-width:1.5px,color:#111,font-size:22px;
```

Применяйте классы к participant: основные акторы — actorPrimary, внутренние сервисы — actorSecondary, внешние системы — actorExternal.

#### Flowchart (workflow)

```mermaid
classDef stepPrimary   fill:#f5f5f5,stroke:#444,stroke-width:1.5px,color:#111,font-size:22px;
classDef stepDecision  fill:#e6ecef,stroke:#333,stroke-width:1.5px,color:#111,font-size:22px;
classDef stepSecondary fill:#e3e7ec,stroke:#555,stroke-width:1.2px,color:#111,font-size:18px;
classDef stepTerminal  fill:#dde7f2,stroke:#44546a,stroke-width:1.5px,color:#111,font-size:22px;
linkStyle default stroke:#666,stroke-width:1.2px,color:#111;
```

- stepPrimary: основные шаги процесса.
- stepDecision: ветвления и условия.
- stepSecondary: подготовительные/второстепенные действия.
- stepTerminal: конечные состояния.

---

## 3. Class Diagram Policy

### 3.1 When Needed

Create or update class diagrams when:

- adding/changing domain models (Assay, Activity, Target, etc.);
- changing ABC/Protocol;
- changing modular boundaries (`domain / application / infrastructure`);
- introducing non-trivial class hierarchies.

### 3.2 Must Show

- Key classes and interfaces;
- Inheritance and implementations;
- Main relationships between components;
- Layer boundaries.

### 3.3 Location

- `docs/architecture/diagrams/class/`
- `docs/pipelines/<provider>/<entity>/diagrams/class/`

---

## 4. Sequence Diagram Policy

### 4.1 When Needed

Sequence diagrams are required for:

- complex pipeline execution scenarios;
- API interactions (pagination, retries, rate-limit, errors);
- pipeline run lifecycle;
- custom logic in clients or adapters.

### 4.2 Required Elements

- Participants (CLI, PipelineFacade, Pipeline, API Client, Storage, etc.);
- Main call sequence;
- Branches: success, partial success, errors.

### 4.3 Location

- `docs/pipelines/<provider>/<entity>/diagrams/sequence/`
- `docs/architecture/diagrams/sequence/`

---

## 5. Flowchart Policy

### 5.1 When Needed

Use flowcharts for:

- branching pipeline logic;
- choosing load strategy (full/incremental);
- fallback and idempotency flows;
- error handling paths.

### 5.2 Must Show

- Main process steps;
- Decision points;
- End states: success, partial success, fatal error.

### 5.3 Location

- `docs/pipelines/<provider>/<entity>/diagrams/flow/`

---

## 6. Minimum Set for Production Pipelines

Every production pipeline must have:

1. Flowchart of the overall workflow.
2. Sequence diagram for the main scenario (extract → transform → validate → write).
3. Class diagram (if custom models or abstractions exist).

For trivial pipelines, a reduced set is allowed only with reviewer approval.

---

## 7. Process and Responsibilities

### 7.1 Author

- creates or updates diagrams;
- adds links in the README of the corresponding module;
- updates any affected diagrams to the current style palette (palette/fonts/layout) when touching a module.

### 7.2 Reviewer

- checks presence and freshness of diagrams;
- blocks PRs that violate the policy.

### 7.3 Architect

- runs periodic audits of diagrams;
- initiates removal/update of stale diagrams;
- ensures refit of existing diagrams to the current style palette (class/sequence/flow/component).

---

## 8. PR Checklist

Each PR touching architecture or pipelines must state explicitly:

- whether Class diagram updates are needed;
- whether Sequence diagram updates are needed;
- whether Flowchart updates are needed.

If “yes”, the updated diagram files must be in the diff.
For any existing diagram, verify palette and typography compliance (22/18 pt fonts, neutral colors, ≥1.5 px lines, consistent layout) before merge.

---

## 9. Example Directory Layout

```text
docs/
  architecture/
    diagrams/
      class/
      sequence/
      flow/
      00-diagramming-policy.md
  pipelines/
    chembl/
      activity/
        diagrams/
          class/
          sequence/
          flow/
```
