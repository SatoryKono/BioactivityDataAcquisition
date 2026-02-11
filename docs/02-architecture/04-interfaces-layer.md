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

**Доступные команды (17 модулей в `commands/`):**

| Команда         | Модуль             | Описание                                |
| --------------- | ------------------ | --------------------------------------- |
| `run`           | `run.py`           | Запуск одного пайплайна                 |
| `run-all`       | `run_all.py`       | Запуск всех пайплайнов провайдера       |
| `run-composite` | `run_composite.py` | Запуск композитного пайплайна (ADR-026) |
| `export`        | `export.py`        | Экспорт данных из Gold                  |
| `quarantine`    | `quarantine.py`    | Управление карантинными записями        |
| `health`        | `health.py`        | Проверка здоровья провайдеров           |
| `config`        | `config.py`        | Просмотр и валидация конфигураций       |
| `checkpoint`    | `checkpoint.py`    | Управление checkpoint-ами               |
| `lock`          | `lock.py`          | Управление блокировками                 |
| `vacuum`        | `vacuum.py`        | VACUUM операции для Delta Lake          |
| `cleanup`       | `cleanup.py`       | Очистка Bronze данных                   |
| `maintenance`   | `maintenance.py`   | Maintenance операции                    |
| `archive`       | `archive.py`       | Архивирование данных                    |

**Примеры использования:**

```bash
# Запуск пайплайна с лимитом
python -m bioetl run --pipeline chembl_activity --limit 100

# Запуск композитного пайплайна (ADR-026)
python -m bioetl run --pipeline composite_publication

# Проверка здоровья провайдеров
python -m bioetl health --provider chembl
```

`cli.py` парсит эти аргументы, вызывает функции из `src/bioetl/composition/bootstrap.py` для инициализации системы и запускает выполнение пайплайна.

### 2.2. `http/` — HTTP Health Server

**Расположение:** `src/bioetl/interfaces/http/`

Содержит HTTP health endpoint (`health_server.py`) с интеграцией Prometheus metrics.
Endpoints: `/health`, `/health/live`, `/health/ready`.

### 2.3. `orchestration/` — Оркестрация

**Расположение:** `src/bioetl/interfaces/orchestration/`

orchestration/ — модуль пуст. Signal handlers были удалены 2025-12-31.
Graceful shutdown обрабатывается непосредственно в CLI командах:

- `interfaces/cli/commands/run.py`
- `interfaces/cli/commands/run_all.py`
- `interfaces/cli/commands/run_composite.py`

Shutdown логика вынесена в `application/core/shutdown.py`.

______________________________________________________________________

Для подробной информации о том, как собираются компоненты системы, см. [Слой Composition](05-composition-layer.md).

## 3. Принципы Работы

- **Максимальная простота:** Этот слой должен быть как можно более "глупым". Его задача — делегировать работу другим слоям, а не выполнять её самому.
- **Единственная ответственность:** Единственная ответственность этого слоя — запуск приложения и управление его жизненным циклом на самом верхнем уровне.
- **Импорт из всех слоёв:** Это единственный слой, которому разрешено импортировать модули из `domain`, `application` и `infrastructure` для того, чтобы "собрать" приложение воедино.

______________________________________________________________________

## 4. Связанные Материалы

### Навигация по Слоям

| ← Предыдущий                                       | Текущий        | Следующий →                                  |
| -------------------------------------------------- | -------------- | -------------------------------------------- |
| [Infrastructure Layer](03-infrastructure-layer.md) | **Interfaces** | [Composition Layer](05-composition-layer.md) |

### Связанные Диаграммы

| Диаграмма               | Файл                                                                                               | Описание                              |
| ----------------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------- |
| Five Layer Architecture | [diagrams/mermaid/01_five_layer_architecture.mmd](diagrams/mermaid/01_five_layer_architecture.mmd) | Полная архитектура с Interfaces слоем |
| Layers Interaction      | [05-layers-interaction.mermaid](diagrams/05-layers-interaction.mermaid)                            | Взаимодействие слоёв                  |
| Graceful Shutdown       | [diagrams/mermaid/24_graceful_shutdown.mmd](diagrams/mermaid/24_graceful_shutdown.mmd)             | Sequence diagram graceful shutdown    |

### Связанные ADR

| ADR                                                        | Тема                                |
| ---------------------------------------------------------- | ----------------------------------- |
| [ADR-008](decisions/ADR-008-graceful-shutdown-strategy.md) | Graceful Shutdown Strategy          |
| [ADR-026](decisions/ADR-026-composite-pipeline-pattern.md) | Composite Pipeline — расширения CLI |

### Смежные Разделы Документации

- [Composition Layer](05-composition-layer.md) — bootstrap_pipeline, фабрики

- [CLI Reference](../04-reference/cli.md) — полная документация CLI команд

- [RULES.md §1 "Архитектура и Слои"](../RULES.md) — матрица импортов (interfaces может импортировать всё)

- health_server_integration

- metrics_server_integration

- run_helpers
