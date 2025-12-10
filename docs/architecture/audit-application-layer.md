# Аудит Application Layer — BioETL

> **Дата аудита:** 2025-12-10
> **Версия:** f1d2eab

## 1. Краткий обзор архитектуры слоя application

### 1.1 Структура

```
src/bioetl/application/
├── container.py              # DI-контейнер (313 строк)
├── orchestrator.py           # Оркестратор пайплайнов (305 строк)
├── config/
│   ├── resolution.py         # Резолвер путей конфигов
│   └── runtime.py            # Runtime-конфиг фасад
├── factories/
│   ├── services.py           # ProviderServiceFactory
│   ├── record_source.py      # RecordSourceFactory
│   └── hooks.py              # PipelineHookFactory
├── files/
│   └── csv_record_source.py  # CSV record source реализации
├── pipelines/
│   ├── base.py               # PipelineBase (642 строки)
│   ├── contracts.py          # PipelineContainerABC
│   ├── registry.py           # Реестр пайплайнов
│   ├── stage_runtime_manager.py  # Менеджер стадий (369 строк)
│   ├── hooks_impl.py         # Реализации хуков и политик
│   └── chembl/               # ChEMBL-специфичные компоненты
│       ├── base.py           # ChemblPipelineBase
│       ├── extractor.py      # ChemblExtractorImpl
│       ├── transformer.py    # ChemblTransformerImpl
│       ├── factories.py      # create_chembl_pipeline()
│       ├── stage_metadata.py # Метаданные стадий
│       └── {activity|assay|target|molecule|publication}/  # [!] 25 файлов-заглушек
├── providers/
│   └── defaults.py           # ApplicationFieldProvider
└── transform/
    └── pandas_batch_adapter.py  # PandasBatchAdapter
```

### 1.2 Основные типы компонентов

| Компонент | Роль |
|-----------|------|
| `PipelineContainer` | DI-контейнер, собирает зависимости |
| `PipelineOrchestrator` | Фасад для сборки и запуска пайплайнов |
| `PipelineBase` | Template Method для ETL-стадий |
| `ChemblPipelineBase` | Конкретная реализация для ChEMBL |
| `StageRuntimeManagerImpl` | Управление хуками, политиками, состоянием |
| Factories | Создание сервисов, record sources, хуков |

### 1.3 Взаимодействие с domain и infrastructure

```
interfaces (CLI, container_factory)
         ↓
    application (orchestrator, container, pipelines)
         ↓
       domain (contracts, schemas, configs)
         ↓
   infrastructure (clients, loaders, hash services)
```

**Положительно:** Application не имеет прямых импортов из infrastructure/interfaces.

---

## 2. Список проблем по категориям

### 2.1 Дублирование

| # | Проблема | Местоположение | Влияние |
|---|----------|----------------|---------|
| **D1** | **25 файлов-заглушек стадий** — идентичная структура, отличаются только константы | `pipelines/chembl/{activity,assay,target,molecule,publication}/{extract,transform,validate,export}.py` | Шум, ложная сложность |
| **D2** | `_create_noop_metrics_port()` дублируется | `container.py:283`, `hooks_impl.py:133` | Нарушение DRY |
| **D3** | `_resolve_primary_key()` дублируется 3 раза | `chembl/base.py`, `chembl/extractor.py`, `factories/record_source.py` | Расхождение логики, баги |
| **D4** | `_create_default_metadata_builder()` дублируется | `pipelines/base.py:35`, `chembl/base.py` (через импорт) | Неконсистентность |
| **D5** | `_ensure_csv_options()` в `CsvRecordSourceImpl` и `IdListRecordSourceImpl` | `csv_record_source.py:64,172` | Нарушение DRY |

### 2.2 Неиспользуемые/избыточные абстракции

| # | Проблема | Местоположение | Влияние |
|---|----------|----------------|---------|
| **U1** | **25 модулей стадий** — экспортируют `get_stage_descriptor`, который **нигде не импортируется** | `pipelines/chembl/{entity}/*.py` | Мёртвый код |
| **U2** | `stage_metadata.py` — используется только заглушками | `pipelines/chembl/stage_metadata.py` | Бесполезная абстракция |
| **U3** | Реэкспорт `ExtractorABC`, `LoaderABC` в application contracts | `pipelines/contracts.py:11-12,88` | Лишний уровень indirection |
| **U4** | `ContinueOnErrorPolicyImpl` — используется только в тестах | `hooks_impl.py:66-81` | Потенциально мёртвый код |
| **U5** | Пустые `__init__.py` без экспортов | `application/__init__.py`, `pipelines/__init__.py` | Шум |

