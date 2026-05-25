______________________________________________________________________

Version: 1.2.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# Пайплайн: ChEMBL Activity

**Имя пайплайна:** `chembl_activity`
**Провайдер:** `chembl`
**Сущность:** `activity`
**Версия схемы:** 1.2.0

______________________________________________________________________

## 1. Описание

Пайплайн извлекает данные о биологической активности молекул из API ChEMBL. Каждая запись содержит результат измерения активности (IC50, Ki, Kd, EC50, AC50, GI50, ED50, MIC, CC50 и др.) для пары молекула-мишень.

______________________________________________________________________

## 2. Конфигурация

**Файл:** `configs/entities/chembl/activity.yaml`

```yaml
version: 1.0.0
provider: chembl
entity: activity

pipeline:
    pipeline_name: chembl_activity
    provider: chembl
    entity_type: activity
    business_primary_keys: [activity_id]
    batch_size: 1000
    sink:
        silver:
            mode: merge
        gold:
            enabled: false

schema:
    column_groups:
        - name: system
          fields: [entity_id, content_hash, _source, _index]
        - name: business
          fields: [activity_id, molecule_id, target_id, assay_id, standard_type, standard_value, standard_units]
    silver:
        include_groups: [system, business, dq]
    gold:
        include_groups: [system, business]
        exclude_fields: [_dq_*, _index]
        alias_policy: canonical

quality:
    version: 1.1.0
    provider: chembl
    entity: activity
    field_validations:
        - field: activity_id
          type: required
          nullable: false
```

______________________________________________________________________

## 3. Схема данных

### 3.1. Определение сущности Activity

**Файл:** `src/bioetl/domain/entities/bioactivity/_entity.py`

Сущность `Bioactivity` содержит **77 dataclass-полей** (включая унаследованные служебные поля `BaseEntity`), сгруппированных по категориям:

#### Идентификаторы

| Поле                 | Тип   | Обязательное | Описание                                        |
| -------------------- | ----- | ------------ | ----------------------------------------------- |
| `activity_id`        | `str` | **Да**       | Уникальный идентификатор записи активности      |
| `molecule_id`        | `str` | **Да**       | Канонический ID молекулы (например, `CHEMBL25`) |
| `target_id`          | `str` | Нет          | Канонический ID мишени                          |
| `assay_id`           | `str` | Нет          | Канонический ID анализа                         |
| `publication_id`     | `str` | Нет          | Канонический ID публикации (provider PK)        |
| `publication_doi`    | `str` | Нет          | DOI публикации                                  |
| `publication_pmid`   | `str` | Нет          | PubMed ID                                       |
| `publication_pmc_id` | `str` | Нет          | PubMed Central ID                               |
| `record_id`          | `int` | Нет          | Внутренний ID записи                            |
| `src_id`             | `int` | Нет          | ID источника данных                             |

`publication_doi`, `publication_pmid` и `publication_pmc_id` заполняются из
canonical activity fields, если они уже есть в Bronze payload. Для совместимости
трансформер также принимает provider aliases: `doi`/`document_doi`,
`pmid`/`pubmed_id`/`document_pubmed_id` и `pmc_id`/`document_pmc_id`.
Нормализация выполняется профильным слоем до расчёта `content_hash`, поэтому
регистровые различия DOI не создают hash drift.

#### Данные молекулы

| Поле                 | Тип   | Описание                           |
| -------------------- | ----- | ---------------------------------- |
| `canonical_smiles`   | `str` | SMILES-формула молекулы            |
| `molecule_pref_name` | `str` | Предпочтительное название молекулы |
| `parent_molecule_id` | `str` | ID родительской молекулы           |

#### Данные мишени

| Поле                 | Тип     | Описание                                |
| -------------------- | ------- | --------------------------------------- |
| `target_pref_name`   | `str`   | Название мишени                         |
| `target_organism`    | `str`   | Организм мишени                         |
| `target_taxonomy_id` | `float` | NCBI Taxonomy ID (nullable int pattern) |

#### Данные анализа

| Поле                      | Тип   | Описание                           |
| ------------------------- | ----- | ---------------------------------- |
| `assay_type`              | `str` | Тип анализа (B, F, A, T, P)        |
| `assay_description`       | `str` | Описание анализа                   |
| `assay_variant_accession` | `str` | Accession варианта белка в анализе |
| `assay_variant_mutation`  | `str` | Мутация варианта в анализе         |
| `bao_endpoint`            | `str` | BAO endpoint (онтология)           |
| `bao_endpoint_iri`        | `str` | Persistent OBO IRI для endpoint    |
| `bao_endpoint_mapping_status` | `str` | Статус IRI mapping: `mapped`, `unmapped`, `missing` |
| `bao_format`              | `str` | BAO format                         |
| `bao_format_iri`          | `str` | Persistent OBO IRI для assay format |
| `bao_format_mapping_status` | `str` | Статус IRI mapping: `mapped`, `unmapped`, `missing` |
| `bao_label`               | `str` | BAO label                          |
| `bao_ontology_version`    | `str` | Версия BAO registry для companion IRI |

