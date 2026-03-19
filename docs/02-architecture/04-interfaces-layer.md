# Слой Interfaces (Интерфейсы)

**Расположение:** `src/bioetl/interfaces/`

## 1. Назначение

Слой `Interfaces` — это точка входа в приложение. Он отвечает за приём команд от пользователя (или других систем) и запуск соответствующей бизнес-логики.

Этот слой использует **Composition Root** (слой `Composition`) для сборки зависимостей и получения готовых к работе объектов.

**Ключевые характеристики:**

- **Точка входа:** Содержит код, который запускается напрямую (например, CLI-команды).
- **Адаптация ввода/вывода:** Преобразует внешние запросы (например, аргументы командной строки) в вызовы методов слоя `Application`.
- **Минимальная логика:** Не содержит логики сборки или бизнес-логики.

## 2. Ключевые Компоненты

### 2.1. `cli/` — Интерфейс Командной Строки

**Расположение:** `src/bioetl/interfaces/cli/`

Реализует CLI для взаимодействия с пользователем. Использует библиотеку **Click** для определения команд.

**Доступные команды (32 модуля в `commands/`, актуально на 2026-03-17):**

| Команда         | Модуль                       | Описание                                |
| --------------- | ---------------------------- | --------------------------------------- |
| `run`           | `run.py`                     | Запуск одного пайплайна                 |
| `run-all`       | `run_all.py`                 | Запуск всех пайплайнов провайдера       |
| `run-composite` | `run_composite.py`           | Запуск композитного пайплайна (ADR-026) |
| `export`        | `export.py`                  | Экспорт данных из Gold                  |
| `quarantine`    | `quarantine.py`              | Управление карантинными записями        |
| `health`        | `health.py`                  | Проверка здоровья провайдеров           |
| `config`        | `config.py`                  | Просмотр и валидация конфигураций       |
| `checkpoint`    | `checkpoint.py`              | Управление checkpoint-ами               |
| `lock`          | `lock.py`                    | Управление блокировками                 |
| `vacuum`        | `vacuum.py`                  | VACUUM операции для Delta Lake          |
| `cleanup`       | `cleanup.py`                 | Очистка Bronze данных                   |
| `maintenance`   | `maintenance.py`             | Maintenance операции                    |
| `archive`       | `archive.py`                 | Архивирование данных                    |
| `adr`           | `adr.py`                     | Управление ADR (Architecture Decisions) |
| `debug`         | `debug.py`                   | Диагностические утилиты                 |

**Вспомогательные модули в `commands/`:**

| Модуль                          | Назначение                              |
| ------------------------------- | --------------------------------------- |
| `execution_policy.py`           | Политики исполнения команд              |
| `run_helpers.py`                | Вспомогательные функции для run-команд  |
| `run_all_helpers.py`            | Вспомогательные функции для run-all     |
| `run_command_policy.py`         | Политики run-команд                     |
| `run_composite_runtime.py`      | Runtime для composite                   |
| `run_result_presenter.py`       | Форматирование результатов запуска      |
| `health_server_integration.py`  | Интеграция health-сервера               |
| `metrics_server_integration.py` | Интеграция metrics-сервера              |

**Примеры использования:**

```bash
# Запуск пайплайна с лимитом
python -m bioetl run --pipeline chembl_activity --limit 100

# Запуск композитного пайплайна (ADR-026)
python -m bioetl run-composite --composite publication

# Проверка здоровья провайдеров
python -m bioetl health --provider chembl
```

`interfaces/cli/main.py` парсит аргументы и вызывает composition runtime bootstrap (`bootstrap_pipeline_runner`, `bootstrap_composite_runner`) для запуска исполнения. Каноническая точка входа CLI — `src/bioetl/interfaces/cli/main.py`.

### 2.2. `http/` — HTTP Health Server

**Расположение:** `src/bioetl/interfaces/http/`

Содержит HTTP health endpoint (`health_server.py`) с интеграцией Prometheus metrics.
Endpoints: `/health`, `/health/live`, `/health/ready`.

### 2.3. `orchestration/` — Оркестрация (Driving Adapters)

**Расположение:** `src/bioetl/interfaces/orchestration/`

`orchestration/` — модуль пуст. Signal handlers были удалены 2025-12-31.
Graceful shutdown обрабатывается непосредственно в CLI командах:

- `interfaces/cli/commands/run.py`
- `interfaces/cli/commands/run_all.py`
- `interfaces/cli/commands/run_composite.py`
  Shutdown логика вынесена в `application/core/lifecycle/shutdown.py`.

----------------------------------------------------------------------

Для подробной информации о том, как собираются компоненты системы, см. [Слой Composition](05-composition-layer.md).

## 3. Принципы Работы

- **Максимальная простота:** Этот слой должен быть как можно более "глупым". Его задача — делегировать работу другим слоям, а не выполнять её самому.
- **Единственная ответственность:** Единственная ответственность этого слоя — запуск приложения и управление его жизненным циклом на самом верхнем уровне.
- **Импорт из всех слоёв:** Это единственный слой, которому разрешено импортировать модули из `domain`, `application` и `infrastructure` для того, чтобы "собрать" приложение воедино.

----------------------------------------------------------------------

## 4. Связанные Материалы

### Навигация по Слоям

| ← Предыдущий                                       | Текущий        | Следующий →                                  |
| -------------------------------------------------- | -------------- | -------------------------------------------- |
| [Infrastructure Layer](03-infrastructure-layer.md) | **Interfaces** | [Composition Layer](05-composition-layer.md) |

### Связанные Диаграммы

| Диаграмма               | Файл                                                                                               | Описание                              |
| ----------------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------- |
| Five Layer Architecture | [01-high-level.mermaid](diagrams/foundation/01-high-level.mmd)                                   | Полная архитектура с Interfaces слоем |
| Layers Interaction      | [05-layers-interaction.mermaid](diagrams/foundation/05-layers-interaction.mmd)                    | Взаимодействие слоёв                  |
| Graceful Shutdown       | [05-pipeline-lifecycle-states.mermaid](diagrams/foundation/05-pipeline-lifecycle-states.mmd)      | Sequence diagram graceful shutdown    |

### Связанные ADR

| ADR                                                        | Тема                                |
| ---------------------------------------------------------- | ----------------------------------- |
| [ADR-008](decisions/ADR-008-graceful-shutdown-strategy.md) | Graceful Shutdown Strategy          |
| [ADR-026](decisions/ADR-026-composite-pipeline-pattern.md) | Composite Pipeline — расширения CLI |

### Смежные Разделы Документации

- [Composition Layer](05-composition-layer.md) — runtime bootstrap (`bootstrap_pipeline_runner`, `bootstrap_composite_runner`), фабрики
- [CLI Reference](../04-reference/cli.md) — полная документация CLI команд
- [RULES.md §1 "Архитектура и Слои"](../00-project/RULES.md) — матрица импортов (interfaces может импортировать всё)