### 2.3 Нарушения DDD и слоения

| # | Проблема | Местоположение | Влияние |
|---|----------|----------------|---------|
| **L1** | `ChemblExtractorImpl._resolve_record_source()` **дублирует** логику `RecordSourceFactory` | `chembl/extractor.py:82-108` vs `factories/record_source.py:34-89` | Две точки изменения |
| **L2** | `PipelineOrchestrator.build_pipeline()` пересекается с `create_chembl_pipeline()` | `orchestrator.py:50-97` vs `chembl/factories.py:9-31` | Размытие ответственности |
| **L3** | `PipelineBase` смешивает оркестрацию и бизнес-логику | `base.py:125-223` (метод `run()`) | God Method (~100 строк) |
| **L4** | `PipelineContainer` содержит 3 внутренних фабрики с lazy initialization | `container.py:76-104` | Скрытые зависимости |

### 2.4 Перегруженные/размытые по ответственности компоненты

| # | Проблема | Метрика | Влияние |
|---|----------|---------|---------|
| **C1** | `PipelineBase` — Template Method + runtime management + context building | 642 строки, 30+ методов | Трудно тестировать и расширять |
| **C2** | `StageRuntimeManagerImpl` — хуки + ошибки + счётчики + chunk processing | 369 строк | Перегружен ответственностями |
| **C3** | `PipelineOrchestrator` — сборка + запуск + background execution + сериализация реестра | 305 строк | Размытый фокус |
| **C4** | `ChemblPipelineBase.__init__` принимает 12 параметров | 12 параметров | Сложная сигнатура |

---

## 3. Конкретные рекомендации по упрощению

### 3.1 Удаление мёртвого кода

| Действие | Что удалить | Ожидаемый эффект |
|----------|-------------|------------------|
| **R1** | Удалить 25 файлов в `pipelines/chembl/{entity}/*.py` и 5 `__init__.py` | **-30 файлов**, -650 строк кода |
| **R2** | Удалить `stage_metadata.py` | **-1 файл**, -47 строк |
| **R3** | Рассмотреть удаление `ContinueOnErrorPolicyImpl` или перенос в tests/fixtures | -15 строк продакшн-кода |

### 3.2 Устранение дублирования

| Действие | Что сделать | Ожидаемый эффект |
|----------|-------------|------------------|
| **R4** | Вынести `_create_noop_metrics_port()` в shared utilities или domain | 1 источник истины |
| **R5** | Вынести `_resolve_primary_key()` в отдельный `PrimaryKeyResolver` helper | Устранение 3 дублей |
| **R6** | Удалить `_create_default_metadata_builder()` из `chembl/base.py` (использовать импорт из `base.py`) | Консистентность |
| **R7** | Вынести `_ensure_csv_options()` в отдельную функцию | Устранение дубля |

### 3.3 Упрощение архитектуры

| Действие | Что сделать | Ожидаемый эффект |
|----------|-------------|------------------|
| **R8** | Удалить `ChemblExtractorImpl._resolve_record_source()`, использовать inject из контейнера | Единая точка создания RecordSource |
| **R9** | Удалить `create_chembl_pipeline()` или интегрировать в `PipelineOrchestrator` | Устранение параллельных путей |
| **R10** | Извлечь `_process_extract_stage()` из `PipelineBase` в отдельный `StageProcessor` | Уменьшение PipelineBase |
| **R11** | Разделить `StageRuntimeManagerImpl` на `HookNotifier` + `StageCounter` + `ErrorHandler` | SRP-compliant компоненты |

### 3.4 Оптимизация contracts

| Действие | Что сделать | Ожидаемый эффект |
|----------|-------------|------------------|
| **R12** | Убрать реэкспорт `ExtractorABC`, `LoaderABC` из `application/pipelines/contracts.py`; импортировать напрямую из domain | Явные зависимости |

---

## 4. Список задач/тикетов для рефакторинга

### Высокий приоритет

