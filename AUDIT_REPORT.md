# Архитектурный аудит кодовой базы BioETL

## Входные данные
*   **Язык/стек**: Python 3.11+, httpx, Polars, Delta Lake, Redis, Prefect
*   **Архитектурный стиль**: Hexagonal (Ports & Adapters) + Medallion Architecture
*   **Размер проекта**: ~69 файлов src (~8800 SLOC), ~75 файлов tests, 60+ md файлов docs
*   **Основные зависимости**: httpx, polars, deltalake, pydantic, redis, boto3, structlog, prefect, pandera
*   **Область**: ETL pipeline для биоактивности (ChEMBL, PubChem, UniProt → Delta Lake)

## 1. Количественная оценка (Score Card)

**Интегральный балл: 8.9 / 10** (Хорошее состояние)

| Категория | Вес | Оценка (1–10) | Обоснование |
| :--- | :---: | :---: | :--- |
| **Архитектура слоёв** | 1.0 | **10** | Строгое соблюдение Hexagonal Architecture. Границы слоёв контролируются AST-тестами (`test_architecture.py`). Чистый Domain слой. |
| **Модульность и связность** | 0.9 | **8** | Высокая связность внутри модулей. Зависимости инвертированы через Ports (`PipelineServices`). **Минус**: `DeltaWriter` содержит хардкод схемы, что повышает зацепление. |
| **Качество доменной модели** | 0.8 | **9** | Использование DDD (Value Objects, Entities). Порты определены как `Protocol`. Отсутствие I/O в домене. |
| **Тестовое покрытие и качество** | 0.9 | **9** | Строгие настройки `pytest`, наличие архитектурных тестов, мутационное тестирование (`mutmut`), высокие требования к покрытию (80%+). |
| **Обработка ошибок** | 0.8 | **9** | Типизированные исключения (`bioetl.domain.exceptions`), использование Circuit Breaker и Retry политик на уровне инфраструктуры. |
| **Логирование и наблюдаемость** | 0.7 | **9** | Структурированное логирование (`structlog`), метрики через `MetricsPort`. Отличная изоляция библиотек мониторинга. |
| **Производительность и масштабируемость** | 0.8 | **9** | Асинхронный I/O (`asyncio`), потоковая обработка (`zstd` streaming), использование Delta Lake и Polars. |
| **Безопасность** | 0.7 | **9** | `bandit` в CI, секреты через `pydantic-settings`, отсутствие хардкода. Безопасные практики (хэширование PII). |
| **Документация** | 0.6 | **9** | Docs-as-Code (`RULES.md` как источник правды), подробные docstrings, ADR. |
| **Технический долг** | 0.8 | **8** | Кодбаза чистая после рефакторинга. Основной долг — нарушение принципа единственной ответственности в `DeltaWriter`. |

---

## 2. Качественный анализ архитектуры

### Диаграмма текущего состояния

```mermaid
graph TD
    subgraph Interfaces ["Interfaces Layer"]
        CLI[CLI / Bootstrap]
    end

    subgraph Application ["Application Layer"]
        Pipe[Pipelines]
        PS[PipelineServices]
    end

    subgraph Domain ["Domain Layer"]
        Ports[Ports (Protocols)]
        Entities[Entities & VOs]
        Exceptions[Exceptions]
    end

    subgraph Infrastructure ["Infrastructure Layer"]
        subgraph Adapters
            Chembl[ChemblAdapter]
        end
        subgraph Storage
            BW[BronzeWriter]
            DW[DeltaWriter]
        end
        Config[Config & Settings]
    end

    %% Dependency Direction
    CLI --> |Injects Dependencies| Pipe
    Pipe --> |Uses| PS
    PS --> |Depends on| Ports

    Chembl -.-> |Implements| Ports
    BW -.-> |Implements| Ports
    DW -.-> |Implements| Ports

    Pipe --> |Manipulates| Entities
    Ports --> |Uses| Entities
    Ports --> |Raises| Exceptions

    Chembl --> |Uses| Config
```

### Анализ соблюдения принципов
*   **Соблюдение границ слоёв**: Реализовано образцово. `src/bioetl/domain` изолирован от внешнего мира. `src/bioetl/application` зависит только от абстракций.
*   **Направление зависимостей**: Строго внутрь (к Домену). Инфраструктура зависит от Домена (реализует порты), но Домен не знает об Инфраструктуре. Нарушения пресекаются `test_architecture.py`.
*   **Ports & Adapters**: Порты явно выделены (`bioetl.domain.ports`) как протоколы. Адаптеры (`ChemblAdapter`) реализуют их неявно (Duck Typing), что идиоматично для Python.
*   **Единообразие именования**: Классы и модули именуются консистентно (`*Adapter`, `*Writer`, `*Port`).
*   **Структура пакетов**: Соответствует техническому разделению (hexagonal), внутри — функциональное деление.

