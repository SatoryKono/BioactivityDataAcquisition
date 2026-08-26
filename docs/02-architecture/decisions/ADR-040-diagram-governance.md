______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-08'

______________________________________________________________________

# ADR-040: Diagram Governance and Layout Policy

## **Date:** 2026-02-25 **Status:** Accepted **Decision makers:** @BioETL-Team **Related:** ADR-005 (Layered Architecture), ADR-020 (Composition Layer)

## Context

BioETL содержит два согласованных diagram subtrees с разными форматами и
назначением. Текущий measured baseline ниже отражает состояние репозитория на
`2026-07-18`:

**Canonical sources** (`docs/02-architecture/diagrams/`):

- `architecture/` — 89 `.mmd` файла
- `class-diagrams/` — 145 `.mmd` файла (curated `01`–`16` including `01a`/`08a`/`14a`, 1 sandbox, generated `90-pkg-*`)
- `foundation/` — 55 `.mmd` файлов
- `_template.mmd` — 1 reusable template
- Итого: **290 `.mmd` артефактов**

**Decomposed views** (`docs/02-architecture/diagrams/views/`):

- 31 foundation families × 5 views
- 3 architecture-derived families × 2 views (`03-medallion-data-flow`, `13-port-protocol-contracts`, `16-transformer-hierarchy`)
- 3 singleton architecture-derived views (`21-idempotent-processing-guards`, `23-reproducible-run-contract`, `24-control-plane-artifact-publication-pipeline`)
- `00-legend.mermaid`
- Итого: **165 `.mermaid` файлов**

### Проблемы до ADR-040

До принятия данного ADR в проекте сосуществовали **две несовместимые цветовые схемы**:

| Слой           | Старая (Tailwind-based) | Новая (canonical)   |
| -------------- | ----------------------- | ------------------- |
| Domain         | `#FFF7ED / #F59E0B`     | `#f5f3ff / #7c3aed` |
| Application    | `#ECFDF5 / #10B981`     | `#f0fdf4 / #16a34a` |
| Infrastructure | `#EFF6FF / #2563EB`     | `#fff1f2 / #dc2626` |
| Composition    | `#F5F3FF / #7C3AED`     | `#fff7ed / #f59e0b` |
| Interfaces     | `#F1F5F9 / #64748B`     | `#eff6ff / #2563eb` |

Дополнительно: 286 emoji-префиксов в subgraph labels (`🟡 Domain Layer`) мешали CLI-рендерингу.
Исторически large parts of the view corpus использовали uniform `linkStyle`
без семантического разделения типов связей, а inventory/nav/policy описывали
разные baselines.

### Существующая инфраструктура

- Тема: `theme/mermaid-config.json` + `theme/custom.css` (строки 140–151)
- Рендер: `render.sh` (SVG + PNG, 300 DPI)
- Lint: `scripts/diagrams/lint/lint_diagrams.py`
- Шаблон: `diagrams/_template.mmd`
- Политика LLM: `docs/02-architecture/diagrams/governance/policy.md` (POL-LLM-DIAGRAMS-001)

______________________________________________________________________

## Decision

### D1: Canonical Colour Scheme

Единственным источником палитры является **`theme/custom.css` строки 140–151**.
Все inline `style` директивы в `.mermaid` и `.mmd` файлах MUST соответствовать этой схеме.

| Слой           | Fill      | Stroke    |
| -------------- | --------- | --------- |
| Domain         | `#f5f3ff` | `#7c3aed` |
| Application    | `#f0fdf4` | `#16a34a` |
| Infrastructure | `#fff1f2` | `#dc2626` |
| Composition    | `#fff7ed` | `#f59e0b` |
| Interfaces     | `#eff6ff` | `#2563eb` |
| External       | `#f1f5f9` | `#64748b` |
| Bronze         | `#fff7ed` | `#f59e0b` |
| Silver         | `#f8fafc` | `#475569` |
| Gold           | `#fefce8` | `#ca8a04` |
| Quarantine     | `#ffe4e6` | `#e11d48` |

Использование произвольных цветов MUST NOT. Emoji-префиксы в subgraph labels MUST NOT.

### D2: Dual Repository Structure