BAO token-поля (`bao_endpoint`, `bao_format`, `bao_label`) сохраняются для обратной
совместимости. Companion-поля добавляют machine-readable IRI, версию ontology
registry и статус mapping без изменения исторических token-полей.

#### Сырые значения активности

| Поле          | Тип     | Описание                       |
| ------------- | ------- | ------------------------------ |
| `type`        | `str`   | Тип измерения (сырой)          |
| `value`       | `float` | Значение (сырое)               |
| `units`       | `str`   | Единицы измерения (сырые)      |
| `relation`    | `str`   | Отношение (`=`, `<`, `>`, `~`) |
| `upper_value` | `float` | Верхняя граница диапазона      |
| `text_value`  | `str`   | Текстовое значение             |
| `qudt_units`  | `str`   | Единицы из онтологии QUDT      |
| `qudt_unit_iri` | `str` | Persistent QUDT unit IRI |
| `qudt_unit_mapping_status` | `str` | Статус QUDT mapping: `mapped`, `unmapped`, `missing` |
| `qudt_ontology_version` | `str` | Версия QUDT registry для companion IRI |
| `uo_units`    | `str`   | Единицы из онтологии UO        |
| `uo_unit_iri` | `str` | Persistent OBO IRI для UO unit |
| `uo_unit_mapping_status` | `str` | Статус UO mapping: `mapped`, `unmapped`, `missing` |
| `uo_ontology_version` | `str` | Версия UO registry для companion IRI |

Для неизвестных или provider-specific единиц token сохраняется, а companion IRI
остаётся `null` со статусом `unmapped`. Для отсутствующих значений статус
становится `missing`.

#### Стандартизированные значения

| Поле                   | Тип     | Описание                                                             |
| ---------------------- | ------- | -------------------------------------------------------------------- |
| `standard_type`        | `str`   | Тип: IC50, Ki, Kd, EC50, AC50, GI50, ED50, MIC, CC50, EC50, Kd и др. |
| `standard_value`       | `float` | Стандартизированное значение                                         |
| `standard_units`       | `str`   | Единицы: nM, uM, и др.                                               |
| `standard_relation`    | `str`   | Отношение                                                            |
| `standard_upper_value` | `float` | Верхняя граница                                                      |
| `standard_text_value`  | `str`   | Текстовое стандартизированное значение                               |
| `standard_flag`        | `int`   | Флаг стандартизации                                                  |

#### Вычисляемые метрики

| Поле            | Тип     | Описание                       |
| --------------- | ------- | ------------------------------ |
| `pchembl_value` | `float` | pChEMBL = -log10(IC50 в молях) |

##### Метрики эффективности лиганда (Ligand Efficiency)

| Поле                    | Тип     | Описание                                                                   |
| ----------------------- | ------- | -------------------------------------------------------------------------- |
| `ligand_efficiency_bei` | `float` | **BEI** (Binding Efficiency Index) — эффективность связывания на атом      |
| `ligand_efficiency_le`  | `float` | **LE** (Ligand Efficiency) — изменение энергии связывания на тяжелый атом  |
| `ligand_efficiency_lle` | `float` | **LLE** (Lipophilic Ligand Efficiency) — баланс активности и липофильности |
| `ligand_efficiency_sei` | `float` | **SEI** (Surface Efficiency Index) — эффективность по площади поверхности  |

> **Примечание**: Все метрики ligand-efficiency вычисляются ChEMBL и предоставляются через API. В Silver слое они разворачиваются из вложенного словаря в отдельные колонки для удобства аналитики.

#### Данные публикации (Document/Publication data)

| Поле               | Тип   | Описание          |
| ------------------ | ----- | ----------------- |
| `journal`          | `str` | Журнал публикации |
| `publication_year` | `int` | Год публикации    |

#### Метаданные качества

