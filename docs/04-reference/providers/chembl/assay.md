# Пайплайн: ChEMBL Assay

**Имя пайплайна:** `chembl_assay`
**Провайдер:** `chembl`
**Сущность:** `assay`
**Версия схемы:** 1.0.0

---

## 1. Описание

Пайплайн извлекает определения биоанализов (assay) из API ChEMBL. Каждая запись описывает экспериментальный метод измерения биологической активности, включая тип анализа, организм, условия и метаданные качества.

---

## 2. Конфигурация

**Файл:** `configs/pipelines/chembl/assay.yaml`

```yaml
pipeline_name: chembl_assay
provider: chembl
entity_type: assay
version: "1.0.0"
primary_keys: ["assay_chembl_id"]
silver_table: "chembl_assay"

gold_filter_types:
    - B  # Binding
    - F  # Functional
gold_min_confidence: 4  # Минимальный confidence_score (0-9)

transform:
    steps:
        - normalize_values
        - add_metadata
        - calculate_content_hash

sink:
    bronze:
        path: "data/output/bronze"
        format: jsonl
        save_json: true
    silver:
        path: "data/output/silver"
        format: delta
        mode: merge
        partition_by: ["assay_type"]
    gold:
        enabled: true
        path: "data/output/gold"
        format: delta
        mode: overwrite

dq_rules:
    soft_fail_threshold: 0.05   # 5% ошибок → WARNING
    hard_fail_threshold: 0.20   # 20% ошибок → FAIL BATCH
```

---

## 3. Схема данных

### 3.1. Определение сущности Assay

**Файл:** `src/bioetl/domain/entities.py`

Сущность `Assay` содержит **39 полей**, сгруппированных по категориям:

#### Идентификаторы

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| `assay_chembl_id` | `str` | **Да** | Уникальный идентификатор анализа (например, `CHEMBL1234567`) |
| `target_chembl_id` | `str` | Нет | ChEMBL ID мишени |
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

> **Примечание**: Поля `variant_*` извлекаются из вложенного словаря API с помощью `flatten_nested_dict()`. Поле `variant_sequence_json` сохраняет оригинальную структуру для аудита.

#### Комплексные поля

| Поле | Тип | Описание |
|------|-----|----------|
| `assay_classifications` | `str` | Классификации (JSON-строка списка) |
| `assay_parameters` | `str` | Параметры анализа (JSON-строка списка) |

#### Системные поля (добавляются при обработке)

| Поле | Тип | Описание |
|------|-----|----------|
| `entity_id` | `str` | `chembl:{assay_chembl_id}` |
| `content_hash` | `str` | SHA256-хеш содержимого |
| `_run_id` | `str` | UUID запуска пайплайна |
| `_run_type` | `str` | `incremental`, `backfill`, `rebuild` |
| `_source_batch_id` | `str` | UUID батча |
| `_ingestion_ts` | `str` | Timestamp загрузки (ISO8601) |

---

### 3.2. Валидация при создании сущности

```python
def _validate_invariants(self) -> None:
    if not self.assay_chembl_id:
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
entity_id = f"chembl:{assay_chembl_id}"

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
| **Data Quality** | Карантин записи | Invalid assay_chembl_id |

### 5.2. DQ-правила для Assay

1. **`assay_chembl_id`** — обязательное поле
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
Путь: bronze/v1/chembl/assay/2025-12-22/batch_{uuid}.jsonl.zst
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
    pa.field("assay_chembl_id", pa.string()),
    pa.field("target_chembl_id", pa.string()),
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
| **Merge Key** | `assay_chembl_id` |
| **Партиционирование** | `assay_type` |

---

### 6.3. Gold Layer

#### Фильтр для Gold

**Файл:** `src/bioetl/application/pipelines/chembl/assay_filter.py`

```python
def should_include(self, _context, record) -> bool:
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
│  • Merge by: assay_chembl_id            │
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

## 9. Watermark (инкрементальная загрузка)

**Файл:** `src/bioetl/application/pipelines/chembl/assay_watermark.py`

Для инкрементальных запусков используется `assay_chembl_id` как watermark:

```python
def extract(self, _context, record) -> Watermark:
    assay_id = record.get("assay_chembl_id")
    if assay_id is not None:
        return Watermark.from_id(str(assay_id))
    return Watermark.from_id("")
```

---

## 10. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/pipelines/chembl/assay.yaml` |
| Сущность | `src/bioetl/domain/entities.py` |
| Трансформер | `src/bioetl/application/pipelines/chembl/assay_transformer.py` |
| Gold-фильтр | `src/bioetl/application/pipelines/chembl/assay_filter.py` |
| Watermark | `src/bioetl/application/pipelines/chembl/assay_watermark.py` |
| Silver Schema | `src/bioetl/infrastructure/schemas/silver.py` |
| Gold Schema | `src/bioetl/infrastructure/schemas/gold.py` |
| Data Contract | `docs/contracts/chembl_assay_gold.json` |

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
