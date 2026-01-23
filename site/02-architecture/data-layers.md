# Архитектура Данных и Слои (Data Layers)

В этом документе детально описывается реализация слоев данных (Bronze, Silver, Gold), их форматы, схемы, процессы нормализации и валидации.

Документ является дополнением к [RULES.md](../RULES.md) и предоставляет техническую детализацию для разработчиков.

## 1. Bronze Layer (Сырые данные)

Слой Bronze предназначен для хранения сырых данных в исходном формате, полученных от внешних провайдеров. Является неизменяемым (Append-only) источником истины для всех последующих пересчетов.

### 1.1. Формат и Хранение
*   **Формат**: `JSONL` (JSON Lines), сжатый кодеком `zstd`.
*   **Путь**: `bronze/v1/{provider}/{entity}/{date}/`.
    *   `v1` — версия формата хранения (версия бакета/пути).
    *   `{date}` — дата выгрузки (ingestion date), формат `YYYY-MM-DD`.
*   **Схема**: Implicit (Схема источника). Файлы сохраняются "как есть", без валидации структуры содержимого, но с добавлением технических метаданных.
*   **Правило**: Файлы в Bronze **НИКОГДА** не перезаписываются и не удаляются (кроме политики Retention для архивации).

### 1.2. Метаданные (Wrapper)
Каждая запись в Bronze оборачивается или дополняется техническими полями при сохранении:

| Поле | Тип | Описание |
|------|-----|----------|
| `_ingestion_ts` | Timestamp (UTC) | Время получения записи. |
| `_run_id` | UUID | Идентификатор запуска пайплайна (Correlation ID). |
| `_batch_id` | UUID | Идентификатор пакета данных. |

**Примечание**: Если источник возвращает массив JSON, он разбивается на отдельные строки (records).

### 1.3. Реализация (Code Reference)
*   **Writer**: `src/bioetl/infrastructure/storage/bronze_writer.py`
*   **Логика**:
    1.  Получение батча данных от адаптера.
    2.  Добавление метаданных.
    3.  Сериализация в JSONL.
    4.  Сжатие `zstd`.
    5.  Загрузка в S3 с уникальным именем файла (обычно содержащим `run_id` и порядковый номер части).

---

## 2. Silver Layer (Нормализованные данные)

Слой Silver содержит очищенные, нормализованные и дедуплицированные данные. Это основной аналитический слой.

### 2.1. Формат и Технологии
*   **Формат**: Delta Lake (Parquet + Transaction Log).
*   **Engine**: `delta-rs` (через библиотеку `deltalake` Python binding).
*   **Путь**: `silver/{provider}/{entity}/[{partition_cols}/]` — партиционирование опционально, настраивается через `partition_by` в YAML конфиге пайплайна.
*   **Протокол**: Writer Version 2 (поддержка Column Mapping), Reader Version 1.

### 2.2. Схема и Валидация
Валидация происходит **перед** записью в Silver. Используется библиотека `pandera`.

*   **Контракты**: Определены в `src/bioetl/domain/schemas/{provider}.py`.
*   **Обработка ошибок валидации**:
    *   **Info/Warning** (например, новые поля или отсутствие необязательных): Данные пропускаются, но метаданные дрейфа схемы логируются.
    *   **Data Quality Error** (нарушение типов, провал check-ов):
        *   Soft Fail (<5%): Замена на `NULL` (если поле `nullable`) или пометка флагом `_dq_error`.
        *   Hard Fail (>20%): Батч отклоняется, запись в Quarantine.
    *   **Critical Schema Violation**: Исключение, остановка пайплайна.

### 2.3. Нормализация
Перед валидацией данные проходят стадию нормализации:
1.  **Приведение типов**: Строки "123" -> Int 123, "TRUE" -> Boolean True.
2.  **Очистка строк**: `strip()`, приведение к нижнему регистру (где применимо), удаление непечатных символов.
3.  **Обработка NULL**:
    *   Явные `NULL` сохраняются.
    *   Пустые строки `""` преобразуются в `NULL` (для строковых полей, если это не имеет бизнес-смысла).
    *   `NaN` (float) допустим, но строковые "NaN" преобразуются в `NULL`.
    *   Sentinel values (например, -1 для ID) преобразуются в `NULL`.
4.  **Даты**: Приведение всех дат к ISO 8601 (`YYYY-MM-DD`) и таймстемпов к UTC.

### 2.4. Дедупликация и Merge Strategy
Silver слой использует стратегию **Merge/Upsert** для обеспечения идемпотентности.

*   **Первичный ключ (Primary Key)**: Определяется для каждой сущности (например, `chembl_id`). Если естественного ключа нет, используется синтетический `content_hash`.
*   **Логика Merge**:
    *   Если запись с PK существует: Обновление (UPDATE).
    *   Если запись не существует: Вставка (INSERT).
*   **Приоритет обновлений (Conflict Resolution)**:
    При конкурентных запусках (например, Backfill vs Incremental) используется поле `_run_type`.
    Приоритет: `rebuild` > `backfill` > `incremental`.
    *В коде*: Условный update в Delta Merge (см. `src/bioetl/infrastructure/storage/delta_writer.py`).

