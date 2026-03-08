# BioETL: Промты для оптимизации архитектурных диаграмм v3.0

**Версия:** 3.0 | **Дата:** 2026-02-25
**Контекст:** Обновлено по актуальной ветке main (merge c5f760b)
**Отличия от v2.0:** Foundation-декомпозиция уже выполнена в main (156 файлов). Промт 1 удалён. Фокус сдвинут на качество существующих Views, architecture/ слой, lint и ADR.

---

## Текущее состояние (после merge main 2026-02-25)

### Файловая структура — ДВА каталога

```
docs/02-architecture/
├── mmd-diagrams/                          ← КАНОНИЧЕСКОЕ расположение (84 .mermaid)
│   ├── architecture/  (18 .mermaid)           ← НЕ декомпозированы
│   ├── class-diagrams/ (16 .mermaid)          ← НЕ декомпозированы
│   ├── foundation/    (50 .mermaid)           ← Исходники (с %%{init:})
│   ├── theme/
│   │   ├── mermaid-config.json            ← 131 строка, полная
│   │   └── custom.css                     ← 152 строки, layer colours
│   ├── render.sh                          ← SVG+PNG pipeline
│   └── README.md                          ← Каталог + цветовая схема
│
└── diagrams/                              ← LEGACY + НОВАЯ ДЕКОМПОЗИЦИЯ
    ├── mermaid/                            ← 156 .mermaid файлов (NEW в main!)
    │   ├── 00-legend.mermaid              ← Легенда (K01–K39 коды)
    │   ├── *-overview.mermaid (31 шт.)    ← ≤15 узлов
    │   ├── *-domain.mermaid  (31 шт.)     ← Домен-фокус
    │   ├── *-infra.mermaid   (31 шт.)     ← Инфра-маппинг
    │   ├── *-dataflow.mermaid (31 шт.)    ← Поток данных
    │   └── *-full.mermaid    (31 шт.)     ← Полные reference
    ├── diagram-views-inventory.md         ← Инвентаризация (31 parent)
    ├── diagram-views-plan.md              ← План декомпозиции
    ├── README.md                          ← View-навигация + онбординг
    ├── diagrams-index.md                  ← Обновлён (секция Diagram Views)
    └── 00-diagramming-policy.md           ← Политика
```

### Что выполнено в main

| Промт v1.0 | Статус | Результат |
|-------------|--------|-----------|
| П.1: Декомпозиция по Views | **ВЫПОЛНЕН** (foundation/) | 31 × 5 = 155 views + 1 legend = 156 файлов |
| П.2: Subgraph/namespace | **ЧАСТИЧНО** | Views используют subgraph, но без `namespace` для classDiagram |
| П.3: Визуальный вес | **ЧАСТИЧНО** | linkStyle есть, но одинаковый для всех связей |
| П.4: Шаблон + CI | **НЕ выполнен** | Нет `-template.mermaid`, lint не обновлён |
| П.5: Layout-хаки | **НЕ выполнен** | — |
| П.6: ADR | **НЕ выполнен** | — |

### КРИТИЧЕСКАЯ ПРОБЛЕМА: Расхождение цветовых схем

В проекте теперь ДВЕ конкурирующие палитры:

| Слой | `custom.css` (утверждённая) | `diagrams/mermaid/` (новая) | Конфликт |
|------|---------------------------|----------------------------|----------|
| Domain | `#f3e5f5` / `#6a1b9a` (purple) | `#FFF7ED` / `#F59E0B` (amber) | **ДА** |
| Application | `#e8f5e9` / `#2e7d32` (green) | `#ECFDF5` / `#10B981` (emerald) | **ДА** |
| Infrastructure | `#ffcdd2` / `#c62828` (red) | `#EFF6FF` / `#2563EB` (blue) | **ДА** |
| Composition | `#fff3e0` / `#e65100` (orange) | `#F5F3FF` / `#7C3AED` (violet) | **ДА** |
| Interfaces | `#e3f2fd` / `#1565c0` (blue) | `#F1F5F9` / `#64748B` (slate) | **ДА** |

