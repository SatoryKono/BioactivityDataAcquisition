# Пайплайн: ChEMBL Assay

**Имя пайплайна:** `chembl_assay`
**Провайдер:** `chembl`
**Сущность:** `assay`
**Версия схемы:** 1.2.0

---

## 1. Описание

Пайплайн извлекает определения биоанализов (assay) из API ChEMBL. Каждая запись описывает экспериментальный метод измерения биологической активности, включая тип анализа, организм, условия и метаданные качества.

---

## 2. Конфигурация

**Файл:** `configs/entities/chembl/assay.yaml`

```yaml
version: 1.0.0
provider: chembl
entity: assay

pipeline:
    pipeline_name: chembl_assay
    provider: chembl
    entity_type: assay
    business_primary_keys: [assay_id]
    batch_size: 1000

schema:
    column_groups:
        - name: system
          fields: [entity_id, content_hash, _run_id, _run_type, _source_batch_id, _ingestion_ts, _index]
        - name: business
          fields: [assay_id, target_id, document_chembl_id, assay_type, confidence_score, description]
    silver:
        include_groups: [system, business, dq]
    gold:
        include_groups: [system, business]
        exclude_fields: [_dq_*, _source_batch_id, _index]
        alias_policy: canonical

quality:
    version: 1.1.0
    provider: chembl
    entity: assay
    field_validations:
        - field: assay_id
          type: required
          nullable: false
        - field: confidence_score
          type: range
          min: 0
          max: 9
          nullable: true

filters:
    version: 1.0.0
    provider: chembl
    entity: assay
    gold_filters:
        columns:
            assay_type: [B, F]
        ranges:
            confidence_score:
                min: 4
                include_min: true
```

---

## 3. Схема данных

### 3.1. Определение сущности Assay

**Файл:** `src/bioetl/domain/entities.py`

Сущность `Assay` содержит **39 полей**, сгруппированных по категориям:

#### Идентификаторы

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| `assay_id` | `str` | **Да** | Уникальный идентификатор анализа (например, `CHEMBL1234567`) |
| `target_id` | `str` | Нет | ChEMBL ID мишени |
| `document_chembl_id` | `str` | Нет | ChEMBL ID публикации |
| `cell_chembl_id` | `str` | Нет | ChEMBL ID клеточной линии |
| `tissue_chembl_id` | `str` | Нет | ChEMBL ID ткани |
| `src_id` | `int` | Нет | ID источника данных |
| `src_assay_id` | `str` | Нет | ID анализа в источнике |
| `aidx` | `str` | Нет | Внутренний индекс |

#### Классификация анализа

| Поле | Тип | Описание |
|------|-----|----------|
| `assay_type` | `str` | Код типа: `B` (Binding), `F` (Functional), `A` (ADMET), `T` (Toxicity), `U` (Unassigned), `P` (Physicochemical) |
| `assay_type_description` | `str` | Полное название типа |
| `assay_category` | `str` | Категория анализа |
| `assay_test_type` | `str` | Тип теста |
| `assay_group` | `str` | Группа анализа |

#### Биологический контекст

| Поле | Тип | Описание |
|------|-----|----------|
| `assay_organism` | `str` | Организм (например, `Homo sapiens`) |
| `assay_tax_id` | `int` | Таксономический ID |
| `assay_cell_type` | `str` | Тип клетки |
| `assay_tissue` | `str` | Ткань |
| `assay_strain` | `str` | Штамм |
| `assay_subcellular_fraction` | `str` | Субклеточная фракция |

#### BAO (BioAssay Ontology) аннотации

| Поле | Тип | Описание |
|------|-----|----------|
| `bao_format` | `str` | BAO формат (URI) |
| `bao_label` | `str` | BAO метка |

#### Описание и качество

| Поле | Тип | Описание |
|------|-----|----------|
| `description` | `str` | Текстовое описание анализа |
| `confidence_score` | `int` | Оценка уверенности (0-9) |
| `confidence_description` | `str` | Описание уровня уверенности |
| `relationship_type` | `str` | Тип связи с мишенью |
| `relationship_description` | `str` | Описание связи |

#### Дополнительные метаданные

| Поле | Тип | Описание |
|------|-----|----------|
| `assay_pref_name` | `str` | Предпочтительное название анализа (если доступно) |
| `score` | `float` | Оценка анализа (отличается от confidence_score) |

#### Вариантная информация (Variant Sequence)

Поля развёрнуты из вложенного словаря ChEMBL API (`variant_sequence`):

