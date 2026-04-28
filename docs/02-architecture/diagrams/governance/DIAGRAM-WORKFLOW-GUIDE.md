______________________________________________________________________

Version: 1.1.1
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Руководство по работе с диаграммами BioETL

______________________________________________________________________

## 1. Обзор системы диаграмм

Проект BioETL поддерживает **289 tracked diagram files**:
**127** `.mmd`-артефактов в canonical tree (`architecture/`, `class-diagrams/`,
`foundation/`, `_template.mmd`) и **162** `.mermaid` view-файла в `views/`
(34 parent families, 161 derived views и `00-legend.mermaid`). Вся система
подчинена ADR-040 — решению об управлении диаграммами, которое определяет
цветовую палитру, метаданные, правила lint-проверки и стратегии компоновки.

### 1.1. Двойная структура хранения

**Канонические исходники** — `docs/02-architecture/diagrams/`:

| Каталог           | Файлов | Назначение                                             |
| ----------------- | ------ | ------------------------------------------------------ |
| `architecture/`   | 52     | Системные и компонентные диаграммы уровня архитектуры  |
| `class-diagrams/` | 19     | UML-классы: порты, сущности, агрегаты, конфиги         |
| `foundation/`     | 55     | Исторические эталонные диаграммы, TOP-25 архитектурных |

**Декомпозированные представления** — `docs/02-architecture/diagrams/views/` (162 файла):

Большинство foundation families разворачиваются в стандартный набор из
**5 представлений (views)**:

- `*-full.mermaid` — полная копия-эталон
- `*-overview.mermaid` — кросс-слойный обзор (до 15 нод)
- `*-domain.mermaid` — фокус на domain-слой
- `*-infra.mermaid` — маппинг infrastructure
- `*-dataflow.mermaid` — поток данных

Дополнительно есть узкие architecture-derived families с сокращённым набором
views (`03-medallion-data-flow`, `13-port-protocol-contracts`,
`16-transformer-hierarchy`) и служебный `00-legend.mermaid`.
Количество views следует текущему tracked decomposition baseline и
обновляется вместе с добавлением новых parent-диаграмм и derived slices.

### 1.2. Поддерживаемые типы диаграмм

| Тип               | Где применяется                                      | Примеры                                    |
| ----------------- | ---------------------------------------------------- | ------------------------------------------ |
| `flowchart`       | ETL-пайплайны, потоки управления, архитектурные слои | medallion-data-flow, pipeline-execution    |
| `sequenceDiagram` | Временные взаимодействия, протоколы                  | lock-acquisition, client-api-request       |
| `classDiagram`    | Иерархии классов, порты, адаптеры                    | domain-ports, entities-aggregates          |
| `stateDiagram`    | Конечные автоматы                                    | pipeline-lifecycle-states, circuit-breaker |
| `erDiagram`       | Связи между сущностями                               | full-er-diagram                            |
| `mindmap`         | Иерархическое мышление                               | architecture-principles-mindmap            |

### 1.3. Граница между canonical sources и publication artifacts

Canonical source of truth для диаграмм остаётся в `.mmd`-деревьях
`architecture/`, `class-diagrams/` и `foundation/`, а также в derived source
tree `views/*.mermaid`. Файлы в `svg/`, `png/`, `bundles/`, `descriptions/` и
дополнительные `INDEX.md` следует трактовать как publication artifacts.

Для Markdown bundle publication первичным render artifact теперь считается
`svg/`. Деревья `png/` сохраняются как compatibility/export layer и не должны
снова трактоваться как единственный обязательный surface для чтения bundle-файлов.

Для Markdown bundle generation каноническими публичными entrypoints теперь считаются:

```bash
python -m scripts.diagrams render-pdf
python -m scripts.diagrams render-views
```

Нижележащий backend `python -m scripts.diagrams.generate_all_bundles --collection <name>`
остаётся canonical leaf implementation, но для обычных пользователей и
документации следует предпочитать router surface `scripts.diagrams`.

Legacy entrypoints `generate_architecture_bundle.py` и
`generate_views_bundle.py` поддерживаются как compatibility wrappers и не
должны снова расходиться по поведению с canonical generator. Когда нужно
исправить drift, предпочтительно регенерировать только затронутую коллекцию,
а не выполнять широкое обновление всех derived artifacts сразу.