| Поле                        | Тип   | Описание                                     |
| --------------------------- | ----- | -------------------------------------------- |
| `activity_comment`          | `str` | Комментарий к активности                     |
| `data_validity_comment`     | `str` | Комментарий о валидности                     |
| `data_validity_description` | `str` | Описание проблемы с данными                  |
| `potential_duplicate`       | `int` | Флаг потенциального дубликата                |
| `manual_curation_flag`      | `int` | Флаг ручной кураторской проверки (0/1)       |
| `original_activity_id`      | `int` | ID исходной записи активности (traceability) |

#### Тип действия (Action Type)

Поля развёрнуты из вложенного словаря ChEMBL API (`action_type`):

| Поле                      | Тип   | Описание                                            |
| ------------------------- | ----- | --------------------------------------------------- |
| `action_type`             | `str` | Тип действия: INHIBITOR, AGONIST, ANTAGONIST и др.  |
| `action_type_description` | `str` | Описание типа действия                              |
| `action_type_parent_type` | `str` | Родительская группа типа действия (может быть null) |

> **Примечание**: Поля `action_type_*` извлекаются из вложенного словаря API с помощью `flatten_nested_dict()`. Если запись не содержит информации о типе действия, все поля будут `None`.

#### Системные поля persisted-row contract

| Поле           | Тип   | Описание                            |
| -------------- | ----- | ----------------------------------- |
| `entity_id`    | `str` | `chembl:{activity_id}`              |
| `content_hash` | `str` | SHA256-хеш содержимого              |
| `_source`      | `str` | Канонический provider/source anchor |
| `_index`       | `int` | Порядковый индекс записи в батче    |

Occurrence-scoped provenance (`_run_id`, `_run_type`, `_source_batch_id`,
`_ingestion_ts`) не входит в физический Silver/Gold row contract и
публикуется через sidecar metadata, lineage fragments, run manifest, run
ledger и audit artifacts.

______________________________________________________________________

### 3.2. Валидация при создании сущности

```python
def validate_invariants(self) -> None:
    if not self.activity_id:
        raise ValueError("Activity ID is required")
    if not self.molecule_id:
        raise ValueError("Molecule ID is required")
    if self.pchembl_value is not None and self.pchembl_value < 0:
        raise ValueError("pChemBL value must be non-negative")
```

______________________________________________________________________

## 4. Нормализация данных

**Файл:** `src/bioetl/application/pipelines/chembl/activity_transformer.py`

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

| Исходный тип      | Преобразование                      |
| ----------------- | ----------------------------------- |
| `float` с NaN/Inf | → `None`                            |
| `float`           | → `round(value, 10)`                |
| `int`             | → безопасная конвертация или `None` |
| `str`             | → `strip()`                         |
| `dict`, `list`    | → JSON-строка                       |

### 4.3. Генерация идентификаторов

```python
# Entity ID: уникальный бизнес-ключ
entity_id = f"chembl:{activity_id}"

# Content Hash: SHA256 для версионирования
content_hash = sha256("chembl" + canonical_json(business_fields))
```

### 4.4. Поля, исключённые из хеша

```python
META_FIELDS = {
    "_ingestion_ts",
    "_run_id",
    "_run_type",
    "_dq_warn",
    "_dq_error",
    "_source_batch_id",
}
```

______________________________________________________________________

## 5. Валидация и Data Quality

### 5.1. Классификация ошибок

| Тип              | Поведение               | Примеры                       |
| ---------------- | ----------------------- | ----------------------------- |
| **Critical**     | Остановка пайплайна     | Auth failure, schema mismatch |
| **Recoverable**  | Retry (3x, backoff 2.0) | 429, 502, 504                 |
| **Data Quality** | Карантин записи         | Invalid SMILES, missing field |

### 5.2. DQ-правила для Activity

1. **`standard_value` > 0** — не null, не отрицательный
1. **`standard_type`** ∈ {IC50, Ki, Kd, EC50, AC50, GI50, ED50, MIC, CC50, EC50, Kd, ...}
1. **`molecule_id`** соответствует regex `^CHEMBL\d+$`

### 5.3. Пороги ошибок

| Порог | Условие              | Действие                    |
| ----- | -------------------- | --------------------------- |
| Soft  | > 5% ошибок в батче  | WARNING в лог               |
| Hard  | > 20% ошибок в батче | `DataQualityThresholdError` |

### 5.4. Карантин

Записи, не прошедшие валидацию, отправляются в карантин:

```python
{
    "raw_record": {...},  # Исходная запись
    "error_code": "INVALID-STANDARD-VALUE",
    "error_details": "standard_value is negative",
    "batch_id": "uuid",
    "timestamp": "2025-12-19T10:30:00Z",
}
```

______________________________________________________________________

## 6. Запись в слои Medallion

### 6.1. Bronze Layer