**Все 5 слоёв** имеют разные цвета между `custom.css` и decomposed Views.
Это означает, что `render.sh` (использующий `custom.css`) перезатрёт inline-стили
только для subgraph с matching ID, но inline `style` в самих файлах
визуально не будет соответствовать цветовой схеме README.md.

### Другие расхождения

| Аспект | `mmd-diagrams/` (канонические) | `diagrams/mermaid/` (views) |
|--------|-------------------------------|---------------------------|
| Расширение | `.mermaid` | `.mermaid` |
| Метаданные | `@version`, `@date`, `@type`, `@level` | `%% View: ... \| Parent: ...` (1 строка) |
| `%%{init:}` | 55/84 файлов | 0/156 файлов |
| Render pipeline | `render.sh` (SVG+PNG, theme) | Нет своего render |
| Subgraph naming | ID = слой ("External", "Domain") | ID = слой + emoji ("🟡 Domain Layer") |
| linkStyle | Нет (стили через CSS) | Есть, но uniform (все одинаковые) |

---

## Промт 1: Гармонизация цветовой схемы (CRITICAL)

**Приоритет:** CRITICAL — без этого render.sh и inline-стили конфликтуют
**Scope:** 156 файлов `diagrams/mermaid/*.mermaid` + решение о canonical palette

```
Режим: CODE

## Контекст
В проекте сосуществуют ДВЕ цветовые схемы. Необходимо выбрать одну
и привести все файлы к единообразию.

## Решение: Принять существующую схему из custom.css + README.md

Обоснование:
- custom.css — утверждённая, задокументирована в README.md
- 84 .mermaid файла + render.sh уже используют эту схему
- POL-LLM-DIAGRAMS-001 ссылается на неё

### Целевая палитра (из custom.css строки 140-151)

| Слой | Fill | Stroke |
|------|------|--------|
| Domain | `#f3e5f5` | `#6a1b9a` |
| Application | `#e8f5e9` | `#2e7d32` |
| Infrastructure | `#ffcdd2` | `#c62828` |
| Composition | `#fff3e0` | `#e65100` |
| Interfaces | `#e3f2fd` | `#1565c0` |
| External | `#eceff1` | `#455a64` |

### Замены в 156 файлах `diagrams/mermaid/*.mermaid`

```
# Domain
sed -i 's/fill:#FFF7ED,stroke:#F59E0B/fill:#f3e5f5,stroke:#6a1b9a/g'

# Application
sed -i 's/fill:#ECFDF5,stroke:#10B981/fill:#e8f5e9,stroke:#2e7d32/g'

# Infrastructure
sed -i 's/fill:#EFF6FF,stroke:#2563EB/fill:#ffcdd2,stroke:#c62828/g'

# Composition
sed -i 's/fill:#F5F3FF,stroke:#7C3AED/fill:#fff3e0,stroke:#e65100/g'

# Interfaces
sed -i 's/fill:#F1F5F9,stroke:#64748B/fill:#e3f2fd,stroke:#1565c0/g'
```

### Также убрать emoji из subgraph labels (мешает CLI-рендерингу)

```
# "🟡 Domain Layer" → "Domain Layer"
# "🟢 Application Layer" → "Application Layer"
# "🔵 Infrastructure Layer" → "Infrastructure Layer"
# "🟣 Composition Layer" → "Composition Layer"
# "⚪ Interfaces Layer" → "Interfaces Layer"
```

## Проверка
1. `grep -r "FFF7ED\|ECFDF5\|EFF6FF\|F5F3FF\|F1F5F9" diagrams/mermaid/` — должно быть 0 результатов
2. `grep -r "🟡\|🟢\|🔵\|🟣\|⚪" diagrams/mermaid/` — должно быть 0 результатов
3. Рендер нескольких файлов через mmdc — визуальная проверка