______________________________________________________________________

## 2. Метаданные и шаблон

### 2.1. Обязательные заголовки `.mmd`

Каждый канонический `.mmd`-файл обязан содержать метаданные:

```
%% BioETL — <заголовок>
%% <Что охватывает>

%% @version 1.0.0
%% @date    2026-02-26
%% @type    flowchart
%% @level   System / Component
%% @nodes   25
%% @adr     ADR-040
```

Тег `@nodes` критически важен: он определяет, будет ли применён ELK layout, и влияет на lint-проверки `SIZE-001`/`SIZE-002`.

### 2.2. Заголовки `.mermaid` views

Для декомпозированных представлений формат короче:

```
%% View: Overview | Parent: 01-high-level-full.mermaid
```

### 2.3. Шаблон

Файл `diagrams/_template.mmd` содержит эталонные секции: все метаданные с пояснениями, copy-paste палитру цветов, примеры фигур нод, типы связей, стилизацию subgraph, инструкции по ELK layout и выбору направления.

______________________________________________________________________

## 3. Цветовая схема

### 3.1. Цвета слоёв

Каноническая палитра определена в `theme/custom.css` и строго обязательна. Произвольные hex-цвета запрещены — используются только канонические значения.

| Слой           | Fill      | Stroke             | Семантика                              |
| -------------- | --------- | ------------------ | -------------------------------------- |
| Domain         | `#f5f3ff` | `#7c3aed` (Purple) | Бизнес-логика, entities, value objects |
| Application    | `#f0fdf4` | `#16a34a` (Green)  | Сервисы, оркестрация, use cases        |
| Infrastructure | `#fff1f2` | `#dc2626` (Red)    | Адаптеры, клиенты, хранилище           |
| Composition    | `#fff7ed` | `#f59e0b` (Orange) | Фабрики, DI, сборка                    |
| Interfaces     | `#eff6ff` | `#2563eb` (Blue)   | CLI, API, внешние интерфейсы           |
| External       | `#f1f5f9` | `#64748b` (Gray)   | Сторонние системы                      |

### 3.2. Цвета Medallion

| Слой       | Fill      | Stroke             |
| ---------- | --------- | ------------------ |
| Bronze     | `#fff7ed` | `#f59e0b` (Orange) |
| Silver     | `#f8fafc` | `#475569` (Slate)  |
| Gold       | `#fefce8` | `#ca8a04` (Amber)  |
| Quarantine | `#ffe4e6` | `#e11d48` (Red)    |

### 3.3. Тема Mermaid

Конфигурация рендеринга: `theme/mermaid-config.json` (131 строка) — полная инициализация Mermaid. CSS-стили: `theme/custom.css` (152 строки) — цвета слоёв, стилизация subgraph.

______________________________________________________________________

## 4. ELK Layout и edgeRouting

### 4.1. Зачем нужен ELK

По умолчанию Mermaid использует движок **Dagre**, который оптимизирует компактность и минимизацию пересечений, но не гарантирует ортогональность рёбер — стрелки могут входить в ноды под произвольными углами. **ELK (Eclipse Layout Kernel)** решает эту проблему.

### 4.2. Когда применять

| Число нод | Движок               | Lint-правило       |
| --------- | -------------------- | ------------------ |
| 1–20      | Dagre (по умолчанию) | Нет                |
| 21–40     | ELK (рекомендуется)  | LAYOUT-001 (WARN)  |
| >40       | ELK (обязательно)    | LAYOUT-002 (ERROR) |

ELK применяется **только** к `flowchart`/`graph`. Для `classDiagram`, `sequenceDiagram`, `stateDiagram`, `erDiagram` и `mindmap` он не поддерживается — эти типы используют собственные layout-движки.

### 4.3. Синтаксис ELK init

Директива вставляется **перед** объявлением `graph` или `flowchart`:

```
%%{init: {'layout': 'elk', 'theme': 'base', 'themeVariables': {'fontFamily': 'Inter, Roboto, sans-serif'}, 'elk': {'mergeEdges': true, 'nodePlacementStrategy': 'BRANDES_KOEPF', 'cycleBreakingStrategy': 'GREEDY', 'direction': 'RIGHT', 'spacing.nodeNode': 40, 'spacing.edgeNode': 30, 'spacing.edgeEdge': 20, 'edgeRouting': 'ORTHOGONAL'}}}%%
flowchart TB
```