| Поле | Тип | Описание |
|------|-----|----------|
| `variant_accession` | `str` | UniProt accession варианта |
| `variant_isoform` | `str` | Идентификатор изоформы |
| `variant_mutation` | `str` | Описание мутации (например, V600E) |
| `variant_organism` | `str` | Организм варианта |
| `variant_sequence` | `str` | Аминокислотная последовательность |
| `variant_tax_id` | `int` | NCBI Taxonomy ID |
| `variant_sequence_json` | `str` | Оригинальный JSON (для forensic-анализа) |

> **Примечание**: Поля `variant-*` извлекаются из вложенного словаря API с помощью `flatten_nested_dict()`. Поле `variant_sequence_json` сохраняет оригинальную структуру для аудита.

#### Комплексные поля

| Поле | Тип | Описание |
|------|-----|----------|
| `assay_classifications` | `str` | Классификации (JSON-строка списка) |
| `assay_parameters` | `str` | Параметры анализа (JSON-строка списка) |

#### Системные поля (добавляются при обработке)

| Поле | Тип | Описание |
|------|-----|----------|
| `entity_id` | `str` | `chembl:{assay_id}` |
| `content_hash` | `str` | SHA256-хеш содержимого |
| `_run_id` | `str` | UUID запуска пайплайна |
| `_run_type` | `str` | `incremental`, `backfill`, `rebuild` |
| `_source_batch_id` | `str` | UUID батча |
| `_ingestion_ts` | `str` | Timestamp загрузки (ISO8601) |

---

### 3.2. Валидация при создании сущности

```python
def validate_invariants(self) -> None:
    if not self.assay_id:
        raise ValueError("Assay ChEMBL ID is required")
    if self.confidence_score is not None and not (0 <= self.confidence_score <= 9):
        raise ValueError(f"Confidence score must be 0-9, got {self.confidence_score}")
```

---

## 4. Нормализация данных

**Файл:** `src/bioetl/application/pipelines/chembl/assay_transformer.py`

### 4.1. Этапы трансформации

```
Сырой JSON (ChEMBL API)
         │
         ▼
    1. Генерация entity_id
         │
         ▼
    2. Нормализация типов
         │
         ▼
    3. Генерация content_hash
         │
         ▼
    4. Добавление системных полей
         │
         ▼
    SilverRecord (dict)
```

### 4.2. Правила нормализации типов

| Исходный тип | Преобразование |
|--------------|----------------|
| `int` | → безопасная конвертация или `None` |
| `str` | → `strip()` |
| `dict`, `list` | → JSON-строка |

### 4.3. Генерация идентификаторов

```python
# Entity ID: уникальный бизнес-ключ
entity_id = f"chembl:{assay_id}"

# Content Hash: SHA256 для версионирования
content_hash = sha256(
    "chembl" + canonical_json(business_fields)
)
```

---

## 5. Валидация и Data Quality

### 5.1. Классификация ошибок

| Тип | Поведение | Примеры |
|-----|-----------|---------|
| **Critical** | Остановка пайплайна | Auth failure, schema mismatch |
| **Recoverable** | Retry (3x, backoff 2.0) | 429, 502, 504 |
| **Data Quality** | Карантин записи | Invalid assay_id |

### 5.2. DQ-правила для Assay

1. **`assay_id`** — обязательное поле
2. **`confidence_score`** ∈ [0, 9] если присутствует
3. **`assay_type`** ∈ {B, F, A, T, U, P} (рекомендуется)

### 5.3. Пороги ошибок

| Порог | Условие | Действие |
|-------|---------|----------|
| Soft | > 5% ошибок в батче | WARNING в лог |
| Hard | > 20% ошибок в батче | `DataQualityThresholdError` |

---

## 6. Запись в слои Medallion

### 6.1. Bronze Layer

```
Путь: bronze/v1/chembl/assay/2025-12-22/batch-{uuid}.jsonl.zst
```

| Параметр | Значение |
|----------|----------|
| **Формат** | JSONL + Zstandard |
| **Режим** | Append-only |
| **Retention** | 90 дней |

---

### 6.2. Silver Layer

**PyArrow Schema** (`src/bioetl/infrastructure/schemas/silver.py`):

```python
CHEMBL_ASSAY_SCHEMA = pa.schema([
    pa.field("entity_id", pa.string()),
    pa.field("content_hash", pa.string()),
    pa.field("assay_id", pa.string()),
    pa.field("target_id", pa.string()),
    pa.field("document_chembl_id", pa.string()),
    pa.field("assay_type", pa.string()),
    pa.field("assay_type_description", pa.string()),
    pa.field("assay_organism", pa.string()),
    pa.field("confidence_score", pa.int64()),
    pa.field("bao_format", pa.string()),
    pa.field("bao_label", pa.string()),
    pa.field("description", pa.string()),
    pa.field("_run_id", pa.string()),
    pa.field("_run_type", pa.string()),
    pa.field("_ingestion_ts", pa.string()),
    # ... всего 43 поля (39 бизнес + 4 системных)
])
```

