______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Слой Interfaces (Интерфейсы)

**Расположение:** `src/bioetl/interfaces/`

## 1. Назначение

Слой `Interfaces` — это точка входа в приложение. Он отвечает за приём команд от пользователя (или других систем) и запуск соответствующей бизнес-логики.

Этот слой использует **Composition Root** (слой `Composition`) для сборки зависимостей и получения готовых к работе объектов.

**Ключевые характеристики:**

- **Точка входа:** Содержит driving adapters, которые запускаются напрямую или принимают внешние сигналы (CLI, HTTP health probes, retained orchestration seams).
- **Адаптация ввода/вывода:** Преобразует внешние запросы (например, аргументы командной строки) в вызовы методов слоя `Application`.
- **Минимальная логика:** Не содержит логики сборки или бизнес-логики.

## 2. Ключевые Компоненты

### 2.1. `cli/` — Интерфейс Командной Строки

**Расположение:** `src/bioetl/interfaces/cli/`

Реализует CLI для взаимодействия с пользователем. Использует библиотеку **Click** для определения команд.

**Доступные top-level команды и support/compat модули в `commands/` (снимок синхронизирован на 2026-05-07):**

| Команда         | Модуль             | Описание                                                                            |
| --------------- | ------------------ | ----------------------------------------------------------------------------------- |
| `run`           | `run.py`           | Public CLI seam; canonical implementation lives in `domains/run/command.py`         |
| `run-all`       | `run_all.py`       | Public CLI seam; canonical implementation lives in `domains/run_all/command.py`     |
| `run-composite` | `run_composite.py` | Public CLI seam; canonical implementation lives in `domains/composite/command.py`   |
| `run-manifest`  | `run_manifest.py`  | Inspect immutable manifest payloads and append-only ledger history                  |
| `export`        | `export.py`        | Экспорт данных из Gold                                                              |
| `quarantine`    | `quarantine.py`    | Public CLI seam; canonical implementation lives in `domains/quarantine/command.py`  |
| `health`        | `health.py`        | Public CLI seam; canonical implementation lives in `domains/health/command.py`      |
| `config`        | `config.py`        | Просмотр и валидация конфигураций                                                   |
| `checkpoint`    | `checkpoint.py`    | Управление checkpoint-ами                                                           |
| `dq`            | `config_dq.py`     | Команды конфигурации data quality                                                   |
| `diagnostics`   | `diagnostics.py`   | Unified operator diagnostics across metrics, health, checkpoints, manifests, and quarantine |
| `lineage`       | `lineage.py`       | Inspect pipeline lineage                                                            |
| `lock`          | `lock.py`          | Управление блокировками                                                             |
| `maintenance`   | `maintenance.py`   | Public CLI seam; canonical implementation lives in `domains/maintenance/command.py` |
| `adr`           | `adr.py`           | Управление ADR (Architecture Decisions)                                             |
| `debug`         | `debug.py`         | Диагностические утилиты                                                             |

**Вспомогательные реализации:**

Support-only helpers are not published as top-level command seams. Import
`domains/health/*` and `domains/quarantine/*` owner modules directly from inside
the CLI package tests and command implementations.

**Примеры использования:**

```bash
# Запуск пайплайна с лимитом
python -m bioetl run --pipeline chembl_activity --limit 100

# Запуск композитного пайплайна (ADR-026)
python -m bioetl run-composite --composite publication

# Проверка здоровья провайдеров
python -m bioetl health --provider chembl
```

`interfaces/cli/main.py` регистрирует `run`, `run-all`, `run-composite`,
`run-manifest` и остальные command groups. Для запуска исполнения он делегирует
в composition runtime bootstrap (`bootstrap_pipeline_runner`,
`bootstrap_composite_runner`), а для inspection-only control-plane операций
использует `get_run_manifest_service()` через composition service API.

### 2.2. `http/` — HTTP Health Server

**Расположение:** `src/bioetl/interfaces/http/`

Содержит HTTP health server с entrypoint `health_server.py` и mixin-based decomposition:
`health_server_http_mixin.py`, `health_server_routing_mixin.py`,
`health_server_state_mixin.py`, `types.py`.
Endpoints: `/health`, `/health/live`, `/health/ready`.

### 2.3. `orchestration/` — Оркестрация (Driving Adapters)

**Расположение:** `src/bioetl/interfaces/orchestration/`

`orchestration/` сейчас является минимальным retained package seam без активных
signal-handler implementations. Signal handlers были удалены 2025-12-31.
Graceful shutdown обрабатывается непосредственно в canonical domain command modules:

- `interfaces/cli/commands/domains/run/command.py`
- `interfaces/cli/commands/domains/run_all/command.py`
- `interfaces/cli/commands/domains/composite/command.py`
  Shutdown логика вынесена в `application/core/lifecycle/shutdown.py`.

______________________________________________________________________

Для подробной информации о том, как собираются компоненты системы, см. [Слой Composition](05-composition-layer.md).

## 3. Принципы Работы

- **Максимальная простота:** Этот слой должен быть как можно более "глупым". Его задача — делегировать работу другим слоям, а не выполнять её самому.
- **Единственная ответственность:** Единственная ответственность этого слоя — запуск приложения и управление его жизненным циклом на самом верхнем уровне.
- **Без прямого Infrastructure coupling:** `interfaces` может импортировать `domain`, `application` и `composition`, но не должен напрямую импортировать `infrastructure`; конкретные adapters и storage implementations подключаются только через Composition layer.

______________________________________________________________________

## 4. Связанные Материалы

### Навигация по Слоям

| ← Предыдущий                                       | Текущий        | Следующий →                                  |
| -------------------------------------------------- | -------------- | -------------------------------------------- |
| [Infrastructure Layer](03-infrastructure-layer.md) | **Interfaces** | [Composition Layer](05-composition-layer.md) |

### Связанные Диаграммы

| Диаграмма               | Файл                                                                                         | Описание                              |
| ----------------------- | -------------------------------------------------------------------------------------------- | ------------------------------------- |
| Five Layer Architecture | [01-high-level.mermaid](diagrams/foundation/01-high-level.mmd)                               | Полная архитектура с Interfaces слоем |
| Layers Interaction      | [05-layers-interaction.mermaid](diagrams/foundation/05-layers-interaction.mmd)               | Взаимодействие слоёв                  |
| Graceful Shutdown       | [05-pipeline-lifecycle-states.mermaid](diagrams/foundation/05-pipeline-lifecycle-states.mmd) | Sequence diagram graceful shutdown    |

### Связанные ADR

| ADR                                                               | Тема                                |
| ----------------------------------------------------------------- | ----------------------------------- |
| [ADR-008](decisions/ADR-008-graceful-shutdown-strategy.md)        | Graceful Shutdown Strategy          |
| [ADR-026](decisions/ADR-026-composite-pipeline-pattern.md)        | Composite Pipeline — расширения CLI |
| [ADR-044](decisions/ADR-044-run-manifest-ledger-control-plane.md) | Control-plane inspection CLI        |

### Смежные Разделы Документации

- [Composition Layer](05-composition-layer.md) — runtime bootstrap (`bootstrap_pipeline_runner`, `bootstrap_composite_runner`), фабрики
- [CLI Reference](../04-reference/cli.md) — полная документация CLI команд
- [ADR-005](decisions/ADR-005-composition-layer-separation.md) — активная матрица импортов; `interfaces` использует `composition` и не импортирует `infrastructure` напрямую
- [RULES.md §1 "Архитектура и Слои"](../00-project/RULES.md) — high-level layering rules и ссылки на активные ADR