**Параметры ELK:**

| Параметр                | Значение          | Эффект                                                   |
| ----------------------- | ----------------- | -------------------------------------------------------- |
| `mergeEdges`            | `true`            | Сливает параллельные рёбра и снижает визуальный шум      |
| `nodePlacementStrategy` | `'BRANDES_KOEPF'` | Более чистое layered-расположение                        |
| `cycleBreakingStrategy` | `'GREEDY'`        | Стабильнее разрывает циклы в плотных графах              |
| `spacing.nodeNode`      | `40`              | Добавляет отступы между нодами                           |
| `spacing.edgeNode`      | `30`              | Разводит рёбра и ноды                                    |
| `spacing.edgeEdge`      | `20`              | Уменьшает пересечения рёбер                              |
| `edgeRouting`           | `'ORTHOGONAL'`    | Рёбра проходят строго под углами 90° (Manhattan routing) |

Параметр `edgeRouting: 'ORTHOGONAL'` — ключевой для получения аккуратных прямоугольных стрелок. Без него ELK использует режим `POLYLINE` или `SPLINES`, и стрелки по-прежнему могут быть диагональными.

### 4.4. Выбор направления

| Паттерн диаграммы                 | Direction         | Обоснование                                 |
| --------------------------------- | ----------------- | ------------------------------------------- |
| Иерархия, DI-граф, port-map       | `TB` (top-down)   | Вертикаль подчёркивает слои                 |
| Pipeline, data flow, config chain | `LR` (left-right) | Горизонталь подчёркивает последовательность |

### 4.5. Автоматизация: apply_elk_layout.py

Утилита `src/tools/apply_elk_layout.py` автоматически добавляет ELK init к диаграммам, превышающим порог нод:

```bash
# Предварительный просмотр (без записи)
python src/tools/apply_elk_layout.py --dry-run

# Применить к architecture/ (по умолчанию)
python src/tools/apply_elk_layout.py

# Применить ко всем .mmd в foundation/
python src/tools/apply_elk_layout.py --dir docs/02-architecture/diagrams/foundation

# Свой порог (по умолчанию 20)
python src/tools/apply_elk_layout.py --threshold 15

# Принудительно выровнять routing у уже существующих ELK-диаграмм
python src/tools/apply_elk_layout.py --enforce-routing ORTHOGONAL
```

Скрипт парсит `@nodes`, проверяет тип диаграммы, пропускает файлы с уже установленной директивой, и опционально меняет направление TB→LR для pipeline-паттернов (medallion, data-flow, storage-layer, config, cli-interface).

Если для конкретной диаграммы осознанно нужен `POLYLINE`, добавьте маркер-комментарий:

```mermaid
%% @allow-polyline-routing
```

______________________________________________________________________

## 5. Семантические стили связей (linkStyle)

### 5.1. Классификация рёбер

Инструмент `src/tools/differentiate_linkstyle.py` классифицирует связи по 6 семантическим типам:

| Тип                  | Стиль                                 | Семантика                                  |
| -------------------- | ------------------------------------- | ------------------------------------------ |
| **data**             | `stroke:#1E293B, width:2px`           | Поток данных, чтение/запись                |
| **orchestration**    | `stroke:#16a34a, width:2px`           | Вызовы сервисов, управление                |
| **DI/implements**    | `stroke:#7c3aed, width:1.5px, dashed` | Dependency injection, реализация протокола |
| **observability**    | `stroke:#94A3B8, width:1px`           | Логирование, метрики, трейсинг             |
| **error/quarantine** | `stroke:#dc2626, width:2px, dashed`   | Обработка ошибок, карантин                 |
| **generic**          | `stroke:#475569, width:2px, dashed`   | Неопределённые связи                       |

### 5.2. Когда применяется

Инструмент активируется, если диаграмма:

- Тип `flowchart`
- Все существующие `linkStyle` однородны (одинаковый стиль)
- Более 5 связей
- 3+ различных семантических типа обнаружено

### 5.3. Эвристики классификации

Рёбра классифицируются по: типу стрелки (`.` = dashed → DI), ключевым словам в метках (implement, inject → DI), принадлежности целевой ноды к domain-subgraph (→ DI), ключевым словам observability в ID нод, целям quarantine/error, кросс-слойным связям с Infrastructure (→ data).

