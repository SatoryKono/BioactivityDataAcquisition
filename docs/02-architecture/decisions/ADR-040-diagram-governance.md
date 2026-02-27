# ADR-040: Diagram Governance and Layout Policy

**Status:** Accepted
**Date:** 2026-02-25
**Decision makers:** @BioETL-Team
**Related:** ADR-005 (Layered Architecture), ADR-020 (Composition Layer)

---

## Context

BioETL содержит два каталога диаграмм с разными форматами и назначением:

**Canonical sources** (`docs/02-architecture/mmd-diagrams/`):
- `architecture/` — 18 canonical + 11 subdomain-decomposed = 29 `.mermaid` файлов
- `class-diagrams/` — 16 `.mermaid` файлов (class diagram families)
- `foundation/` — 59 `.mermaid` файлов (historical + TOP-25)
- Итого: **104 `.mermaid` файла** (93 canonical по README)

**Decomposed views** (`docs/02-architecture/mmd-diagrams/views/`):
- 31 parent diagram × 5 views (`-full`, `-overview`, `-domain`, `-infra`, `-dataflow`)
- + `00-legend.mermaid`
- Итого: **156 `.mermaid` файлов**

### Проблемы до ADR-040

До принятия данного ADR в проекте сосуществовали **две несовместимые цветовые схемы**:

| Слой | Старая (Tailwind-based) | Новая (canonical) |
|------|------------------------|-------------------|
| Domain | `#FFF7ED / #F59E0B` | `#f3e5f5 / #6a1b9a` |
| Application | `#ECFDF5 / #10B981` | `#e8f5e9 / #2e7d32` |
| Infrastructure | `#EFF6FF / #2563EB` | `#ffcdd2 / #c62828` |
| Composition | `#F5F3FF / #7C3AED` | `#fff3e0 / #e65100` |
| Interfaces | `#F1F5F9 / #64748B` | `#e3f2fd / #1565c0` |

Дополнительно: 286 emoji-префиксов в subgraph labels (`🟡 Domain Layer`) мешали CLI-рендерингу.
Все 156 `.mermaid` view-файлов использовали uniform `linkStyle` без семантического разделения типов связей.

### Существующая инфраструктура

- Тема: `theme/mermaid-config.json` + `theme/custom.css` (строки 140–151)
- Рендер: `render.sh` (SVG + PNG, 300 DPI)
- Lint: `scripts/lint-diagrams.py`
- Шаблон: `mmd-diagrams/-template.mermaid`
- Политика LLM: `docs/02-architecture/06-diagram-policy.md` (POL-LLM-DIAGRAMS-001)

---

## Decision

### D1: Canonical Colour Scheme

Единственным источником палитры является **`theme/custom.css` строки 140–151**.
Все inline `style` директивы в `.mermaid` и `.mermaid` файлах MUST соответствовать этой схеме.

| Слой | Fill | Stroke |
|------|------|--------|
| Domain | `#f3e5f5` | `#6a1b9a` |
| Application | `#e8f5e9` | `#2e7d32` |
| Infrastructure | `#ffcdd2` | `#c62828` |
| Composition | `#fff3e0` | `#e65100` |
| Interfaces | `#e3f2fd` | `#1565c0` |
| External | `#eceff1` | `#455a64` |
| Bronze | `#fff3e0` | `#e65100` |
| Silver | `#eceff1` | `#607d8b` |
| Gold | `#fff8e1` | `#f9a825` |
| Quarantine | `#ffebee` | `#d32f2f` |

Использование произвольных цветов MUST NOT. Emoji-префиксы в subgraph labels MUST NOT.

### D2: Dual Repository Structure

```
mmd-diagrams/              ← единый корень всех диаграмм
  architecture/            ← system/component-level diagrams (.mmd)
  class-diagrams/          ← class structure diagrams (.mmd)
  foundation/              ← historical reference + TOP-25 (.mmd)
  views/                   ← decomposed .mermaid views
    *-full.mermaid         ← полные reference копии
    *-overview.mermaid     ← cross-layer overview
    *-domain.mermaid       ← domain-layer focus
    *-infra.mermaid        ← infrastructure-mapping focus
    *-dataflow.mermaid     ← data flow focus
    00-legend.mermaid      ← link types + code glossary
  docs/                    ← diagram documentation
  _template.mmd            ← шаблон для новых диаграмм
```

Новые **architecture views** создаются как `.mmd` в `mmd-diagrams/architecture/`.
Foundation views создаются как `.mermaid` в `mmd-diagrams/views/`.

### D3: View-based Decomposition Rules

| Threshold | Action |
|-----------|--------|
| ≤15 узлов | Рекомендуемый предел, без декомпозиции |
| 16–20 узлов | Soft limit — рассмотреть декомпозицию |
| 21–35 узлов | WARN — декомпозиция рекомендуется |
| >35 узлов | CRITICAL — декомпозиция обязательна |