---

## 3. Реестр проблем

| ID | Тип | Локация | Описание | Severity | Effort |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **P-001** | `LEAKY_ABSTRACTION` | `infra/storage/delta_writer.py` | Метод `write_silver` содержит явное определение схемы Arrow для ChEMBL (`molecule_chembl_id` и т.д.). Инфраструктурный класс знает о деталях конкретного домена, что делает его непригодным для других сущностей. | **High** | **M** |
| **P-002** | `DUPLICATION` | `infra/adapters/chembl/client.py` | Реализована собственная логика пагинации. В проекте существует практика использования `PaginatedFetcherMixin` (согласно `AGENTS.md`), здесь же она не применена. | **Low** | **S** |
| **P-003** | `CONFIG_LEAK` | `infra/storage/bronze_writer.py` | Логика формирования путей (`bronze/v1/...`) зашита в код писателя. Это нарушает принцип разделения ответственности: писатель должен писать байты, а не определять структуру каталогов. | **Medium** | **S** |

---

## 4. План рефакторинга

### Фаза 0 — Quick wins
#### [R-01] Decouple DeltaWriter Schema
- **Цель**: Сделать `DeltaWriter` агностичным к бизнес-сущностям.
- **Затрагиваемые модули**: `src/bioetl/infrastructure/storage/delta_writer.py`, фабрики пайплайнов.
- **Действия**:
  1. Изменить сигнатуру `write_silver`, чтобы схема передавалась как аргумент (или `contract`).
  2. Вынести определение схемы пайплайна ChEMBL в конфигурацию или Application слой (как Data Contract).
- **Риски**: `SchemaViolationError` если передаваемая схема не совпадет с данными.
- **DoD**: В `delta_writer.py` нет упоминаний полей ChEMBL; тесты проходят с моковой схемой.
- **Влияние на Score Card**: Модульность +1.

### Фаза 1 — Архитектурные улучшения
#### [R-02] Unify Pagination Logic
- **Цель**: Устранить дублирование кода пагинации.
- **Затрагиваемые модули**: `src/bioetl/infrastructure/adapters/chembl/client.py`.
- **Действия**:
  1. Проверить существование `PaginatedFetcherMixin` в `infra/adapters/http/`.
  2. Рефакторить `ChemblAdapter` для использования миксина.
- **Риски**: Поломка специфичной обработки курсоров ChEMBL.
- **DoD**: Адаптер использует стандартный миксин.

#### [R-03] Implement Storage Path Strategy
- **Цель**: Вынести логику путей S3 в отдельную стратегию.
- **Затрагиваемые модули**: `BronzeWriter`.
- **Действия**:
  1. Выделить интерфейс `PathStrategy`.
  2. Реализовать дефолтную стратегию (текущая логика).
  3. Инжектировать стратегию в `BronzeWriter`.
- **DoD**: `BronzeWriter` не содержит строковых литералов путей.

---

## 5. Метрики и контроль регресса

Для поддержания достигнутого уровня качества (8.9) предлагается:

1.  **Расширенные Архитектурные Тесты**:
    *   Добавить правило в `test_architecture.py`: запретить инстанцирование `pa.schema` с конкретными полями внутри пакета `infrastructure.storage` (разрешить только передачу извне).
    *   Проверять, что классы в `adapters` не имеют методов `fetch` без использования общих абстракций пагинации (где применимо).

2.  **Статические метрики (CI Gates)**:
    *   **Import Linter**: Строго запретить импорт `bioetl.application` в `bioetl.infrastructure` (уже есть, но усилить проверкой транзитивных зависимостей).
    *   **Cyclomatic Complexity**: Удерживать < 10 для методов Writer'ов.

3.  **Тестовое покрытие**:
    *   Удерживать покрытие Domain слоя на уровне 100%.
    *   Infrastructure: не менее 85% (с учетом интеграционных тестов на `fakeredis`/`moto`).

**Прогноз**: Выполнение Фазы 0 и 1 повысит интегральный балл до **9.2** за счет улучшения модульности и устранения утечек абстракций.
