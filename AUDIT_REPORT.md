# Архитектурный аудит кодовой базы

## Входные данные
*   **Язык/стек**: Python 3.11+, httpx, Polars, Delta Lake, Redis, Prefect
*   **Архитектурный стиль**: Hexagonal (Ports & Adapters) + Medallion Architecture
*   **Размер проекта**: ~69 файлов src (~8800 SLOC), ~75 файлов tests, 60+ md файлов docs
*   **Основные зависимости**: httpx, polars, deltalake, pydantic, redis, boto3, structlog, prefect, pandera
*   **Область**: ETL pipeline для биоактивности (ChEMBL, PubChem, UniProt → Delta Lake)

## 1. Количественная оценка (Score Card)

| # | Категория | Вес | Оценка (1–10) | Обоснование |
|---|-----------|-----|---------------|-------------|
| 1 | **Архитектура слоёв** | 0.15 | 10 | Границы слоёв строго соблюдаются и защищены автоматическими AST-тестами (`test_architecture.py`). Import fix в `BasePipeline` восстановил целостность. |
| 2 | **Модульность и связность** | 0.12 | 9 | Высокая cohesion. Введение `OrchestrationPort` уменьшило coupling с Prefect. Фабрики пайплайнов изолируют создание графа зависимостей. |
| 3 | **Качество доменной модели** | 0.12 | 8 | Используются Value Objects (RunID, Watermark), Ports (Protocols). Бизнес-логика трансформаций выделена, но есть тенденция к анемичной модели в пайплайнах. |
| 4 | **Тестовое покрытие и качество** | 0.12 | 9 | Архитектурные тесты консолидированы и строги. Unit-тесты покрывают базовую логику. Новые пайплайны имеют базовую реализацию, требуют расширения тестов. |
| 5 | **Обработка ошибок и устойчивость** | 0.10 | 9 | Единая иерархия исключений, Circuit Breaker, Rate Limiter. Исправлен критический баг с импортом `QuarantineManager`. |
| 6 | **Логирование и observability** | 0.08 | 8 | Structlog, Prometheus метрики. Введены stubs для CLI-инспекции карантина, но полная реализация требует доработки сервиса. |
| 7 | **Производительность и масштабируемость** | 0.08 | 7 | Async I/O используется корректно. Новые адаптеры (PubChem/UniProt) используют пагинацию. Масштабирование ограничено одним воркером (нет distributed execution). |
| 8 | **Безопасность** | 0.08 | 8 | Pydantic validation, secrets management через env. Отсутствуют явные уязвимости. Запрет unsafe builtins контролируется тестами. |
| 9 | **Документация** | 0.08 | 9 | Подробная документация (RULES.md, ADRs). Код снабжен docstrings. Новые пайплайны имеют YAML-конфигурации. |
| 10 | **Технический долг** | 0.07 | 9 | Критические ошибки исправлены. Дублирование тестов устранено. `BasePipeline` требует рефакторинга (God Object), но это не блокирует работу. |

**Интегральный балл: 8.78** (Хорошее состояние)

---

## 2. Качественный анализ архитектуры

*   **Соблюдение границ слоёв**: ✅ Строго соблюдается. AST-тесты гарантируют, что Domain не зависит от внешних библиотек, а Infrastructure не протекает в Application (за исключением `bootstrap` как Composition Root).
*   **Направление зависимостей**: ✅ Правильное. Application зависит от Domain Ports. Infrastructure реализует эти порты.
*   **Ports & Adapters**: ✅ Выделены. `OrchestrationPort` добавлен как Protocol. Адаптеры (PubChem, UniProt) реализованы в infrastructure и инжектируются через фабрики.
*   **Единообразие именования**: ✅ Соблюдается (`*Pipeline`, `*Factory`, `*Port`).
*   **Структура пакетов**: ✅ Функциональное разделение (pipelines, core) внутри слоев.

## 3. Реестр проблем