Стандартные view-типы для **foundation/**:
- `-full` — полный reference (сохраняется обязательно)
- `-overview` — cross-layer (≤15 узлов)
- `-domain` — domain-layer focus (≤15 узлов)
- `-infra` — infrastructure-mapping (≤15 узлов)
- `-dataflow` — data movement (≤15 узлов)

Для **architecture/** — декомпозиция по subdomain (предметная группировка),
суффиксы `a/b/c/d` по теме (например, `13a-port-contracts-data-sources.mermaid`).

Оригиналы сохраняются как `-full` reference и не удаляются.

### D4: Metadata Formats

**`.mermaid` файлы** (canonical):
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
%% View: <Overview|Domain|Infrastructure|Dataflow|Full> | Parent: <file.mermaid>
flowchart TB
```

### D5: linkStyle Differentiation

View-файлы с ≥3 типами связей и >5 соединениями SHOULD использовать дифференцированный `linkStyle`.
Классификация выполняется по принадлежности узлов к subgraph-слою (Domain → DI, Infrastructure → data и т.д.).

| Тип связи | Стиль |
|-----------|-------|
| data flow | `stroke:#1E293B,stroke-width:2px` |
| orchestration | `stroke:#2e7d32,stroke-width:2px` |
| DI / implements | `stroke:#6a1b9a,stroke-width:1.5px,stroke-dasharray:5` |
| observability | `stroke:#94A3B8,stroke-width:1px` |
| error / quarantine | `stroke:#c62828,stroke-width:2px,stroke-dasharray:4` |
| generic | `stroke:#475569,stroke-width:2px,stroke-dasharray:5` |

Каждый differentiated блок MUST сопровождаться комментарием:
```
%% linkStyle: data 0-3 | orchestration 4-8 | di 9-11
```

### D6: CI Validation

`scripts/lint-diagrams.py` проверяет оба каталога:

| Rule | Description |
|------|-------------|
| SIZE-001 | Node count > 35 → ERROR |
| SIZE-002 | Node count > 20 → WARN |
| META-001 | Отсутствие `@version`/`@date`/`@type`/`@level` в `.mermaid` → WARN |
| META-002 | Отсутствие `%% View:` в `.mermaid` view-файле → WARN |
| COLOUR-001 | Использование deprecated pre-ADR-040 палитры в `style`/`classDef` → ERROR |
| COLOUR-002 | Emoji в subgraph labels → ERROR |
| GRAPH-001 | Orphan nodes (defined but not in any edge) в `flowchart`/`sequenceDiagram` → WARN |

Примечание по реализации `SIZE-*`:
- `*-full.mermaid` reference views исключены из `SIZE-001`/`SIZE-002`.
- `00-legend*` исключены из `SIZE-001`/`SIZE-002`.

Примечание по size-normalization (`scripts/uniform-diagram-sizes.py`):
- `@uniform-group` задаёт групповую нормализацию высоты.
- `@uniform-width global` (по умолчанию) использует общую ширину для всех групп.
- `@uniform-width group` разрешает width per group для снижения `&nbsp;`-padding в перегруженных class-diagram family.

Pre-commit hooks: `lint-diagrams`, `prune-orphan-diagram-nodes`.

#### GRAPH-001 — Orphan Node Rule

Реализован в `scripts/prune-orphan-nodes.py`. Нода считается orphan, если:
- Определена (`NodeId["label"]` или bare `NodeId`) в diagram
- Не участвует ни в одном edge / message в том же файле

**Исключения (нода не флагируется):**
- Аннотация `%% keep-orphan: NodeId` (inline в файле)
- Нода внутри subgraph, чьё имя встречается в edge (lenient subgraph rule)
- Файлы `00-legend*`
- `classDiagram`, `stateDiagram`, `erDiagram`, `mindmap`

**Инструмент:**
```bash
python scripts/prune-orphan-nodes.py --check      # аудит
python scripts/prune-orphan-nodes.py --fix         # удалить garbage orphans
python scripts/prune-orphan-nodes.py --grandfather # exemption для всех текущих
```

### D7: Tool Selection Criteria

| Условие | Инструмент | Layout |
|---------|------------|--------|
| ≤20 узлов | Mermaid (Dagre) | TB или LR |
| 21–40 узлов | Mermaid + ELK init | TB или LR |
| >40 узлов | Mermaid + ELK init (preferred) или D2 (ELK engine) | TB или LR |

### D8: Adaptive Layout Rules

ELK (Eclipse Layout Kernel) SHOULD использоваться для `flowchart`/`graph` диаграмм с `@nodes > 20`.

**Синтаксис (вставлять перед объявлением `graph`/`flowchart`):**

```
%%{init: {'layout': 'elk', 'elk': {'mergeEdges': false, 'nodePlacementStrategy': 'SIMPLE', 'edgeRouting': 'ORTHOGONAL'}}}%%
```

**Direction selection:**

| Паттерн | Direction | Примеры |
|---------|-----------|---------|
| Иерархия / DI граф / port map | `TB` | `01-high-level-hexagonal`, `12-bootstrap-di-container` |
| Pipeline / data flow / config chain | `LR` | `03-medallion-data-flow`, `11-configuration-system` |

**CI Rules (lint-diagrams.py):**

| Rule | Условие | Severity |
|------|---------|----------|
| LAYOUT-001 | `flowchart/graph` с `@nodes > 20` без ELK init | WARNING |
| LAYOUT-002 | `flowchart/graph` с `@nodes > 40` без ELK init | ERROR |

**Инструмент:** `src/tools/apply-elk-layout.py --dry-run` для аудита, без `--dry-run` для применения.

### D9: Cross-Diagram Link Harmonization

Все диаграммы проекта SHOULD использовать единую семантическую палитру для связей.

**Каноническая палитра (5 семантических типов + baseline):**

| Семантика | Цвет | Толщина | Пунктир | Flowchart | Sequence | Class | State | ER |
|-----------|-------|---------|---------|-----------|----------|-------|-------|----|
| Data flow | `#1E293B` | 2px | — | `linkStyle` | `->>` sync | `-->` | — | `\|\|--o{` solid |
| Orchestration | `#2e7d32` | 2px | — | `linkStyle` | `->> [ORCH]` | `-->` delegates | `-->` transition | — |
| DI/implements | `#6a1b9a` | 1.5px | `5` | `linkStyle` | — | `<\|--` / `..>` | — | `\|o..o\|` dashed |
| Observability | `#94A3B8` | 1px | — | `linkStyle` | `-->>` return | `..>` observes | — | — |
| Error/quarant | `#c62828` | 2px | `4 3` | `linkStyle` | `-->> [ERR]` | — | `-->` error | — |
| Baseline | `#475569` | 2px | — | default | default | default | — | — |

**Реализация по уровням:**

| Уровень | Механизм | Обязательность | Scope |
|---------|----------|----------------|-------|
| **L1** — `%%{init}` | `themeVariables.lineColor` per type | MUST для новых диаграмм | Все `.mermaid` |
| **L2** — CSS | `theme/custom.css` D9 секция | Автоматически при SVG render | Все SVG |
| **L3** — Метки | `[DATA]`, `[DI]`, `[ORCH]`, `[OBS]`, `[ERR]` prefix | SHOULD для >10 рёбер | Исходники |
| **L4** — SVG post-proc | `harmonize-link-styles.py` | MAY для публикуемых | Rendered SVG |

**Per-type %%{init} presets:**

```
%% sequenceDiagram:
%%{init: {'theme': 'base', 'themeVariables': {'signalColor': '#475569', 'actorLineColor': '#475569'}}}%%

%% classDiagram:
%%{init: {'theme': 'base', 'themeVariables': {'lineColor': '#475569'}}}%%

%% stateDiagram:
%%{init: {'theme': 'base', 'themeVariables': {'lineColor': '#2e7d32'}}}%%

%% erDiagram:
%%{init: {'theme': 'base', 'themeVariables': {'lineColor': '#1E293B'}}}%%
```

**Инструмент:** `src/tools/harmonize-link-styles.py --dry-run` для аудита rendered SVG.

---

## Implementation

Выполнено в рамках принятия ADR-040 (2026-02-25):

| Действие | Scope | Результат |
|----------|-------|-----------|
| Гармонизация цветовой схемы | 106 `.mermaid` файлов | 300 замен, старая Tailwind-палитра удалена |
| Удаление emoji из subgraph labels | 106 файлов | 286 emoji убрано |
| linkStyle дифференциация | 16 flowchart файлов | 5 типов связей |
| Создание `-template.mermaid` | `mmd-diagrams/` | Единый шаблон для новых диаграмм |
| `@nodes` в architecture/ | 29 файлов | Уже присутствовали |
| D9 Link Harmonization | CSS + tool + template | `lineColor` #475569, CSS D9 секция, `harmonize-link-styles.py` |
| ELK `edgeRouting: ORTHOGONAL` | 14 `.mermaid` + config | Ортогональные рёбра во всех ELK-диаграммах |

---

## Consequences

### Positive

- Единая палитра — нет визуальных конфликтов
- linkStyle дифференциация даёт семантическое разделение (data / DI / orchestration)
- CI предотвращает деградацию при добавлении новых диаграмм
- `_template.mmd` стандартизирует создание новых диаграмм
- Единый корень `mmd-diagrams/` с `views/` для decomposed views

### Negative

- Два расширения (`.mmd` + `.mermaid`) — когнитивная нагрузка
- Синхронизация `foundation/*.mmd` ↔ `views/*-full.mermaid` ручная
- linkStyle индексы хрупкие: любое добавление/удаление связи требует пересчёта

### Risks

- **linkStyle fragility**: изменение порядка связей ломает индексацию. Митигация: комментарий `%% linkStyle: ...` как проверочная документация
- **Эвристика `@nodes`**: подсчёт узлов ±20% от реального (subgraph границы). Митигация: lint проверяет только >35 threshold
- **Расхождение `-full.mermaid` с источником**: `foundation/*.mmd` и `views/*-full.mermaid` могут разойтись. Митигация: CI drift check (планируется)

---

## Related ADRs

- **ADR-005** — Layered Architecture (Hexagonal / Ports & Adapters)
- **ADR-020** — Composition Layer isolation
- **POL-LLM-DIAGRAMS-001** — `docs/02-architecture/06-diagram-policy.md`