### 2.5. PII и Безопасность
*   Поля, помеченные как чувствительные (PII), **ОБЯЗАНЫ** быть хэшированы перед записью в Silver.
*   **Алгоритм**: `sha256(lowercase(value) + SALT)`.
*   Соль управляется через Secrets Manager и ротируется (см. `RULES.md` §5.4.1).

### 2.6. Партиционирование
*   **Конфигурация**: Определяется через `partition_by` в `configs/pipelines/{provider}/{entity}.yaml`.
*   **Примеры**: `["year", "month"]` (по дате), `["assay_type"]` (по типу сущности), `[]` (без партиционирования).
*   **Стандарт**: По дате источника или по типу данных, если кардинальность низкая.
*   **Z-ORDER**: Не применяется в Silver (обычно сортировка по ingestion time), так как основная цель — write throughput.

---

## 3. Gold Layer (Витрины данных)

Слой Gold содержит агрегированные данные, подготовленные для бизнес-аналитики и ML-моделей. Данные моделируются в виде схем "Звезда" или широких витрин.

### 3.1. Silver → Gold Transformation

При переходе из Silver в Gold выполняется трансформация данных:

*   **Исключение JSON полей**: Вложенные JSON-строки, сохранённые в Silver для forensic целей, исключаются из Gold.
*   **Плоская структура**: Gold содержит только плоские (scalar) поля для оптимизации аналитических запросов.
*   **Реализация**: `BasePipeline.transform_for_gold()` метод с константой `GOLD_EXCLUDE_FIELDS`.

#### Пример: ChEMBL Molecule

| Silver (JSON) | Gold (Flat) |
|---------------|-------------|
| `molecule_hierarchy` (JSON string) | `hierarchy_parent_chembl_id`, `hierarchy_active_chembl_id` |
| `molecule_properties` (JSON string) | `property_mw_freebase`, `property_alogp`, `property_hba`, `property_hbd`, `property_psa`, `property_rtb`, `property_ro5_violations`, `property_qed_weighted`, `property_full_molformula` |
| `molecule_structures` (JSON string) | `structure_canonical_smiles`, `structure_standard_inchi`, `structure_standard_inchi_key` |
| `molecule_synonyms` (JSON string) | *Excluded* |
| `cross_references` (JSON string) | *Excluded* |
| `atc_classifications` (JSON string) | *Excluded* |

**Примечание**: Silver сохраняет полные JSON-данные для возможности восстановления и расследования (forensic retention).

### 3.2. Формат и Оптимизация
*   **Формат**: Delta Lake.
*   **Путь**: `gold/{domain}/{mart_name}/` (например, `gold/discovery/target_affinity`).
*   **Оптимизация чтения**:
    *   **Z-ORDER Clustering**: Обязательно применяется по часто используемым предикатам фильтрации (например, `target_id`, `assay_type`).
    *   **Compaction**: Регулярная (еженедельная) компрессия мелких файлов через `OPTIMIZE`.

### 3.3. Контракты Данных (Data Contracts)
Gold слой имеет строгие публичные контракты.
*   **Реестр**: JSON Schema файлы в `docs/contracts/gold/`.
*   **Стабильность**: Любое изменение схемы в Gold требует:
    1.  Обновления JSON-контракта.
    2.  Создания миграции или новой версии витрины (v2).
    3.  Уведомления потребителей (Breaking Change Policy).

### 3.4. Агрегация и Бизнес-логика
*   Джойны между разными сущностями (например, Activity + Molecule + Target).
*   Вычисление производных метрик (AVG, SUM).
*   Применение бизнес-фильтров (исключение отозванных статей, невалидных экспериментов).

### 3.5. Управление жизненным циклом (Lifecycle)
*   Данные в Gold часто перезаписываются полностью (`mode="overwrite"`) для партиций или всей таблицы при пересчете витрин.
*   Retention: Постоянное хранение, пока актуальна бизнес-задача.

---

## Сводная таблица характеристик

| Характеристика | Bronze | Silver | Gold |
|:---|:---|:---|:---|
| **Назначение** | Сырая выгрузка, Archive | Очищенные данные, Source of Truth | Аналитика, ML, Отчеты |
| **Формат** | JSONL + zstd | Delta Lake | Delta Lake |
| **Схема** | Schema-on-Read (Implicit) | Enforced (Pandera), Evolution | Strict (JSON Contracts) |
| **Мутабельность** | Append-only (Immutable) | Upsert (Merge) | Overwrite / Upsert |
| **Партиционирование** | Ingestion Date | Source Date / Entity Type | Business Dimensions |
| **Оптимизация** | Сжатие | Partitioning | Z-ORDER, Optimize |
| **PII** | Plain Text (Restricted Access) | Hashed + Salted | Aggregated / Excluded |
| **Recovery** | Replay source | Rebuild from Bronze | Recompute from Silver |