```bash
python src/tools/differentiate_linkstyle.py --dry-run   # Предпросмотр
python src/tools/differentiate_linkstyle.py              # Применить
```

______________________________________________________________________

## 6. Lint-проверки и CI

### 6.1. Правила lint_diagrams.py

| Правило     | Severity | Условие                                                                  |
| ----------- | -------- | ------------------------------------------------------------------------ |
| SIZE-001    | ERROR    | @nodes > 35                                                              |
| SIZE-002    | WARN     | @nodes > 20                                                              |
| SIZE-003    | WARN     | @nodes > 35, но есть декомпозированные sibling-файлы (`01a/01b/...`)     |
| META-001    | WARN     | Нет `@version`/`@date`/`@type`/`@level` в `.mmd`                         |
| META-002    | ERROR    | Некорректный формат даты в `%% Updated:`/`%% @date`                      |
| CONTENT-001 | ERROR    | Содержит placeholder/TODO/FIXME/stub                                     |
| CONTENT-002 | ERROR    | Менее 3 непустых строк                                                   |
| STALE-001   | ERROR    | `@date` старше 180 дней                                                  |
| STALE-002   | WARN     | `@date` старше 90 дней                                                   |
| COLOUR-001  | ERROR    | Deprecated палитра Tailwind в `style`/`classDef`                         |
| COLOUR-002  | ERROR    | Emoji в subgraph labels                                                  |
| LAYOUT-001  | WARN     | flowchart/@nodes > 20 без ELK init                                       |
| LAYOUT-002  | ERROR    | flowchart/@nodes > 40 без ELK init                                       |
| LINK-001    | WARN     | Плотный flowchart использует только один тип стрелок                     |
| LINK-002    | WARN     | Хрупкий singleton-паттерн в `linkStyle` (много индексных строк `1:1`)    |
| GRAPH-001   | WARN     | Orphan-ноды (определены, но не в рёбрах)                                 |
| NBSP-001    | ERROR    | Используется `&nbsp;`-padding в исходнике                                |
| CLASS-001   | WARN     | Неэкранированный dunder-метод в classDiagram (`__enter__`)               |
| CLASS-002   | WARN     | Смешанный стиль return-нотации методов (`): Type` и `) Type`)            |
| CLASS-003   | WARN     | Сигнатура метода слишком длинная для стабильного рендера (>~88 символов) |

Исключения: `-full.mermaid` reference views и `00-legend*` освобождены от SIZE-001/SIZE-002.

```bash
python scripts/diagrams/lint_diagrams.py                  # Проверить всё
python scripts/diagrams/lint_diagrams.py --json           # JSON-вывод для CI
python scripts/diagrams/lint_diagrams.py --stale-days 120 # Свой порог
python scripts/diagrams/check_class_method_render_integrity.py \
  --source-dir docs/02-architecture/diagrams/class-diagrams \
  --svg-dir docs/02-architecture/diagrams/class-diagrams/svg
```

### 6.2. Управление orphan-нодами

Скрипт `scripts/diagrams/prune_orphan_nodes.py` находит ноды, определённые в диаграмме, но не участвующие ни в одном ребре.

```bash
python scripts/diagrams/prune_orphan_nodes.py --check        # Отчёт (exit 1 при нахождении)
python scripts/diagrams/prune_orphan_nodes.py --check --json  # JSON для CI
python scripts/diagrams/prune_orphan_nodes.py --fix           # Удалить orphan-ноды
python scripts/diagrams/prune_orphan_nodes.py --grandfather   # Пометить все текущие как допустимые
```

Нода **не считается orphan**, если:

- Помечена аннотацией `%% keep-orphan: NodeId`
- Находится в subgraph, родитель которого участвует в рёбрах
- Файл — `00-legend*`

### 6.3. Pre-commit хуки

Два хука в `.pre-commit-config.yaml`:

| Хук                          | Скрипт                                           | Назначение            |
| ---------------------------- | ------------------------------------------------ | --------------------- |
| `lint-diagrams`              | `scripts/diagrams/lint_diagrams.py`              | Валидация всех правил |
| `prune-orphan-diagram-nodes` | `scripts/diagrams/prune_orphan_nodes.py --check` | Детекция orphan-нод   |

