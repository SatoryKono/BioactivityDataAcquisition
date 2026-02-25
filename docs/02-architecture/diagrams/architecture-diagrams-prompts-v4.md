# BioETL: Промты для оптимизации архитектурных диаграмм v4.0

**Версия:** 4.0 | **Дата:** 2026-02-25
**Контекст:** Обновлено по актуальной ветке main (merge fecde7d)
**Отличия от v3.0:** Промты 1, 3, 5, 7 выполнены в main. Lint частично выполнен (без SIZE/COLOUR). linkStyle дифференциация покрыла 124/156 файлов, но 9 view-файлов + 16 full-файлов остались с uniform стилем. Фокус v4.0 — доделки и новые задачи.

---

## Текущее состояние (после merge main 2026-02-25)

### Файловая структура

```
docs/02-architecture/
├── mmd-diagrams/                          ← КАНОНИЧЕСКОЕ расположение (105 .mmd)
│   ├── architecture/  (29 .mmd)           ← 18 original + 11 decomposed ✅
│   ├── class-diagrams/ (16 .mmd)          ← НЕ декомпозированы
│   ├── foundation/    (59 .mmd)           ← Исходники (с %%{init:})
│   ├── _template.mmd                      ← ✅ Создан
│   ├── theme/
│   │   ├── mermaid-config.json            ← 131 строка
│   │   └── custom.css                     ← 189 строк
│   ├── render.sh                          ← SVG+PNG pipeline
│   └── README.md                          ← ✅ Обновлён (секция Decomposed)
│
├── diagrams/                              ← DECOMPOSED VIEWS
│   ├── mermaid/                            ← 156 .mermaid файлов
│   │   ├── 00-legend.mermaid              ← ✅ С Link Types subgraph
│   │   ├── *-overview.mermaid (31 шт.)    ← ≤15 узлов
│   │   ├── *-domain.mermaid  (31 шт.)     ← Домен-фокус
│   │   ├── *-infra.mermaid   (31 шт.)     ← Инфра-маппинг
│   │   ├── *-dataflow.mermaid (31 шт.)    ← Поток данных
│   │   └── *-full.mermaid    (31 шт.)     ← Полные reference
│   ├── README.md                          ← ✅ Ссылка на ADR-040
│   └── diagram-views-inventory.md
│
├── decisions/
│   └── ADR-040-diagram-governance.md      ← ✅ Создан (D1-D7)
│
└── 06-diagram-policy.md                   ← ✅ Ссылка на ADR-040

scripts/lint_diagrams.py                   ← ✅ Dual-dir, META/NAME/STALE
.pre-commit-config.yaml                    ← ✅ lint-diagrams hook
src/tools/
├── build_diagram_docs.py                  ← ✅ НОВЫЙ: Word doc builder (597 LOC)
└── differentiate_linkstyle.py             ← ✅ НОВЫЙ: linkStyle tool (367 LOC)
```

### Статус выполнения v3.0 → v4.0

| Промт v3.0 | Статус | Детали |
|-------------|--------|--------|
| П.1: Гармонизация цветов | **ВЫПОЛНЕН** | 0 файлов со старой палитрой, 0 emoji |
| П.2: linkStyle дифференциация | **ЧАСТИЧНО** | 124/156 файлов — differentiated; 9 view + 16 full — uniform |
| П.3: Декомпозиция architecture/ | **ВЫПОЛНЕН** | 11 sub-файлов (01a/b/c, 05a/b, 12a/b, 13a/b/c/d) |
| П.4: lint_diagrams.py + pre-commit | **ЧАСТИЧНО** | META/NAME/STALE/CONTENT — есть; **SIZE и COLOUR — НЕТ** |
| П.5: _template.mmd + @nodes | **ВЫПОЛНЕН** | 29/29 architecture файлов с @nodes |
| П.6: Layout-хаки | **НЕ ВЫПОЛНЕН** | Отложен до визуальной проверки |
| П.7: ADR-040 | **ВЫПОЛНЕН** | D1-D7, Implementation section |

### Расхождения ADR-040 D6 vs реальность

