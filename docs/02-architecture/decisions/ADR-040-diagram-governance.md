# ADR-040: Diagram Governance and Layout Policy

**Status:** Accepted
**Date:** 2026-02-25
**Decision makers:** @BioETL-Team
**Related:** ADR-005 (Layered Architecture), ADR-020 (Composition Layer)

---

## Context

BioETL содержит два каталога диаграмм с разными форматами и назначением:

**Canonical sources** (`docs/02-architecture/mmd-diagrams/`):
- `architecture/` — 18 canonical + 11 subdomain-decomposed = 29 `.mmd` файлов
- `class-diagrams/` — 16 `.mmd` файлов (class diagram families)
- `foundation/` — 59 `.mmd` файлов (historical + TOP-25)
- Итого: **104 `.mmd` файла** (93 canonical по README)

**Decomposed views** (`docs/02-architecture/diagrams/mermaid/`):
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
- Lint: `scripts/lint_diagrams.py`
- Шаблон: `mmd-diagrams/_template.mmd`
- Политика LLM: `docs/02-architecture/06-diagram-policy.md` (POL-LLM-DIAGRAMS-001)

---

## Decision

### D1: Canonical Colour Scheme

Единственным источником палитры является **`theme/custom.css` строки 140–151**.
Все inline `style` директивы в `.mermaid` и `.mmd` файлах MUST соответствовать этой схеме.

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
mmd-diagrams/          ← canonical .mmd (rendered via render.sh)
  architecture/        ← system/component-level diagrams
  class-diagrams/      ← class structure diagrams
  foundation/          ← historical reference + TOP-25
  _template.mmd        ← шаблон для новых диаграмм
diagrams/mermaid/      ← decomposed .mermaid views (foundation)
  *-full.mermaid       ← полные reference копии
  *-overview.mermaid   ← cross-layer overview
  *-domain.mermaid     ← domain-layer focus
  *-infra.mermaid      ← infrastructure-mapping focus
  *-dataflow.mermaid   ← data flow focus
  00-legend.mermaid    ← link types + code glossary
```

Новые **architecture views** создаются как `.mmd` в `mmd-diagrams/architecture/`.
Foundation views создаются как `.mermaid` в `diagrams/mermaid/`.

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
суффиксы `a/b/c/d` по теме (например, `13a-port-contracts-data-sources.mmd`).

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

`scripts/lint_diagrams.py` проверяет оба каталога:

| Rule | Description |
|------|-------------|
| SIZE-001 | Node count > 35 → ERROR |
| SIZE-002 | Node count > 20 → WARN |
| META-001 | Отсутствие `@version`/`@date`/`@type`/`@level` в `.mmd` → WARN |
| META-002 | Отсутствие `%% View:` в `.mermaid` view-файле → WARN |
| COLOUR-001 | Использование неканонической палитры → ERROR |
| COLOUR-002 | Emoji в subgraph labels → ERROR |

Pre-commit hook: `lint-diagrams`.

### D7: Tool Selection Criteria

| Условие | Инструмент |
|---------|-----------|
| ≤20 узлов, стандартный layout | Mermaid |
| 20–40 узлов, сложный layout | PlantUML |
| >40 узлов | D2 (ELK layout engine) |

---

## Implementation

Выполнено в рамках принятия ADR-040 (2026-02-25):

| Действие | Scope | Результат |
|----------|-------|-----------|
| Гармонизация цветовой схемы | 106 `.mermaid` файлов | 300 замен, старая Tailwind-палитра удалена |
| Удаление emoji из subgraph labels | 106 файлов | 286 emoji убрано |
| linkStyle дифференциация | 16 flowchart файлов | 5 типов связей |
| Создание `_template.mmd` | `mmd-diagrams/` | Единый шаблон для новых диаграмм |
| `@nodes` в architecture/ | 29 файлов | Уже присутствовали |

---

## Consequences

### Positive

- Единая палитра — нет визуальных конфликтов между `mmd-diagrams/` и `diagrams/mermaid/`
- linkStyle дифференциация даёт семантическое разделение (data / DI / orchestration)
- CI предотвращает деградацию при добавлении новых диаграмм
- `_template.mmd` стандартизирует создание новых диаграмм
- Два каталога позволяют независимое развитие canonical sources и decomposed views

### Negative

- Два каталога + два расширения — когнитивная нагрузка при навигации
- Синхронизация `foundation/*.mmd` ↔ `diagrams/mermaid/*-full.mermaid` ручная
- linkStyle индексы хрупкие: любое добавление/удаление связи требует пересчёта

### Risks

- **linkStyle fragility**: изменение порядка связей ломает индексацию. Митигация: комментарий `%% linkStyle: ...` как проверочная документация
- **Эвристика `@nodes`**: подсчёт узлов ±20% от реального (subgraph границы). Митигация: lint проверяет только >35 threshold
- **Расхождение `-full.mermaid` с источником**: `foundation/*.mmd` и `diagrams/mermaid/*-full.mermaid` могут разойтись. Митигация: CI drift check (планируется)

---

## Related ADRs

- **ADR-005** — Layered Architecture (Hexagonal / Ports & Adapters)
- **ADR-020** — Composition Layer isolation
- **POL-LLM-DIAGRAMS-001** — `docs/02-architecture/06-diagram-policy.md`