### 6.4. Проверка видимости текста в SVG

Скрипт `scripts/diagrams/check_svg_text_visibility.py` валидирует smoke-набор SVG на предмет
типичного регресса: edge-label отображается как белый прямоугольник без видимого текста.

Проверки скрипта:

- наличие `fo-fallback` текстовых узлов при `foreignObject`-лейблах;
- наличие читаемого текста в `g.edgeLabel`;
- наличие инжектированных CSS-правил для `.edgeLabel span` и `text.fo-fallback`.

```bash
python scripts/diagrams/check_svg_text_visibility.py --manifest docs/02-architecture/diagrams/manifests/visual-smoke.txt
python scripts/diagrams/check_svg_text_visibility.py --manifest docs/02-architecture/diagrams/manifests/visual-smoke.txt --json
```

______________________________________________________________________

## 7. Плотность нод и декомпозиция

### 7.1. Пороги

| Число нод | Статус       | Действие                   |
| --------- | ------------ | -------------------------- |
| 1–15      | Оптимально   | Диаграмма самодостаточна   |
| 16–20     | Мягкий лимит | Рассмотреть декомпозицию   |
| 21–35     | WARN         | Декомпозиция рекомендована |
| >35       | CRITICAL     | Декомпозиция обязательна   |

### 7.2. Стратегия декомпозиции

При превышении 35 нод диаграмма разбивается на субдоменные файлы с суффиксами `a`, `b`, `c`, `d`. Пример:

```
13-port-protocol-contracts.mmd      → основной (до 35 нод)
13a-port-contracts-data-sources.mmd → фокус на data source ports
13b-port-contracts-storage.mmd      → фокус на storage ports
13c-port-contracts-observability.mmd → фокус на observability
13d-port-contracts-services.mmd     → фокус на service ports
```

______________________________________________________________________

## 8. Рендеринг

### 8.1. Конвейер рендеринга

```bash
# Linux/WSL/Windows (Git Bash, WSL, CI)
bash docs/02-architecture/diagrams/tooling/render.sh
```

Формат вывода: SVG + PNG (base 300 DPI). Применяется тема из `theme/mermaid-config.json` и `theme/custom.css`. SVG-файлы дополнительно оптимизируются через SVGO (`svgo.config.js`).
Для больших диаграмм рендерер автоматически повышает разрешение PNG по `@nodes` (по умолчанию `@nodes >= 30`): `scale=4`, `DPI=450`.
Также поддерживаются per-file overrides в исходнике диаграммы:

```text
%% @png-scale 6
%% @png-dpi   600
```

Результат записывается в `<source-dir>/svg/` и `<source-dir>/png/` рядом с исходником диаграммы.

______________________________________________________________________

## 9. Типичный workflow создания диаграммы

1. **Скопировать шаблон:** `cp _template.mmd architecture/NN-topic.mmd`
1. **Заполнить метаданные:** `@version`, `@date`, `@type`, `@level`, `@nodes`
1. **Нарисовать диаграмму:** использовать каноническую палитру цветов
1. **Проверить lint:** `python scripts/diagrams/lint_diagrams.py`
1. **Применить ELK** (если @nodes > 20): `python src/tools/apply_elk_layout.py`
1. **Применить linkStyle** (если flowchart с 5+ связями): `python src/tools/differentiate_linkstyle.py`
1. **Проверить orphan-ноды:** `python scripts/diagrams/prune_orphan_nodes.py --check`
1. **Отрендерить:** `bash docs/02-architecture/diagrams/tooling/render.sh`
   Для усиленного рендера больших схем можно задать: `--large-threshold`, `--large-scale`, `--large-png-dpi`.
1. **Проверить обязательные SVG-артефакты:** `python scripts/diagrams/check_diagram_artifacts.py --manifest docs/02-architecture/diagrams/manifests/visual-smoke.txt`
   Для дополнительной compatibility-проверки PNG используйте curated manifest: `python scripts/diagrams/check_diagram_artifacts.py --manifest docs/02-architecture/diagrams/manifests/png-compatibility.txt --require-png`
1. **Проверить видимость текста в SVG:** `python scripts/diagrams/check_svg_text_visibility.py --manifest docs/02-architecture/diagrams/manifests/visual-smoke.txt`
1. **Прогнать quality-gates:** `python scripts/diagrams/check_diagram_quality_gates.py --manifest docs/02-architecture/diagrams/manifests/quality-gates.txt`
1. **Добавить в индекс:** обновить `README.md` каталога