ADR-040 D6 декларирует проверки SIZE-001/002 и COLOUR-001/002, но `lint_diagrams.py`
(main) НЕ содержит этих функций. Только META-001, NAME-001, CONTENT-001/002, STALE-001/002.

### Оставшиеся uniform linkStyle файлы (9 views)

```
01-high-level-domain.mermaid
01-high-level-overview.mermaid
04-domain-layer-class-diagram-overview.mermaid
05-layers-interaction-domain.mermaid
12-local-deployment-architecture-domain.mermaid
14-provider-health-states-overview.mermaid
33-cli-run-interaction-domain.mermaid
36-architecture-principles-mindmap-overview.mermaid
50-exception-hierarchy-domain.mermaid
```

Причина: main's `differentiate_linkstyle.py` пропустил их (вероятно, <3 типов связей
или non-flowchart diagram type). `*-full.mermaid` (16 файлов) — исключены by design.

---

## Промт 1: Добавить SIZE и COLOUR проверки в lint_diagrams.py (GAP)

**Приоритет:** HIGH — ADR-040 D6 декларирует эти проверки, но они отсутствуют
**Scope:** `scripts/lint_diagrams.py`

```
Режим: CODE

## Контекст
ADR-040 D6 определяет 6 правил lint: SIZE-001, SIZE-002, META-001, META-002,
COLOUR-001, COLOUR-002. Текущий lint_diagrams.py реализует только META/NAME/CONTENT/STALE.
Необходимо добавить SIZE и COLOUR.

## Задача

### 1. Добавить APPROVED_FILLS константу

```python
# Approved fill colours from custom.css (ADR-040 D1)
APPROVED_FILLS = {
    "#f3e5f5", "#e8f5e9", "#ffcdd2", "#fff3e0",
    "#e3f2fd", "#eceff1", "#fff8e1", "#ffebee",
    "#f8fafc",  # Legend/neutral background
}
```

### 2. Добавить check_node_count()

```python
def check_node_count(path: Path, lines: list[str]) -> list[Issue]:
    """Warn if diagram exceeds node limits (ADR-040 D3/D6)."""
    issues: list[Issue] = []
    fname = str(path)
    content = "\n".join(lines)

    # Skip -full reference diagrams
    if "-full." in path.name:
        return issues

    node_patterns = [
        r'\w+\["',        # flowchart: NodeId["
        r'\w+\[',         # flowchart: NodeId[
        r'\w+\(',         # flowchart: NodeId(
        r'\w+\{',         # flowchart: NodeId{
        r'class\s+\w+',   # classDiagram
        r'participant\s',  # sequenceDiagram
        r'state\s+\w+',   # stateDiagram
    ]
    node_count = 0
    for pattern in node_patterns:
        node_count += len(re.findall(pattern, content))

    if node_count > 35:
        issues.append(Issue(
            file=fname, severity="ERROR", rule="SIZE-001",
            message=f"~{node_count} nodes (>35 CRITICAL). Decompose.",
        ))
    elif node_count > 20:
        issues.append(Issue(
            file=fname, severity="WARNING", rule="SIZE-002",
            message=f"~{node_count} nodes (>20 soft limit).",
        ))
    return issues
```

### 3. Добавить check_subgraph_colours()

```python
def check_subgraph_colours(path: Path, lines: list[str]) -> list[Issue]:
    """Check subgraph styles use approved colour scheme (ADR-040 D1/D6)."""
    issues: list[Issue] = []
    fname = str(path)
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("style ") and "fill:" in stripped:
            fill_match = re.search(r"fill:(#[0-9a-fA-F]{6})", stripped)
            if fill_match and fill_match.group(1).lower() not in APPROVED_FILLS:
                issues.append(Issue(
                    file=fname, severity="WARNING", rule="COLOUR-001",
                    message=f"L{i+1}: Unapproved fill {fill_match.group(1)}",
                ))
    return issues
```

### 4. Добавить check_emoji_labels()

```python
EMOJI_PATTERN = re.compile(r'[\U0001F300-\U0001F9FF]')