| Параметр | Значение |
|----------|----------|
| **Формат** | Delta Lake |
| **Merge Key** | `assay_id` |
| **Партиционирование** | `assay_type` |

---

### 6.3. Gold Layer

#### Фильтр для Gold

Фильтрация для Gold настраивается в `configs/entities/chembl/assay.yaml`
через секцию `filters.gold_filters`.

```python
def should_include(self, -context, record) -> bool:
    # Фильтр по типу анализа
    if self.preferred_types:
        assay_type = record.get("assay_type")
        if assay_type not in self.preferred_types:
            return False

    # Фильтр по confidence_score
    confidence_score = record.get("confidence_score")
    if confidence_score is not None:
        if int(confidence_score) < self.min_confidence:
            return False

    return True
```

| Параметр | Значение |
|----------|----------|
| **Формат** | Delta Lake |
| **Режим** | Overwrite |
| **Валидация** | Strict Pandera schema |

#### Критерии Gold

По умолчанию в Gold попадают анализы:
- `assay_type` = `B` (Binding) или `F` (Functional)
- `confidence_score` >= 4

---

## 7. Полный поток данных

```
ChEMBL API (/assay.json)
         │
         ▼
┌─────────────────────────────────────────┐
│  BRONZE (сырые данные)                  │
│  ─────────────────────────────────────  │
│  • Путь: bronze/v1/chembl/assay/...     │
│  • Формат: JSONL + Zstandard            │
│  • Режим: Append-only                   │
│  • Retention: 90 дней                   │
└─────────────────────────────────────────┘
         │
         ▼ AssayTransformer.transform()
         │
         ├── DQ Error? ──► QUARANTINE
         │                   │
         ▼                   ▼
┌─────────────────────────────────────────┐
│  SILVER (нормализованные данные)        │
│  ─────────────────────────────────────  │
│  • Формат: Delta Lake                   │
│  • Merge by: assay_id            │
│  • Schema: 43 поля (PyArrow)            │
│  • Партиции: assay_type                 │
└─────────────────────────────────────────┘
         │
         ▼ AssayGoldFilter.should_include()
         │
         ├── Не прошёл? ──► (пропускаем)
         │
         ▼
┌─────────────────────────────────────────┐
│  GOLD (бизнес-данные)                   │
│  ─────────────────────────────────────  │
│  • Только B/F типы с confidence >= 4    │
│  • Strict Pandera validation            │
│  • Режим: Overwrite                     │
└─────────────────────────────────────────┘
```

---

## 8. Типы анализов (Assay Types)

| Код | Название | Описание |
|-----|----------|----------|
| **B** | Binding | Анализы связывания (IC50, Ki, Kd) |
| **F** | Functional | Функциональные анализы (EC50, ED50) |
| **A** | ADMET | Фармакокинетика (всасывание, распределение, метаболизм) |
| **T** | Toxicity | Токсикологические тесты |
| **P** | Physicochemical | Физико-химические свойства |
| **U** | Unassigned | Не классифицированные |

---

## 9. Инкрементальная загрузка

Отдельный watermark-модуль удалён (см. ADR-011). Инкрементальность обеспечивается
через `run_type`, checkpoints и идемпотентный merge по ключам.

---

## 10. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/entities/chembl/assay.yaml` |
| Сущность | `src/bioetl/domain/entities.py` |
| Трансформер | `src/bioetl/application/pipelines/chembl/assay_transformer.py` |
| Gold-фильтр | `configs/entities/chembl/assay.yaml` (`filters.gold_filters`) |
| Pipeline defs | `src/bioetl/application/pipelines/chembl/_pipelines.py` |
| Silver Schema | `src/bioetl/infrastructure/schemas/silver.py` |
| Gold Schema | `src/bioetl/infrastructure/schemas/gold.py` |
| Data Contract | `docs/04-reference/contracts/gold/chembl_assay_v1.0.json` |

---

## 11. Пример использования CLI

```bash
# Инкрементальная загрузка (по умолчанию)
bioetl run --pipeline chembl_assay

# С ограничением количества записей
bioetl run --pipeline chembl_assay --limit 1000

# Полная перезагрузка
bioetl run --pipeline chembl_assay --run-type rebuild

# С фильтрацией по ID из CSV
bioetl run --pipeline chembl_assay --input-csv data/input/assay.csv
```

---

*Последнее обновление: 2025-12-24*