**Файл:** `src/bioetl/infrastructure/storage/bronze_writer.py`

```
Путь: bronze/v1/chembl/activity/2025-12-19/batch-{uuid}.jsonl.zst
```

| Параметр       | Значение                    |
| -------------- | --------------------------- |
| **Формат**     | JSONL + Zstandard (level 3) |
| **Режим**      | Append-only                 |
| **Retention**  | 90 дней                     |
| **Chunk size** | 256 KB                      |

**Metadata sidecar** (`.meta.json`):

This legacy file-level sidecar is an operator-facing occurrence projection, not
an authoritative replay dossier. Exact replay/debug reconstruction must use the
immutable control-plane and lineage surfaces (`run_manifest`, canonical layer
metadata, lineage fragment, effective-config artifact, and ledger evidence)
instead of treating `.meta.json` as standalone source of truth.

```json
{
    "run_id": "uuid",
    "run_type": "incremental",
    "ingestion_ts": "2025-12-19T10:30:00Z",
    "provider": "chembl",
    "entity": "activity",
    "batch_id": "uuid"
}
```

______________________________________________________________________

### 6.2. Silver Layer

**Файл:** `src/bioetl/infrastructure/storage/silver_writer.py`

**PyArrow Schema** (`src/bioetl/infrastructure/schemas/silver.py`):

```python
CHEMBL_ACTIVITY_SCHEMA = pa.schema(
    [
        pa.field("entity_id", pa.string()),
        pa.field("content_hash", pa.string()),
        pa.field("activity_id", pa.string()),
        pa.field("molecule_id", pa.string()),
        pa.field("target_id", pa.string()),
        pa.field("assay_id", pa.string()),
        pa.field("publication_id", pa.string()),
        pa.field("publication_doi", pa.string()),
        pa.field("publication_pmid", pa.string()),
        pa.field("publication_pmc_id", pa.string()),
        pa.field("journal", pa.string()),
        pa.field("publication_year", pa.int64()),
        pa.field("standard_type", pa.string()),
        pa.field("standard_value", pa.float64()),
        pa.field("standard_units", pa.string()),
        pa.field("pchembl_value", pa.float64()),
        pa.field("_source", pa.string()),
        pa.field("_index", pa.int64()),
        # ... всего 77 полей (включая action_type* и ontology companion fields)
    ]
)
```

| Параметр                 | Значение                                             |
| ------------------------ | ---------------------------------------------------- |
| **Формат**               | Delta Lake                                           |
| **Режим записи**         | `merge` (active pipeline config)                     |
| **Бизнес-ключ**          | `activity_id`                                        |
| **Партиционирование**    | Не задано в активном entity config                   |
| **Приоритет конфликтов** | REBUILD > BACKFILL > INCREMENTAL (run_type metadata) |

______________________________________________________________________

### 6.3. Gold Layer

`chembl_activity` writes both Silver and Gold surfaces in the active runtime
config. The active entity config keeps the Gold sink enabled and the published
Gold contract/export artifacts below describe an emitted runtime surface rather
than a reference-only placeholder.

| Параметр     | Значение                                                                                                 |
| ------------ | -------------------------------------------------------------------------------------------------------- |
| **Статус**   | Enabled in `configs/entities/chembl/activity.yaml`                                                       |
| **Причина**  | Активный pipeline config публикует Gold sink и Gold writer                                               |
| **Контракт** | Gold contract exports соответствуют active emitted surface                                                |

______________________________________________________________________

## 7. Полный поток данных

```
ChEMBL API (/activity.json)
         │
         ▼
┌─────────────────────────────────────────┐
│  BRONZE (сырые данные)                  │
│  ─────────────────────────────────────  │
│  • Путь: bronze/v1/chembl/activity/...  │
│  • Формат: JSONL + Zstandard            │
│  • Режим: Append-only                   │
│  • Retention: 90 дней                   │
└─────────────────────────────────────────┘
         │
         ▼ ActivityTransformer.transform()
         │
         ├── DQ Error? ──► QUARANTINE
         │                   │
         ▼                   ▼
┌─────────────────────────────────────────┐
│  SILVER (нормализованные данные)        │
│  ─────────────────────────────────────  │
│  • Формат: Delta Lake                   │
│  • Append mode; business key = activity_id │
│  • Schema: 62 поля (PyArrow)            │
│  • Gold stage enabled in active config  │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  GOLD                                   │
│  ─────────────────────────────────────  │
│  • Enabled for `chembl_activity`        │
│  • Gold filters and Gold writer active  │
│  • Current terminal output: Gold-ready  │
└─────────────────────────────────────────┘
```