## Выходные артефакты
1. Обновлённые 156 файлов `diagrams/mermaid/*.mermaid` с утверждённой палитрой
2. Обновлённый `diagrams/README.md` (если ссылается на старые цвета)
```

---

## Промт 2: Дифференциация linkStyle по типу связи

**Приоритет:** HIGH — все 155 view-файлов имеют uniform linkStyle
**Scope:** `diagrams/mermaid/*.mermaid` (156 файлов)

```
Режим: CODE

## Контекст
Все decomposed Views в `diagrams/mermaid/` используют одинаковый linkStyle
для всех связей (stroke:#475569, width:2px, dasharray:5). Это делает
диаграммы плоскими — нет визуального разделения типов связей.

## Классификация связей

| Тип | Критерий определения | Стиль |
|-----|---------------------|-------|
| Основной поток данных | `-->` между Bronze/Silver/Gold, между Adapter→Transformer→Writer | `stroke:#1E293B,stroke-width:3px` (сплошная, жирная) |
| Orchestration | `-->` от Runner/Executor к сервисам | `stroke:#2e7d32,stroke-width:2px` (зелёная, средняя) |
| Dependency/DI | `-.->` или связи `implements`/`injects` | `stroke:#6a1b9a,stroke-width:1.5px,stroke-dasharray:5` (пурпур, пунктир) |
| Observability | связи к Logger/Metrics/Tracing | `stroke:#94A3B8,stroke-width:1px` (серая, тонкая) |
| Error/Quarantine | связи к QuarantineWriter/ErrorHandler | `stroke:#c62828,stroke-width:2px,stroke-dasharray:4` (красная, пунктир) |

## Важное ограничение
linkStyle использует 0-based индексы. При изменении нужно:
1. Пересчитать все индексы
2. Добавить комментарий: `%% linkStyle: data 0-3, orch 4-7, DI 8-10, obs 11-12, err 13`

## Scope
Применить дифференциацию ТОЛЬКО к файлам, где ≥3 типов связей
(в основном *-overview и *-infra). Файлы с ≤5 связями — оставить uniform.

## Также обновить 00-legend.mermaid
Текущая легенда содержит 39 кодов K01–K39 без визуального разделения.
Добавить секцию "Link Weights" в начало:
```
subgraph LinkWeights["Link Types"]
    LW1[ ] -->|"data flow"| LW2[ ]
    LW3[ ] -.->|"DI/implements"| LW4[ ]
    LW5[ ] -->|"error"| LW6[ ]
end
```

## Выходные артефакты
1. Обновлённые view-файлы с дифференцированным linkStyle
2. Обновлённый `00-legend.mermaid`
```

---

## Промт 3: Декомпозиция architecture/ (18 .mermaid файлов)

**Приоритет:** HIGH — каноническое расположение НЕ затронуто декомпозицией
**Scope:** `mmd-diagrams/architecture/*.mermaid`

```
Режим: DOC → CODE

## Контекст
Main выполнил декомпозицию ТОЛЬКО для `foundation/` (50 → 155+full views).
Каталог `mmd-diagrams/architecture/` (18 файлов) — НЕ декомпозирован.
Эти файлы — каноническая архитектурная документация проекта.

## Инвентаризация architecture/*.mermaid

Перегруженные файлы (нужна декомпозиция):

| Файл | Узлов | Статус |
|------|-------|--------|
| `13-port-protocol-contracts.mermaid` | ~68 | CRITICAL |
| `01-high-level-hexagonal.mermaid` | ~39 | CRITICAL |
| `05-provider-adapter-hierarchy.mermaid` | ~27 | OVERLOADED |
| `12-bootstrap-di-container.mermaid` | ~29 | OVERLOADED |

Остальные 14 файлов — ≤20 узлов, декомпозиция НЕ нужна.

## Решение: Декомпозиция по subdomain (НЕ по view-type)

Foundation декомпозированы по 4 стандартным views (overview/domain/infra/dataflow).
Для architecture/ используем **предметную** декомпозицию — она семантически
точнее для reference-диаграмм:

### 13-port-protocol-contracts.mermaid (68 узлов → 4 файла)

| Файл | Содержание | ≤N узлов |
|------|-----------|----------|
| `13a-port-contracts-data-sources.mermaid` | DataSourcePort, FilterableDataSourcePort + 7 adapter-ов | ≤15 |
| `13b-port-contracts-storage.mermaid` | StoragePort, DeltaReaderPort, MetadataWriterPort + writers | ≤12 |
| `13c-port-contracts-observability.mermaid` | LoggerPort, MetricsPort, TracingPort, CircuitBreakerPort, RateLimiterPort | ≤15 |
| `13d-port-contracts-services.mermaid` | LockPort, CheckpointPort, QuarantinePort, AuditPort, PiiHasherPort, InputFilterPort, DQMonitorPort | ≤18 |

### 01-high-level-hexagonal.mermaid (39 узлов → 3 файла)

| Файл | Содержание | ≤N узлов |
|------|-----------|----------|
| `01a-hexagonal-overview.mermaid` | 5 layers + external APIs + dependency arrows | ≤15 |
| `01b-hexagonal-domain-app.mermaid` | Domain ports + Application services detail | ≤18 |
| `01c-hexagonal-infra-comp.mermaid` | Infrastructure adapters + Composition factories | ≤18 |

### 05-provider-adapter-hierarchy.mermaid (27 узлов → 2 файла)

| Файл | Содержание | ≤N узлов |
|------|-----------|----------|
| `05a-adapter-hierarchy-base.mermaid` | BaseHttpAdapter, mixins, decorators | ≤12 |
| `05b-adapter-hierarchy-providers.mermaid` | 7 concrete provider adapters + configs | ≤15 |

### 12-bootstrap-di-container.mermaid (29 узлов → 2 файла)

| Файл | Содержание | ≤N узлов |
|------|-----------|----------|
| `12a-bootstrap-factories.mermaid` | Все Factory-классы, Registry | ≤15 |
| `12b-bootstrap-wiring.mermaid` | Assembly sequence, injection graph | ≤15 |

## Формат новых файлов

Совместимый с существующими `@`-метаданными architecture/:
```
%% <Title — one-line description>
%% <Covers — what architectural aspect>

%% @version 1.0.0
%% @date    2026-02-25
%% @type    <flowchart|classDiagram>
%% @level   System / Component
%% @view    <data-sources|storage|observability|services|overview|domain-app|infra-comp|...>
%% @parent  <original-filename.mermaid>
%% @nodes   <count>
```

Стили subgraph — утверждённая палитра (из custom.css):
```
style Domain fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px
style Application fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
style Infrastructure fill:#ffcdd2,stroke:#c62828,stroke-width:2px
style Composition fill:#fff3e0,stroke:#e65100,stroke-width:2px
style Interfaces fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
```

## Обновление README
В `mmd-diagrams/README.md` добавить секцию "Decomposed Architecture Diagrams"
с таблицей parent → sub-файлы.

## Ограничения
- Максимум 20 узлов на файл (жёсткий лимит)
- Имена узлов строго из `src/bioetl/` (проверить grep-ом)
- Оригиналы НЕ удалять — оставить как reference
- НЕ трогать class-diagrams/ и foundation/

## Выходные артефакты
1. ~11 новых `.mermaid` файлов в `mmd-diagrams/architecture/`
2. `@nodes` метаданные добавлены к оригиналам (18 файлов)
3. Обновлённый `mmd-diagrams/README.md`
```

---

## Промт 4: Расширение lint-diagrams.py + pre-commit hook

**Приоритет:** MEDIUM — CI-валидация
**Scope:** `scripts/lint-diagrams.py` + `.pre-commit-config.yaml`

```
Режим: CODE

## Контекст
Существующий `scripts/lint-diagrams.py` (387 строк) работает ТОЛЬКО
с `docs/02-architecture/diagrams/*.mermaid` (legacy каталог).
Теперь в проекте ДВА каталога диаграмм:
1. `docs/02-architecture/mmd-diagrams/**/*.mermaid` — 84 канонических файла
2. `docs/02-architecture/diagrams/mermaid/*.mermaid` — 156 decomposed views

Текущие проверки lint-diagrams.py:
- META-001: Required headers (Title, Covers, Updated, Components)
- NAME-001: Naming convention (NN-topic.mermaid)
- CONTENT-001: Placeholder markers
- CONTENT-002: Minimum 3 non-comment lines
- STALE-001/002: Staleness detection
- EXT-001: .mermaid extension → ERROR (УСТАРЕЛО! .mermaid теперь каноническое)

## Задача

### 1. Поддержка обоих каталогов и расширений

```python
DIAGRAM-DIRS = [
    Path("docs/02-architecture/mmd-diagrams"),     # canonical .mermaid
    Path("docs/02-architecture/diagrams/mermaid"),  # decomposed .mermaid views
]

# Glob for both extensions
def find-diagram-files(base: Path) -> list[Path]:
    return sorted(
        list(base.rglob("*.mermaid")) +
        list(base.rglob("*.mermaid"))
    )
```

### 2. Удалить EXT-001

Удалить `check-extension-consistency()` — `.mermaid` теперь каноническое расширение.

### 3. Обновить NAMING-PATTERN

```python
# Поддержка: NN-topic.mermaid, NN-topic.mermaid, NNa-topic.mermaid, NN-topic-view.mermaid
NAMING-PATTERN = re.compile(
    r"^\d{2}[a-z]?-[a-z0-9]+(?:-[a-z0-9]+)*\.(?:mmd|mermaid)$"
)
```

### 4. Адаптировать META-001 для двух форматов метаданных

mmd-diagrams/ используют `@version`, `@date`, `@type`, `@level`.
diagrams/mermaid/ используют `%% View: ... | Parent: ...`.

```python
def check-metadata-headers(path: Path, lines: list[str]) -> list[Issue]:
    """Check for structured metadata — format depends on location."""
    issues: list[Issue] = []
    fname = str(path)

    if path.suffix == ".mermaid":
        # @-format metadata (mmd-diagrams/)
        required-tags = {"@version", "@date", "@type", "@level"}
        found-tags = set()
        for line in lines:
            for tag in required-tags:
                if line.strip().startswith(f"%% {tag}"):
                    found-tags.add(tag)
        missing = required-tags - found-tags
        for tag in sorted(missing):
            issues.append(Issue(
                file=fname, severity="WARNING", rule="META-001",
                message=f"Missing metadata: %% {tag}",
            ))
    else:
        # View-format metadata (diagrams/mermaid/)
        has-view = any(
            line.startswith("%% View:") or line.startswith("%% @view")
            for line in lines
        )
        if not has-view:
            issues.append(Issue(
                file=fname, severity="WARNING", rule="META-001",
                message="Missing %% View: metadata line",
            ))
    return issues
```

### 5. Добавить SIZE проверки

```python
def check-node-count(path: Path, lines: list[str]) -> list[Issue]:
    """Warn if diagram exceeds node limits."""
    issues: list[Issue] = []
    fname = str(path)
    content = "\n".join(lines)

    # Skip -full reference diagrams
    if "-full." in path.name:
        return issues

    node-patterns = [
        r'\w+\["',        # flowchart: NodeId["
        r'\w+\[',         # flowchart: NodeId[
        r'\w+\(',         # flowchart: NodeId(
        r'\w+\{',         # flowchart: NodeId{
        r'class\s+\w+',   # classDiagram
        r'participant\s',  # sequenceDiagram
        r'state\s+\w+',   # stateDiagram
    ]
    node-count = 0
    for pattern in node-patterns:
        node-count += len(re.findall(pattern, content))

    if node-count > 35:
        issues.append(Issue(
            file=fname, severity="ERROR", rule="SIZE-001",
            message=f"~{node-count} nodes (>35 CRITICAL). Decompose.",
        ))
    elif node-count > 20:
        issues.append(Issue(
            file=fname, severity="WARNING", rule="SIZE-002",
            message=f"~{node-count} nodes (>20 soft limit).",
        ))
    return issues
```

### 6. Добавить COLOUR проверку

```python
APPROVED-FILLS = {
    "#f3e5f5", "#e8f5e9", "#ffcdd2", "#fff3e0",
    "#e3f2fd", "#eceff1", "#fff8e1", "#ffebee",
}

def check-subgraph-colours(path: Path, lines: list[str]) -> list[Issue]:
    """Check subgraph styles use approved colour scheme."""
    issues: list[Issue] = []
    fname = str(path)
    for i, line in enumerate(lines):
        if line.strip().startswith("style ") and "fill:" in line:
            fill-match = re.search(r"fill:(#[0-9a-fA-F]{6})", line)
            if fill-match and fill-match.group(1).lower() not in APPROVED-FILLS:
                issues.append(Issue(
                    file=fname, severity="WARNING", rule="COLOUR-001",
                    message=f"L{i+1}: Unapproved fill {fill-match.group(1)}",
                ))
    return issues
```

### 7. Pre-commit hook

В `.pre-commit-config.yaml`, секция `- repo: local`:

```yaml
      - id: lint-diagrams
        name: Lint Mermaid/MMD diagram files
        entry: python scripts/lint-diagrams.py
        language: python
        pass-filenames: false
        files: '\.mermaid$|\.mermaid$'
```

## Ограничения
- НЕ создавать отдельный bash-скрипт
- Обратная совместимость с legacy `.mermaid`
- Node count — эвристика, ±20% допустимо

## Выходные артефакты
1. Обновлённый `scripts/lint-diagrams.py`
2. Обновлённый `.pre-commit-config.yaml`
```

---

## Промт 5: Шаблон -template.mermaid + стандартизация @nodes

**Приоритет:** MEDIUM — стандартизация метаданных
**Scope:** `mmd-diagrams/-template.mermaid` + 18 architecture/ файлов

```
Режим: CODE

## Контекст
Architecture/ файлы уже используют `@version`, `@date`, `@type`, `@level`.
Decomposed views используют `%% View: ... | Parent: ...`.
Нужен единый шаблон и добавление `@nodes` к architecture/.

## Задача

### Шаг 1: Создать -template.mermaid

Создать `docs/02-architecture/mmd-diagrams/-template.mermaid`:

```
%% <TITLE — one-line description>
%% <COVERS — what architectural aspect>

%% @version 1.0.0
%% @date    <YYYY-MM-DD>
%% @type    <flowchart|classDiagram|sequenceDiagram|stateDiagram|erDiagram|mindmap>
%% @level   <System / Component | Class | Sequence | State>
%% @view    <subdomain-name> (если декомпозирован)
%% @parent  <original-file.mermaid> (если декомпозирован)
%% @nodes   <approximate count>
%% @adr     <related ADR numbers>
%%
%% Styles: theme/mermaid-config.json + theme/custom.css
%% Colour scheme: see README.md § Colour Scheme
%% Subgraph palette:
%%   Domain:         fill:#f3e5f5,stroke:#6a1b9a
%%   Application:    fill:#e8f5e9,stroke:#2e7d32
%%   Infrastructure: fill:#ffcdd2,stroke:#c62828
%%   Composition:    fill:#fff3e0,stroke:#e65100
%%   Interfaces:     fill:#e3f2fd,stroke:#1565c0
%%   External:       fill:#eceff1,stroke:#455a64

flowchart TD
    %% === NODES ===

    %% === LINKS ===

    %% === SUBGRAPH STYLES ===
```

### Шаг 2: Добавить @nodes к architecture/ файлам

Для каждого из 18 файлов `architecture/*.mermaid`:
1. Подсчитать узлы (grep + manual)
2. Добавить ПОСЛЕ строки `%% @level`:
   ```
   %% @nodes   <count>
   ```
3. НЕ менять остальные метаданные

### Шаг 3: Foundation — НЕ трогать
Foundation файлы используют `%%{init:}` (legacy). Не тратить время.

## Выходные артефакты
1. `-template.mermaid`
2. 18 обновлённых `architecture/*.mermaid` с `@nodes`
```

---

## Промт 6: Layout-хаки (точечно, после визуальной проверки)

**Приоритет:** LOW — применять ТОЛЬКО при подтверждённых проблемах
**Scope:** Конкретные файлы после рендеринга

```
Режим: CODE

## Контекст
После Промтов 1–5 необходимо отрендерить диаграммы и визуально проверить.
Layout-хаки применяются ТОЛЬКО к файлам с подтверждёнными проблемами
(пересечения связей, слипание узлов).

## Техники

### A: Невидимые связи (Mermaid ≥10.6)
```mermaid
A ~~~ C  %% LAYOUT-HACK: force same rank
```

### B: Direction subgraph
```mermaid
subgraph Ports["Domain Ports"]
    direction LR  %% горизонтальная раскладка
end
```

### C: Порядок объявления (влияет на rank)
1. Верхние узлы объявляются первыми
2. Связи сверху вниз
3. Межслойные связи в конце

### D: Длина связей (ОСТОРОЖНО, ≤12 узлов)
```mermaid
A --> B       %% short
C ----> D     %% longer
```

## Правила
- `%% LAYOUT-HACK: <reason>` комментарий обязателен
- Max 3 невидимых связи на файл
- Если >5 хаков → вернуться к декомпозиции

## Критерии перехода на PlantUML/D2
| ≤20 узлов | Mermaid |
| 20–40 complex | PlantUML |
| >40 | D2 (ELK) |

## Выходные артефакты
1. Исправленные `.mermaid` / `.mermaid` файлы
2. PNG до/после
```

---

## Промт 7: ADR-040 Diagram Governance

**Приоритет:** GOVERNANCE — фиксация решений
**Scope:** `docs/02-architecture/decisions/ADR-040-diagram-governance.md` + README обновления

```
Режим: DOC

## Задача
Создать `docs/02-architecture/decisions/ADR-040-diagram-governance.md`.

### Содержание

```markdown
# ADR-040: Diagram Governance and Layout Policy

## Status
Accepted

## Date
2026-02-25

## Context
BioETL содержит два каталога диаграмм:
- `docs/02-architecture/mmd-diagrams/` — 84 канонических `.mermaid` файла
  (architecture: 18, class-diagrams: 16, foundation: 50)
- `docs/02-architecture/diagrams/mermaid/` — 156 decomposed `.mermaid` views
  (31 parent × 5 views + legend)

Foundation-диаграммы декомпозированы по Views (overview/domain/infra/dataflow/full).
Architecture-диаграммы — частично (4 OVERLOADED файла → 11 sub-файлов).

Существующая инфраструктура:
- Тема: `theme/mermaid-config.json` + `theme/custom.css`
- Render: `render.sh` (SVG + PNG)
- Lint: `scripts/lint-diagrams.py` (расширен для .mermaid + .mermaid)

## Decision

### D1: Canonical Colour Scheme
Единая палитра зафиксирована в `theme/custom.css` строки 140-151.
Все inline `style` в `.mermaid` и `.mermaid` файлах MUST использовать эту палитру.
Domain=purple (`#f3e5f5`/`#6a1b9a`), Application=green, Infrastructure=red.

### D2: Dual Repository Structure
- `.mermaid` в `mmd-diagrams/` — каноническое расположение для НЕ-decomposed
- `.mermaid` в `diagrams/mermaid/` — decomposed views (foundation)
- Новые architecture views создаются как `.mermaid` в `mmd-diagrams/architecture/`

### D3: View-based Decomposition Rules
- Hard limit: 20 узлов на view-файл (Mermaid Dagre constraint)
- Soft limit: 15 узлов (рекомендуемый)
- Файлы >35 узлов = CRITICAL, декомпозиция обязательна
- foundation/ декомпозированы по 4 стандартным views
- architecture/ декомпозируются по subdomain (предметная группировка)
- Оригиналы сохраняются как *-full reference

### D4: Metadata Formats
- `.mermaid` файлы: `@version`, `@date`, `@type`, `@level`, `@nodes`
- `.mermaid` views: `%% View: <type> | Parent: <file>`

### D5: CI Validation
`scripts/lint-diagrams.py` проверяет оба каталога:
- SIZE-001/002: node limits
- META-001: metadata presence
- COLOUR-001: approved palette
Pre-commit hook: `lint-diagrams`.

### D6: Tool Selection Criteria
| ≤20 узлов | Mermaid |
| 20–40, complex layout | PlantUML |
| >40 | D2 (ELK layout) |

## Consequences

### Positive
- Единая палитра, нет визуальных конфликтов
- CI предотвращает деградацию
- Два каталога позволяют независимое развитие views

### Negative
- Два каталога + два расширения — cognitive overhead
- Синхронизация foundation/*.mermaid ↔ diagrams/mermaid/*-full.mermaid

### Risks
- linkStyle индексы хрупкие
- Эвристика подсчёта узлов — ±20%

## Related ADRs
- ADR-005 (Layered Architecture)
- ADR-020 (Composition Layer)
```

### Также обновить
1. `mmd-diagrams/README.md` — ссылка на ADR-040
2. `diagrams/README.md` — ссылка на ADR-040
3. `06-diagram-policy.md` — ссылка на ADR-040

## Выходные артефакты
1. `ADR-040-diagram-governance.md`
2. 3 обновлённых README/policy файла
```

---

## Порядок выполнения v3.0

```
Промт 1 ──→ Промт 2 ──→ Промт 3 ──→ Промт 5 ──→ Промт 4 ──→ Промт 6 ──→ Промт 7
(цвета)     (linkStyle)  (arch views) (template)   (lint+CI)    (хаки)      (ADR)
CRITICAL    HIGH         HIGH         MEDIUM       MEDIUM       LOW         GOVERNANCE
156 files   ~80 files    ~11 new      ~19 files    2 files      точечно     4 files
```

### Зависимости
- Промт 1 БЛОКИРУЕТ все остальные (цветовая гармонизация первична)
- Промт 2 зависит от Промта 1 (linkStyle должен быть на правильных цветах)
- Промт 3 независим от Промта 2, но лучше после 1
- Промты 4 и 5 независимы, можно параллельно
- Промт 6 — ТОЛЬКО после визуальной проверки рендеров
- Промт 7 — после стабилизации решений

### Изменения vs v2.0

| Промт v2.0 | Промт v3.0 | Что изменилось |
|-------------|-------------|----------------|
| 1: Декомпозиция CRITICAL (foundation) | **УДАЛЁН** | Уже выполнен в main (156 файлов) |
| 2: Subgraph | Поглощён Промтом 1 + 3 | Subgraph уже есть в views; focus на цвета |
| 3: linkStyle | → Промт 2 | Без изменений по сути |
| 4: lint-diagrams.py | → Промт 4 | Адаптирован для двух каталогов |
| 5: Template | → Промт 5 | Без изменений |
| 6: Layout | → Промт 6 | Без изменений |
| 7: ADR-040 | → Промт 7 | Обновлён: dual-repo, два расширения |
| — | **НОВЫЙ Промт 1** | Гармонизация цветов (156 файлов) |
| — | **НОВЫЙ Промт 3** | Декомпозиция architecture/ (11 файлов) |

### Общий объём v3.0

| Категория | Файлов |
|-----------|--------|
| Обновлённые .mermaid (цвета + linkStyle) | ~156 |
| Новые .mermaid (architecture decomposition) | ~11 |
| Обновлённые .mermaid (метаданные @nodes) | ~18 |
| Новые файлы (template) | 1 |
| Обновлённые скрипты | 1 (lint-diagrams.py) |
| Обновлённый pre-commit | 1 |
| Новый ADR | 1 |
| Обновлённая документация | 3–4 (READMEs, policy) |
| **Итого** | **~192 файла** |