```
diagrams/          ← canonical .mmd (rendered via render.sh)
  architecture/        ← system/component-level diagrams
  class-diagrams/      ← class structure diagrams
  foundation/          ← historical reference + TOP-25
  views/               ← decomposed .mermaid views (foundation)
    *-full.mermaid       ← полные reference копии
    *-overview.mermaid   ← cross-layer overview
    *-domain.mermaid     ← domain-layer focus
    *-infra.mermaid      ← infrastructure-mapping focus
    *-dataflow.mermaid   ← data flow focus
    00-legend.mermaid    ← link types + code glossary
  _template.mmd        ← шаблон для новых диаграмм
```

Новые **architecture views** создаются как `.mmd` в `diagrams/architecture/`.
Foundation views создаются как `.mermaid` в `diagrams/views/`.

### D3: View-based Decomposition Rules

| Threshold   | Action                                 |
| ----------- | -------------------------------------- |
| ≤15 узлов   | Рекомендуемый предел, без декомпозиции |
| 16–20 узлов | Soft limit — рассмотреть декомпозицию  |
| 21–35 узлов | WARN — декомпозиция рекомендуется      |
| >35 узлов   | CRITICAL — декомпозиция обязательна    |

Стандартные view-типы для **foundation/**:

- `-full` — полный reference (сохраняется обязательно)
- `-overview` — cross-layer (≤15 узлов)
- `-domain` — domain-layer focus (≤15 узлов)
- `-infra` — infrastructure-mapping (≤15 узлов)
- `-dataflow` — data movement (≤15 узлов)

Для **architecture/** — декомпозиция по subdomain (предметная группировка),
суффиксы `a/b/c/d` по теме (например, `13g-port-contracts-data-sources.mmd`
для port-contracts family; `13a-data-storage-ports.mmd` остаётся в
data-storage/operational family).

Оригиналы сохраняются как `-full` reference и не удаляются.

### D4: Metadata Formats

**`.mmd` файлы** (canonical):

```
%% BioETL — <Title>
%% <Covers>

%% @version 1.0.0
%% @date    YYYY-MM-DD
%% @type    flowchart|classDiagram|sequenceDiagram|stateDiagram|erDiagram|mindmap
%% @level   System / Component | Class / Interface | Sequence | State
%% @nodes   <count>
%% @adr     <ADR-NNN>  (если применимо)
```

**`.mermaid` view-файлы** (decomposed):

```
%% View: <Overview|Domain-Focus|Infrastructure-Mapping|Data-Flow|Full> | Parent: <family-full.mermaid|architecture-topic.mmd>
%% Parent source: docs/02-architecture/diagrams/<foundation|architecture>/<file.mmd>   # required for `*-full.mermaid`
flowchart TB
```

### D5: linkStyle Differentiation

View-файлы с ≥3 типами связей и >5 соединениями SHOULD использовать дифференцированный `linkStyle`.
Классификация выполняется по принадлежности узлов к subgraph-слою (Domain → DI, Infrastructure → data и т.д.).

| Тип связи          | Стиль                                                  |
| ------------------ | ------------------------------------------------------ |
| data flow          | `stroke:#1E293B,stroke-width:2px`                      |
| orchestration      | `stroke:#16a34a,stroke-width:2px`                      |
| DI / implements    | `stroke:#7c3aed,stroke-width:1.5px,stroke-dasharray:5` |
| observability      | `stroke:#94A3B8,stroke-width:1px`                      |
| error / quarantine | `stroke:#dc2626,stroke-width:2px,stroke-dasharray:4`   |
| generic            | `stroke:#475569,stroke-width:2px,stroke-dasharray:5`   |

Каждый differentiated блок MUST сопровождаться комментарием:

```
%% linkStyle: data 0-3 | orchestration 4-8 | di 9-11
```

### D6: CI Validation

`scripts/diagrams/lint/lint_diagrams.py` проверяет оба каталога:

| Rule       | Description                                                                          |
| ---------- | ------------------------------------------------------------------------------------ |
| SIZE-001   | Node count > 35 → ERROR                                                              |
| SIZE-002   | Node count > 20 → WARN                                                               |
| META-001   | Отсутствие structured metadata (`@...` для `.mmd`, `%% View:` для `.mermaid`) → WARN |
| META-002   | Некорректный формат даты в `%% Updated:`/`%% @date` → ERROR                          |
| COLOUR-001 | Использование deprecated pre-ADR-040 палитры в `style`/`classDef` → ERROR            |
| COLOUR-002 | Emoji в subgraph labels → ERROR                                                      |
| GRAPH-001  | Orphan nodes (defined but not in any edge) в `flowchart`/`sequenceDiagram` → WARN    |
| NBSP-001   | Использование `&nbsp;`-padding в исходнике → ERROR                                   |

Примечание по реализации `SIZE-*`:

- `*-full.mermaid` reference views исключены из `SIZE-001`/`SIZE-002`.
- `00-legend*` исключены из `SIZE-001`/`SIZE-002`.

Примечание по size-normalization (`scripts/diagrams/fix/uniform_diagram_sizes.py`):

- `@uniform-group` задаёт групповую нормализацию высоты.
- `@uniform-width global` (по умолчанию) использует общую ширину для всех групп.
- `@uniform-width group` разрешает width per group для снижения `&nbsp;`-padding в перегруженных class-diagram family.

Pre-commit hooks: `lint-diagrams`, `prune-orphan-diagram-nodes`.

#### GRAPH-001 — Orphan Node Rule

Реализован в `scripts/diagrams/fix/prune_orphan_nodes.py`. Нода считается orphan, если:

- Определена (`NodeId["label"]` или bare `NodeId`) в diagram
- Не участвует ни в одном edge / message в том же файле

**Исключения (нода не флагируется):**

- Аннотация `%% keep-orphan: NodeId` (inline в файле)
- Нода внутри subgraph, чьё имя встречается в edge (lenient subgraph rule)
- Файлы `00-legend*`
- `classDiagram`, `stateDiagram`, `erDiagram`, `mindmap`

**Инструмент:**

```bash
python scripts/diagrams/fix/prune_orphan_nodes.py --check      # аудит
python scripts/diagrams/fix/prune_orphan_nodes.py --fix         # удалить garbage orphans
python scripts/diagrams/fix/prune_orphan_nodes.py --grandfather # exemption для всех текущих
```

### D7: Tool Selection Criteria

| Условие     | Инструмент                                         | Layout    |
| ----------- | -------------------------------------------------- | --------- |
| ≤20 узлов   | Mermaid (Dagre)                                    | TB или LR |
| 21–40 узлов | Mermaid + ELK init                                 | TB или LR |
| >40 узлов   | Mermaid + ELK init (preferred) или D2 (ELK engine) | TB или LR |

### D8: Adaptive Layout Rules

ELK (Eclipse Layout Kernel) SHOULD использоваться для `flowchart`/`graph` диаграмм с `@nodes > 20`.

**Синтаксис (вставлять перед объявлением `graph`/`flowchart`):**

```
%%{init: {'layout': 'elk', 'theme': 'base', 'themeVariables': {'fontFamily': 'Inter, Roboto, sans-serif'}, 'elk': {'mergeEdges': true, 'nodePlacementStrategy': 'BRANDES_KOEPF', 'cycleBreakingStrategy': 'GREEDY', 'direction': 'RIGHT', 'spacing.nodeNode': 40, 'spacing.edgeNode': 30, 'spacing.edgeEdge': 20, 'edgeRouting': 'ORTHOGONAL'}}}%%
```

**Direction selection:**

| Паттерн                             | Direction | Примеры                                                |
| ----------------------------------- | --------- | ------------------------------------------------------ |
| Иерархия / DI граф / port map       | `TB`      | `01-high-level-hexagonal`, `12-bootstrap-di-container` |
| Pipeline / data flow / config chain | `LR`      | `03-medallion-data-flow`, `11-configuration-system`    |

**CI Rules (lint_diagrams.py):**

| Rule       | Условие                                        | Severity |
| ---------- | ---------------------------------------------- | -------- |
| LAYOUT-001 | `flowchart/graph` с `@nodes > 20` без ELK init | WARNING  |
| LAYOUT-002 | `flowchart/graph` с `@nodes > 40` без ELK init | ERROR    |

**Инструмент:** `python -m scripts.diagrams apply-elk --dry-run` для аудита, без `--dry-run` для применения.

______________________________________________________________________

## Implementation

Первичный rollout, выполненный в рамках принятия ADR-040 (2026-02-25):

| Действие                          | Scope                 | Результат                                  |
| --------------------------------- | --------------------- | ------------------------------------------ |
| Гармонизация цветовой схемы       | 106 `.mermaid` файлов | 300 замен, старая Tailwind-палитра удалена |
| Удаление emoji из subgraph labels | 106 файлов            | 286 emoji убрано                           |
| linkStyle дифференциация          | 16 flowchart файлов   | 5 типов связей                             |
| Создание `_template.mmd`          | `diagrams/`           | Единый шаблон для новых диаграмм           |
| `@nodes` в architecture/          | 29 файлов             | Уже присутствовали                         |

Текущий corpus с тех пор вырос; актуальные measured counts поддерживаются через
`docs/02-architecture/diagrams/governance/diagrams-index.md` и
`docs/02-architecture/diagrams/governance/diagram-views-inventory.md`.

______________________________________________________________________

## Consequences

### Positive

- Единая палитра — нет визуальных конфликтов между canonical и decomposed наборами
- linkStyle дифференциация даёт семантическое разделение (data / DI / orchestration)
- CI предотвращает деградацию при добавлении новых диаграмм
- `_template.mmd` стандартизирует создание новых диаграмм
- Два каталога позволяют независимое развитие canonical sources и decomposed views

### Negative

- Два каталога + два расширения — когнитивная нагрузка при навигации
- Синхронизация `foundation/*.mmd` ↔ `diagrams/views/*-full.mermaid` ручная
- linkStyle индексы хрупкие: любое добавление/удаление связи требует пересчёта

### Risks

- **linkStyle fragility**: изменение порядка связей ломает индексацию. Митигация: комментарий `%% linkStyle: ...` как проверочная документация
- **Эвристика `@nodes`**: подсчёт узлов ±20% от реального (subgraph границы). Митигация: lint проверяет только >35 threshold
- **Расхождение `-full.mermaid` с источником**: `foundation/*.mmd` и `diagrams/views/*-full.mermaid` могут разойтись. Митигация: blocking CI source-render drift gate и corpus regression guards.

______________________________________________________________________

## References

- **ADR-005** — Layered Architecture (Hexagonal / Ports & Adapters)
- **ADR-020** — Composition Layer isolation
- **POL-LLM-DIAGRAMS-001** — `docs/02-architecture/diagrams/governance/policy.md`
- **Render retention (DOC-GOV-02)** — `docs/02-architecture/diagrams/governance/render-retention.md`

## Compliance

| Control      | Requirement                                                                | Status | Evidence                             |
| ------------ | -------------------------------------------------------------------------- | ------ | ------------------------------------ |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass` | `ADR-040-diagram-governance.md`      |
| Status       | ADR status MUST be explicit and consistent                                 | `pass` | `Accepted`                           |
| Supersession | Superseded or superseding ADRs SHOULD be linked explicitly when applicable | `n/a`  | `metadata block`                     |
| Verification | Implementation and validation expectations MUST be documented              | `pass` | `Verification / Acceptance Criteria` |
| References   | Related ADRs, docs, or artifacts SHOULD be linked                          | `pass` | `References`                         |

## Rollout

- Rollout steps MUST be sequenced before broad adoption.
- Documentation, configuration, and test surfaces SHOULD be updated in the same change set when the decision is implemented.
- Breaking or migration-sensitive adoption SHOULD include an explicit transition window.

## Rollback

- Rollback MUST identify the last known-good behavior or artifact set.
- If the decision changes contracts, configuration, or storage semantics, rollback SHOULD include data and compatibility checks.
- Rollback triggers SHOULD be observable through tests, runtime signals, or regression symptoms.

## Verification

- Verify architecture, configuration, and documentation changes against the current codebase.
- Run the relevant tests, validators, or parity checks before considering the ADR fully adopted.
- Confirm downstream docs and contracts reflect the same decision boundaries.

## Acceptance Criteria

- [x] The decision is documented with current status, date, and owner metadata.
- [x] The implementation path or adoption boundary is testable and linked from the ADR.
- [x] Supersession or migration impact is documented when the decision changes an earlier posture.
- [x] Related docs, contracts, and operational guidance are aligned with this ADR.