### 9.1. PR-checklist для `classDiagram`

Перед merge изменений в `class-diagrams/*.mmd` проверьте:

1. Все dunder-методы экранированы (`+\_\_enter\_\_()`, `+\_\_aexit\_\_(...)`), правило `CLASS-001`.
1. Внутри одного файла не смешиваются стили return-нотации (`): Type` и `) Type`), правило `CLASS-002`.
1. Нет перегруженных сигнатур методов длиннее ~88 символов, правило `CLASS-003`.
1. L1-диаграмма содержит только ключевые методы, вторичные операции вынесены в companion L2 (`01a/08a/14a` и т.д.).
1. Выполнен `python scripts/diagrams/lint_diagrams.py docs/02-architecture/diagrams/class-diagrams`.
1. Выполнен `python scripts/diagrams/check_class_method_render_integrity.py --source-dir docs/02-architecture/diagrams/class-diagrams --svg-dir docs/02-architecture/diagrams/class-diagrams/svg`.
1. Перерендерены изменённые диаграммы через `render.sh`, обязательные `svg`-артефакты обновлены, а `png` обновлены там, где они остаются compatibility/export surface.
1. Нет drift между `.mmd` и рендер-артефактами в PR.

______________________________________________________________________

## 10. Сводная таблица инструментов

| Инструмент                     | Расположение        | Назначение                                                                          |
| ------------------------------ | ------------------- | ----------------------------------------------------------------------------------- |
| run_diagram_checks.sh          | `scripts/diagrams/` | Единый запуск профилей проверок (`pr`/`nightly`/`quick`)                            |
| apply_elk_layout.py            | `src/tools/`        | Добавление ELK init к flowchart с >20 нод                                           |
| differentiate_linkstyle.py     | `src/tools/`        | Семантическая стилизация рёбер                                                      |
| lint_diagrams.py               | `scripts/diagrams/` | Lint-проверка по 14 правилам                                                        |
| prune_orphan_nodes.py          | `scripts/diagrams/` | Детекция и удаление orphan-нод                                                      |
| check_diagram_artifacts.py     | `scripts/diagrams/` | DIAG-T010/T012 для обязательных SVG и DIAG-T011/T012 для optional PNG compatibility |
| check_svg_text_visibility.py   | `scripts/diagrams/` | Smoke-проверка видимости текста в SVG                                               |
| check_diagram_quality_gates.py | `scripts/diagrams/` | DIAG-T018..T023 (style/classDef/decomposition/legend/labels)                        |
| run_diagram_nightly_suite.py   | `scripts/diagrams/` | DIAG-T024..T029 nightly heuristics (interactivity/chaos/growth/theme)               |
| render.sh                      | `diagrams/`         | Рендеринг SVG + PNG (300 DPI, auto-hires + `@png-scale/@png-dpi`)                   |

______________________________________________________________________

## 11. Единый запуск проверок

Для локального и CI-совместимого запуска используйте единый раннер:

```bash
scripts/diagrams/run_diagram_checks.sh --profile pr
```

Доступные профили:

1. `pr` — полный pre-merge набор (syntax, lint, render, artifacts, smoke, quality-gates).
1. `nightly` — `pr` + DIAG-T024..T029 (`run_diagram_nightly_suite.py`).
1. `quick` — облегчённый локальный цикл без рендера и тяжёлых chaos/growth/theme проверок.

Полезные флаги:

1. `--strict-nightly` — nightly падает не только на error, но и на warning.
1. `--skip-render` — пропускает render-шаг в `pr`/`nightly`.
1. `--puppeteer /tmp/puppeteer-config.json` — переопределение пути к Puppeteer config.
1. `--diagram docs/02-architecture/diagrams/foundation/30-port-adapter-mapping.mmd` — запуск проверок только для одной диаграммы.

Пример single-file запуска:

```bash
scripts/diagrams/run_diagram_checks.sh --profile pr \
  --diagram docs/02-architecture/diagrams/foundation/30-port-adapter-mapping.mmd
```

______________________________________________________________________

*Документ основан на ADR-040-diagram-governance.md, 00-diagramming-policy.md и исходном коде инструментов проекта.*