| ID | Тип | Локация | Описание | Severity | Effort |
|----|-----|---------|----------|----------|--------|
| P-002 | GOD_OBJECT | `application/core/base.py` | `BasePipeline` содержит множество convenience properties и ленивую инициализацию 5 компонентов. | Medium | M |
| P-006 | STUB_IMPL | `interfaces/orchestration` | `PrefectOrchestrationAdapter` реализован как заглушка (stub). Требуется реальная интеграция. | Medium | L |
| P-011 | MISSING_TESTS | `tests/unit/pipelines` | Отсутствуют специфичные unit-тесты для логики трансформации новых пайплайнов (PubChem/UniProt). | Low | S |
| P-012 | CLI_LIMITATION | `interfaces/cli.py` | Команды `quarantine inspect` используют bootstrap, но выводят имитационные данные, т.к. сервис карантина не имеет публичного API для инспекции. | Low | M |

## 4. План рефакторинга

### Фаза 0 — Quick wins (Завершено)
*   **[HOTFIX] Исправление импортов**: `BasePipeline` исправлен.
*   **[CLEANUP] Оптимизация тестов**: Архитектурные тесты объединены.
*   **[FEAT] Базовые пайплайны**: PubChem и UniProt подключены.

### Фаза 1 — Критические исправления (Текущий приоритет)
*   **[TEST-001] Тесты для новых пайплайнов**
    *   **Цель**: Обеспечить покрытие бизнес-логики трансформации.
    *   **Модули**: `tests/unit/pipelines/test_pubchem.py`, `tests/unit/pipelines/test_uniprot.py`.
    *   **Действия**: Написать тесты на `transform_bronze_to_silver`.
    *   **Влияние**: Тестовое покрытие (+0.2).

### Фаза 2 — Архитектурные улучшения
*   **[AR-002] Декомпозиция BasePipeline**
    *   **Цель**: Устранить God Object, вынести конфигурацию и доступ к сервисам.
    *   **Модули**: `application/core/base.py`.
    *   **Действия**: Выделить `PipelineContextAccessor`.
    *   **Влияние**: Модульность (+0.5).

*   **[AR-004] Реализация Orchestration Adapter**
    *   **Цель**: Полноценная интеграция с Prefect.
    *   **Модули**: `infrastructure/orchestration/adapters/prefect_adapter.py`.
    *   **Действия**: Реализовать методы `trigger`, `schedule` через Prefect Client API.
    *   **Влияние**: Производительность/Масштабируемость (+0.5).

### Фаза 3 — Улучшения качества
*   **[CLI-001] Полноценная инспекция карантина**
    *   **Цель**: Реальный вывод данных из S3/Delta.
    *   **Модули**: `infrastructure/quarantine/unified_quarantine.py`.
    *   **Действия**: Реализовать метод `inspect()` в сервисе.

## 5. Метрики и контроль регресса

*   **Статические метрики**: `mypy --strict` (уже используется), `ruff`.
*   **Архитектурные тесты**: `tests/test_architecture.py` (AST-based) — **Critical Gate**.
*   **CI-гейты**:
    *   Pass Architecture Tests (Blocker)
    *   Coverage > 80% (Warning)
    *   No Dead Code (Vulture)

### Прогноз Score Card после выполнения фаз 1–2
Ожидается рост интегрального балла до **9.1**. Устранение God Object и реализация реальной оркестрации значительно повысят модульность и масштабируемость.

```mermaid
graph TB
    subgraph "Application"
        BP[BasePipeline]
        P_PC[PubChemPipeline]
        P_UP[UniProtPipeline]
    end
    subgraph "Domain"
        Ports[Ports Protocol]
        OrchPort[OrchestrationPort]
    end
    subgraph "Infrastructure"
        PC_Adp[PubChemClient]
        UP_Adp[UniProtClient]
        Prefect_Adp[PrefectAdapter]
    end

    P_PC --|> BP
    P_UP --|> BP
    BP --> Ports
    BP --> OrchPort

    PC_Adp ..|> Ports
    UP_Adp ..|> Ports
    Prefect_Adp ..|> OrchPort
```