def check_emoji_labels(path: Path, lines: list[str]) -> list[Issue]:
    """Check for emoji in subgraph labels (ADR-040 D1)."""
    issues: list[Issue] = []
    fname = str(path)
    for i, line in enumerate(lines):
        if "subgraph" in line and EMOJI_PATTERN.search(line):
            issues.append(Issue(
                file=fname, severity="ERROR", rule="COLOUR-002",
                message=f"L{i+1}: Emoji in subgraph label",
            ))
    return issues
```

### 5. Зарегистрировать в lint_file()

```python
def lint_file(path: Path, stale_days: int) -> list[Issue]:
    ...
    issues.extend(check_node_count(path, lines))
    issues.extend(check_subgraph_colours(path, lines))
    issues.extend(check_emoji_labels(path, lines))
    return issues
```

## Проверка
```bash
python scripts/lint_diagrams.py 2>&1 | grep -E "SIZE|COLOUR"
```

## Выходные артефакты
1. Обновлённый `scripts/lint_diagrams.py` с SIZE-001/002, COLOUR-001/002
```

---

## Промт 2: Завершить linkStyle дифференциацию (9 оставшихся view-файлов)

**Приоритет:** MEDIUM — 9 view-файлов всё ещё uniform
**Scope:** 9 `.mermaid` файлов

```
Режим: CODE

## Контекст
Main's `src/tools/differentiate_linkstyle.py` обработал 124 из 156 файлов.
9 non-full view-файлов остались с uniform `stroke:#475569,stroke-width:2px,stroke-dasharray:5`.
16 full-файлов — исключены by design (reference, linkStyle uniform допустим).

## Оставшиеся файлы
- 01-high-level-domain.mermaid
- 01-high-level-overview.mermaid
- 04-domain-layer-class-diagram-overview.mermaid
- 05-layers-interaction-domain.mermaid
- 12-local-deployment-architecture-domain.mermaid
- 14-provider-health-states-overview.mermaid
- 33-cli-run-interaction-domain.mermaid
- 36-architecture-principles-mindmap-overview.mermaid
- 50-exception-hierarchy-domain.mermaid

## Задача
Запустить `src/tools/differentiate_linkstyle.py` с `--force` флагом
или вручную применить дифференциацию к файлам.