| ID | Задача | Обоснование |
|----|--------|-------------|
| **TASK-001** | Удалить 30 файлов-заглушек в `pipelines/chembl/{entity}/` и `stage_metadata.py` | Мёртвый код, -700 строк, снижение cognitive load |
| **TASK-002** | Консолидировать `_resolve_primary_key()` в единый helper | 3 дубля → 1 источник истины, предотвращение рассинхронизации |
| **TASK-003** | Удалить дублирование `_create_noop_metrics_port()` | Технический долг, простое исправление |

### Средний приоритет

| ID | Задача | Обоснование |
|----|--------|-------------|
| **TASK-004** | Удалить `ChemblExtractorImpl._resolve_record_source()`, получать RecordSource из контейнера | Устранение дублирования с `RecordSourceFactory` |
| **TASK-005** | Выделить chunk processing из `StageRuntimeManagerImpl` | Упрощение тестирования, SRP |
| **TASK-006** | Рефакторинг `PipelineBase.run()` — извлечь логику стадий в отдельные методы/классы | God Method → композиция |
| **TASK-007** | Унифицировать `PipelineOrchestrator.build_pipeline()` и `create_chembl_pipeline()` | Одна точка входа для создания пайплайнов |

### Низкий приоритет

| ID | Задача | Обоснование |
|----|--------|-------------|
| **TASK-008** | Убрать реэкспорт domain contracts в `application/pipelines/contracts.py` | Чистота импортов |
| **TASK-009** | Рассмотреть перенос `ContinueOnErrorPolicyImpl` в test fixtures | Код используется только в тестах |
| **TASK-010** | Добавить экспорты в пустые `__init__.py` или удалить | Консистентность |

---

## 5. Допущения

1. **Слои идентифицированы** по директориям: `application/`, `domain/`, `infrastructure/`, `interfaces/`
2. **Entity-модули** (`activity/`, `assay/` и т.д.) рассматриваются как часть application layer
3. **pandas** в domain считается допустимым для ETL-системы (infrastructure leakage, но прагматичное решение)

---

## 6. Резюме метрик

| Метрика | Значение |
|---------|----------|
| Файлов в application layer | **52** |
| Мёртвых файлов (заглушки) | **30** (58%) |
| Дублирующихся функций | **5** |
| Классов >300 строк | **3** |
| Параметров в конструкторе (max) | **12** |
| Потенциальное сокращение кода | **~700 строк** |

---

## 7. Визуализация проблем

### 7.1 Структура entity-модулей (мёртвый код)

```
pipelines/chembl/
├── activity/
│   ├── __init__.py      # [DEAD] реэкспорт get_stage_descriptor
│   ├── extract.py       # [DEAD] заглушка
│   ├── transform.py     # [DEAD] заглушка
│   ├── validate.py      # [DEAD] заглушка
│   └── export.py        # [DEAD] заглушка
├── assay/               # [DEAD] аналогично
├── target/              # [DEAD] аналогично
├── molecule/            # [DEAD] аналогично
└── publication/         # [DEAD] аналогично
```

### 7.2 Дублирование `_resolve_primary_key()`

```
┌─────────────────────────────┐
│ chembl/base.py:109-130     │ ← копия #1
└─────────────────────────────┘
         ▼
┌─────────────────────────────┐
│ chembl/extractor.py:110-121│ ← копия #2
└─────────────────────────────┘
         ▼
┌─────────────────────────────┐
│ factories/record_source.py │ ← копия #3
│         :91-101            │
└─────────────────────────────┘
```

### 7.3 Пересечение ответственностей

```
PipelineOrchestrator.build_pipeline()
              │
              ├── извлекает сервисы из контейнера
              ├── создаёт pipeline instance
              └── передаёт те же сервисы
                        │
                        ▼
ChemblPipelineBase.__init__()
              │
              ├── создаёт ChemblExtractorImpl
              │       │
              │       └── ChemblExtractorImpl._resolve_record_source()
              │                    ▲
              │                    │ ДУБЛИРУЕТ
              │                    ▼
              │         RecordSourceFactory.create_record_source()
              │
              └── создаёт ChemblTransformerImpl

        ┌────────────────────────────────┐
        │ create_chembl_pipeline()       │ ← АЛЬТЕРНАТИВНЫЙ путь
        │ (chembl/factories.py)          │   (делает то же самое)
        └────────────────────────────────┘
```
