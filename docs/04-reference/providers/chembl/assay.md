# Пайплайн: ChEMBL Assay

**Имя пайплайна:** `chembl-assay`
**Провайдер:** `chembl`
**Сущность:** `assay`
**Версия схемы:** 1.2.0

---

## 1. Описание

Пайплайн извлекает определения биоанализов (assay) из API ChEMBL. Каждая запись описывает экспериментальный метод измерения биологической активности, включая тип анализа, организм, условия и метаданные качества.

---

## 2. Конфигурация

**Файл:** `configs/pipelines/chembl/assay.yaml`

```yaml
pipeline-name: chembl-assay
provider: chembl
entity-type: assay
version: "1.2.0"
primary-keys: ["assay-chembl-id"]
silver-table: "chembl-assay"

gold-filter-types:
    - B  # Binding
    - F  # Functional
gold-min-confidence: 4  # Минимальный confidence-score (0-9)

transform:
    steps:
        - normalize-values
        - add-metadata
        - calculate-content-hash

sink:
    bronze:
        path: "data/output/bronze"
        format: jsonl
        save-json: true
    silver:
        path: "data/output/silver"
        format: delta
        mode: merge
        partition-by: ["assay-type"]
    gold:
        enabled: true
        path: "data/output/gold"
        format: delta
        mode: overwrite

dq-overrides:
    soft-fail-threshold: 0.05   # 5% ошибок → WARNING
    hard-fail-threshold: 0.20   # 20% ошибок → FAIL BATCH
```

---

## 3. Схема данных

### 3.1. Определение сущности Assay

**Файл:** `src/bioetl/domain/entities.py`

Сущность `Assay` содержит **39 полей**, сгруппированных по категориям:

#### Идентификаторы

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| `assay-chembl-id` | `str` | **Да** | Уникальный идентификатор анализа (например, `CHEMBL1234567`) |
| `target-chembl-id` | `str` | Нет | ChEMBL ID мишени |
| `document-chembl-id` | `str` | Нет | ChEMBL ID публикации |
| `cell-chembl-id` | `str` | Нет | ChEMBL ID клеточной линии |
| `tissue-chembl-id` | `str` | Нет | ChEMBL ID ткани |
| `src-id` | `int` | Нет | ID источника данных |
| `src-assay-id` | `str` | Нет | ID анализа в источнике |
| `aidx` | `str` | Нет | Внутренний индекс |

#### Классификация анализа

| Поле | Тип | Описание |
|------|-----|----------|
| `assay-type` | `str` | Код типа: `B` (Binding), `F` (Functional), `A` (ADMET), `T` (Toxicity), `U` (Unassigned), `P` (Physicochemical) |
| `assay-type-description` | `str` | Полное название типа |
| `assay-category` | `str` | Категория анализа |
| `assay-test-type` | `str` | Тип теста |
| `assay-group` | `str` | Группа анализа |

#### Биологический контекст

| Поле | Тип | Описание |
|------|-----|----------|
| `assay-organism` | `str` | Организм (например, `Homo sapiens`) |
| `assay-tax-id` | `int` | Таксономический ID |
| `assay-cell-type` | `str` | Тип клетки |
| `assay-tissue` | `str` | Ткань |
| `assay-strain` | `str` | Штамм |
| `assay-subcellular-fraction` | `str` | Субклеточная фракция |

#### BAO (BioAssay Ontology) аннотации

| Поле | Тип | Описание |
|------|-----|----------|
| `bao-format` | `str` | BAO формат (URI) |
| `bao-label` | `str` | BAO метка |

#### Описание и качество

| Поле | Тип | Описание |
|------|-----|----------|
| `description` | `str` | Текстовое описание анализа |
| `confidence-score` | `int` | Оценка уверенности (0-9) |
| `confidence-description` | `str` | Описание уровня уверенности |
| `relationship-type` | `str` | Тип связи с мишенью |
| `relationship-description` | `str` | Описание связи |

#### Дополнительные метаданные

| Поле | Тип | Описание |
|------|-----|----------|
| `assay-pref-name` | `str` | Предпочтительное название анализа (если доступно) |
| `score` | `float` | Оценка анализа (отличается от confidence-score) |

#### Вариантная информация (Variant Sequence)

Поля развёрнуты из вложенного словаря ChEMBL API (`variant-sequence`):

| Поле | Тип | Описание |
|------|-----|----------|
| `variant-accession` | `str` | UniProt accession варианта |
| `variant-isoform` | `str` | Идентификатор изоформы |
| `variant-mutation` | `str` | Описание мутации (например, V600E) |
| `variant-organism` | `str` | Организм варианта |
| `variant-sequence` | `str` | Аминокислотная последовательность |
| `variant-tax-id` | `int` | NCBI Taxonomy ID |
| `variant-sequence-json` | `str` | Оригинальный JSON (для forensic-анализа) |

> **Примечание**: Поля `variant-*` извлекаются из вложенного словаря API с помощью `flatten-nested-dict()`. Поле `variant-sequence-json` сохраняет оригинальную структуру для аудита.

#### Комплексные поля

| Поле | Тип | Описание |
|------|-----|----------|
| `assay-classifications` | `str` | Классификации (JSON-строка списка) |
| `assay-parameters` | `str` | Параметры анализа (JSON-строка списка) |

#### Системные поля (добавляются при обработке)