Для файлов где <3 типов связей (все внутри одного subgraph) —
оставить uniform, но обновить стиль с generic (stroke:#475569) на data flow (stroke:#1E293B).

## Критерии
- Файлы с ≤5 связями: uniform `stroke:#1E293B,stroke-width:2px` (не dashed)
- Файлы с >5 связями и ≥2 типов: differentiated по ADR-040 D5

## Выходные артефакты
1. 9 обновлённых view-файлов
```

---

## Промт 3: Декомпозиция class-diagrams/ (НОВЫЙ — не было в v3.0)

**Приоритет:** LOW — class-diagrams имеют другую природу
**Scope:** `mmd-diagrams/class-diagrams/` (16 файлов)

```
Режим: DOC → CODE

## Контекст
class-diagrams/ содержат до 91 элемента (04-types-enums.mmd). Однако classDiagram
в Mermaid имеет другой layout engine и лучше обрабатывает много элементов.

## Анализ (NODE COUNTS)
| Файл | Элементов | Декомпозиция? |
|------|-----------|---------------|
| 04-types-enums.mmd | ~91 | Рассмотреть |
| 09-transformers.mmd | ~73 | Рассмотреть |
| 05-exceptions.mmd | ~51 | Опционально |
| 15-extractors.mmd | ~47 | Опционально |
| 14-observability.mmd | ~45 | Опционально |
| Остальные 11 | <40 | НЕ нужно |

## Решение
НЕ декомпозировать class-diagrams в рамках v4.0 — classDiagram тип
справляется с большим числом элементов. Но добавить @nodes метаданные
к class-diagrams/ файлам (аналогично architecture/).

## Задача
Для каждого из 16 файлов `class-diagrams/*.mmd`:
1. Подсчитать узлы
2. Добавить `%% @nodes <count>` после `%% @level`

## Выходные артефакты
1. 16 обновлённых `class-diagrams/*.mmd` с `@nodes`
```

---

## Промт 4: Drift check — foundation/*.mmd vs diagrams/mermaid/*-full.mermaid

**Приоритет:** MEDIUM — ADR-040 Risks: "Расхождение может возникнуть"
**Scope:** `scripts/` (новый скрипт или расширение lint)

```
Режим: CODE

## Контекст
ADR-040 упоминает риск: `foundation/*.mmd` и `diagrams/mermaid/*-full.mermaid`
могут разойтись. Митигация: "CI drift check (планируется)".

## Задача
Добавить проверку drift в lint_diagrams.py или отдельный скрипт.

### Логика
Для каждого `foundation/NN-name.mmd`:
1. Найти соответствующий `diagrams/mermaid/NN-name-full.mermaid`
2. Извлечь набор узлов (node IDs) из обоих файлов
3. Если набор узлов differs by >20% → WARNING
4. Если один файл существует а другой нет → INFO

### Пример вывода
```
DRIFT-001: 08-complete-etl-workflow: 3 nodes added in .mmd but absent in .mermaid
DRIFT-002: 14-provider-health-states: .mmd has 22 nodes, .mermaid has 19 (14% drift)
```

## Ограничения
- НЕ требовать 100% match — файлы могут иметь разную granularity
- Threshold: 20% — ниже этого drift допустим
- Запускать только при `--check-drift` флаге (не по умолчанию)

## Выходные артефакты
1. Скрипт или новая функция check_drift() в lint_diagrams.py
```

---

## Промт 5: Layout-хаки (точечно, после визуальной проверки)

**Приоритет:** LOW — применять ТОЛЬКО при подтверждённых проблемах
**Scope:** Конкретные файлы после рендеринга

```
Режим: CODE

(Содержание без изменений — перенесено из v3.0 Промт 6)

## Техники
A: Невидимые связи (A ~~~ C)
B: direction LR/TB в subgraph
C: Порядок объявления
D: Длина связей (ОСТОРОЖНО, ≤12 узлов)

## Правила
- `%% LAYOUT-HACK: <reason>` комментарий обязателен
- Max 3 невидимых связи на файл
- Если >5 хаков → вернуться к декомпозиции
```

---

## Порядок выполнения v4.0

```
Промт 1 ──→ Промт 2 ──→ Промт 3 ──→ Промт 4 ──→ Промт 5
(lint gaps)  (linkStyle)  (@nodes CD)  (drift)     (хаки)
HIGH         MEDIUM       LOW          MEDIUM       LOW
1 файл       9 файлов     16 файлов    1 файл       точечно
```

### Зависимости
- Промт 1 независим (lint improvement)
- Промт 2 независим (linkStyle completion)
- Промты 1+2 можно выполнить ПАРАЛЛЕЛЬНО
- Промт 3 независим
- Промт 4 зависит от Промта 1 (если встроен в lint)
- Промт 5 — ТОЛЬКО после визуальной проверки рендеров

### Изменения vs v3.0

| Промт v3.0 | Промт v4.0 | Что изменилось |
|-------------|-------------|----------------|
| 1: Гармонизация цветов | **УДАЛЁН** | Выполнен в main |
| 2: linkStyle | → Промт 2 (9 файлов) | Был 124 файла, осталось 9 |
| 3: Декомпозиция architecture/ | **УДАЛЁН** | Выполнен в main (11 файлов) |
| 4: lint + pre-commit | → Промт 1 (SIZE+COLOUR) | Базовый lint готов, нужны SIZE/COLOUR |
| 5: _template + @nodes | **УДАЛЁН** | Выполнен в main |
| 6: Layout-хаки | → Промт 5 | Без изменений |
| 7: ADR-040 | **УДАЛЁН** | Выполнен в main (D1-D7) |
| — | **НОВЫЙ Промт 3** | @nodes для class-diagrams/ |
| — | **НОВЫЙ Промт 4** | Drift check (foundation ↔ views) |

### Общий объём v4.0

| Категория | Файлов |
|-----------|--------|
| Обновлённые .mermaid (linkStyle) | ~9 |
| Обновлённые .mmd (@nodes) | ~16 |
| Обновлённые скрипты (lint) | 1 |
| **Итого** | **~26 файлов** |

Объём сократился с ~192 файлов (v3.0) до ~26 файлов (v4.0) благодаря
параллельной реализации в main.