______________________________________________________________________

## 8. Результат обработки батча

```python
@dataclass
class BatchResult:
    bronze_count: int  # Записей в Bronze
    silver_count: int  # Успешно трансформировано
    quarantined_count: int  # Отправлено в карантин
```

______________________________________________________________________

## 9. Инкрементальная загрузка

Отдельный watermark-модуль удалён (см. ADR-011). Инкрементальность обеспечивается
через `run_type`, checkpoints и идемпотентный merge по ключам/хешу.

______________________________________________________________________

## 10. Связанные файлы

| Компонент     | Путь                                                                         |
| ------------- | ---------------------------------------------------------------------------- |
| Конфигурация  | `configs/entities/chembl/activity.yaml`                                      |
| Сущность      | `src/bioetl/domain/entities/bioactivity/_entity.py`                          |
| Трансформер   | `src/bioetl/application/pipelines/chembl/activity_transformer.py`            |
| Gold sink     | Enabled in `configs/entities/chembl/activity.yaml`                           |
| Pipeline defs | `src/bioetl/application/pipelines/chembl/pipeline_types.py`                  |
| Silver Schema | `src/bioetl/infrastructure/schemas/silver.py`                                |
| Bronze Writer | `src/bioetl/infrastructure/storage/bronze_writer.py`                         |
| Silver Writer | `src/bioetl/infrastructure/storage/silver_writer.py`                         |
| Gold Writer   | Used by the active `chembl_activity` pipeline                                |
| Data Contract | `src/bioetl/domain/contracts/gold/` (canonical source for generated exports) |

______________________________________________________________________

## 11. Пример использования CLI

```bash
# Инкрементальная загрузка (по умолчанию)
bioetl run --pipeline chembl_activity

# С ограничением количества записей
bioetl run --pipeline chembl_activity --limit 1000

# Backfill за период
bioetl run --pipeline chembl_activity --run-type backfill

# Полная перезагрузка
bioetl run --pipeline chembl_activity --run-type rebuild
```

______________________________________________________________________

## Contract References

| Артефакт             | Ссылка                                                                                   |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Gold contract export | [chembl_activity_v1.0.json](../../contracts/gold/chembl_activity_v1.0.json)              |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                       |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

______________________________________________________________________

## Compliance

| Контроль          | Статус         | Evidence                                                                                      |
| ----------------- | -------------- | --------------------------------------------------------------------------------------------- |
| Metadata          | Pass           | YAML header содержит `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified`      |
| Runtime alignment | Pass           | Активный runtime и config surface описаны в разделах `Конфигурация` и `Связанные файлы`       |
| Contract linkage  | Pass           | [chembl_activity_v1.0.json](../../contracts/gold/chembl_activity_v1.0.json)                   |
| API governance    | Pass           | См. [API Compliance](#api-compliance)                                                         |
| Contract note     | Active runtime surface | Gold export соответствует active config и emitted pipeline surface |

______________________________________________________________________

## API Compliance

### Rate limits & retries

Официальная ChEMBL REST Web Services documentation не публикует числовой лимит запросов. EMBL-EBI Terms of Use разрешают ограничивать или отзывать доступ, если использование мешает работе сервиса. Клиент SHOULD использовать консервативный rate limiting и экспоненциальный backoff; точный retry budget — [неуточнено].

### 429 handling policy

Явная HTTP 429 policy в доступной официальной документации ChEMBL — [неуточнено]. При признаках throttling или блокировки клиент SHOULD снижать частоту запросов и прекращать burst-нагрузку.

### Authentication model

Read-only web services документированы как открытые REST endpoints; обязательная аутентификация для чтения в официальной документации не указана.

### ToS URL

- https://www.ebi.ac.uk/about/terms-of-use

### Data license

ChEMBL data are available under the Creative Commons Attribution-ShareAlike 3.0 Unported license (CC BY-SA 3.0).

### Personal data notes

Наборы данных ChEMBL по своей природе не ориентированы на персональные данные. EMBL-EBI Privacy Notice описывает обработку служебных данных доступа и журналов безопасности; API-specific guidance по персональным данным — [неуточнено].

### Official sources

- [ChEMBL REST Web Services](https://www.ebi.ac.uk/chembl/api/data/docs)
- [ChEMBL homepage / license statement](https://www.ebi.ac.uk/chembl/)
- [EMBL-EBI Terms of Use](https://www.ebi.ac.uk/about/terms-of-use)
- [EMBL-EBI Privacy Notice](https://www.ebi.ac.uk/about/privacy-notice)

*Последнее обновление: 2026-03-30*