| Поле | Тип | Описание |
|------|-----|----------|
| `entity-id` | `str` | `chembl:{assay-chembl-id}` |
| `content-hash` | `str` | SHA256-хеш содержимого |
| `-run-id` | `str` | UUID запуска пайплайна |
| `-run-type` | `str` | `incremental`, `backfill`, `rebuild` |
| `-source-batch-id` | `str` | UUID батча |
| `-ingestion-ts` | `str` | Timestamp загрузки (ISO8601) |

---

### 3.2. Валидация при создании сущности

```python
def -validate-invariants(self) -> None:
    if not self.assay-chembl-id:
        raise ValueError("Assay ChEMBL ID is required")
    if self.confidence-score is not None and not (0 <= self.confidence-score <= 9):
        raise ValueError(f"Confidence score must be 0-9, got {self.confidence-score}")
```

---

## 4. Нормализация данных

**Файл:** `src/bioetl/application/pipelines/chembl/assay-transformer.py`

### 4.1. Этапы трансформации

```
Сырой JSON (ChEMBL API)
         │
         ▼
    1. Генерация entity-id
         │
         ▼
    2. Нормализация типов
         │
         ▼
    3. Генерация content-hash
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
entity-id = f"chembl:{assay-chembl-id}"

# Content Hash: SHA256 для версионирования
content-hash = sha256(
    "chembl" + canonical-json(business-fields)
)
```

---

## 5. Валидация и Data Quality

### 5.1. Классификация ошибок

| Тип | Поведение | Примеры |
|-----|-----------|---------|
| **Critical** | Остановка пайплайна | Auth failure, schema mismatch |
| **Recoverable** | Retry (3x, backoff 2.0) | 429, 502, 504 |
| **Data Quality** | Карантин записи | Invalid assay-chembl-id |

### 5.2. DQ-правила для Assay

1. **`assay-chembl-id`** — обязательное поле
2. **`confidence-score`** ∈ [0, 9] если присутствует
3. **`assay-type`** ∈ {B, F, A, T, U, P} (рекомендуется)

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
CHEMBL-ASSAY-SCHEMA = pa.schema([
    pa.field("entity-id", pa.string()),
    pa.field("content-hash", pa.string()),
    pa.field("assay-chembl-id", pa.string()),
    pa.field("target-chembl-id", pa.string()),
    pa.field("document-chembl-id", pa.string()),
    pa.field("assay-type", pa.string()),
    pa.field("assay-type-description", pa.string()),
    pa.field("assay-organism", pa.string()),
    pa.field("confidence-score", pa.int64()),
    pa.field("bao-format", pa.string()),
    pa.field("bao-label", pa.string()),
    pa.field("description", pa.string()),
    pa.field("-run-id", pa.string()),
    pa.field("-run-type", pa.string()),
    pa.field("-ingestion-ts", pa.string()),
    # ... всего 43 поля (39 бизнес + 4 системных)
])
```

| Параметр | Значение |
|----------|----------|
| **Формат** | Delta Lake |
| **Merge Key** | `assay-chembl-id` |
| **Партиционирование** | `assay-type` |

---

### 6.3. Gold Layer

#### Фильтр для Gold

**Файл:** `src/bioetl/application/pipelines/chembl/assay-filter.py`

```python
def should-include(self, -context, record) -> bool:
    # Фильтр по типу анализа
    if self.preferred-types:
        assay-type = record.get("assay-type")
        if assay-type not in self.preferred-types:
            return False

    # Фильтр по confidence-score
    confidence-score = record.get("confidence-score")
    if confidence-score is not None:
        if int(confidence-score) < self.min-confidence:
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
- `assay-type` = `B` (Binding) или `F` (Functional)
- `confidence-score` >= 4

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
│  • Merge by: assay-chembl-id            │
│  • Schema: 43 поля (PyArrow)            │
│  • Партиции: assay-type                 │
└─────────────────────────────────────────┘
         │
         ▼ AssayGoldFilter.should-include()
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

**Файл:** `src/bioetl/application/pipelines/chembl/assay-watermark.py`

Для инкрементальных запусков используется `assay-chembl-id` как watermark:

```python
def extract(self, -context, record) -> Watermark:
    assay-id = record.get("assay-chembl-id")
    if assay-id is not None:
        return Watermark.from-id(str(assay-id))
    return Watermark.from-id("")
```

---

## 10. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/pipelines/chembl/assay.yaml` |
| Сущность | `src/bioetl/domain/entities.py` |
| Трансформер | `src/bioetl/application/pipelines/chembl/assay-transformer.py` |
| Gold-фильтр | `src/bioetl/application/pipelines/chembl/assay-filter.py` |
| Watermark | `src/bioetl/application/pipelines/chembl/assay-watermark.py` |
| Silver Schema | `src/bioetl/infrastructure/schemas/silver.py` |
| Gold Schema | `src/bioetl/infrastructure/schemas/gold.py` |
| Data Contract | `docs/contracts/chembl-assay-gold.json` |

---

## 11. Пример использования CLI

```bash
# Инкрементальная загрузка (по умолчанию)
bioetl run --pipeline chembl-assay

# С ограничением количества записей
bioetl run --pipeline chembl-assay --limit 1000

# Полная перезагрузка
bioetl run --pipeline chembl-assay --run-type rebuild

# С фильтрацией по ID из CSV
bioetl run --pipeline chembl-assay --input-csv data/input/assay.csv
```

---

*Последнее обновление: 2025-12-24*
