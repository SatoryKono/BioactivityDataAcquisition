______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-31'

______________________________________________________________________

# Пайплайн: ChEMBL Assay

**Имя пайплайна:** `chembl_assay`
**Провайдер:** `chembl`
**Сущность:** `assay`

______________________________________________________________________

## 1. Что делает пайплайн

`chembl_assay` поднимает определения биоанализов из ChEMBL и нормализует их в
Silver-запись `Assay`. Источник поведения для текущей реализации:

- `configs/entities/chembl/assay.yaml`
- `src/bioetl/application/pipelines/chembl/assay_transformer.py`
- `src/bioetl/domain/entities/chembl_activity.py`
- `src/bioetl/infrastructure/schemas/silver_chembl_core.py`
- `src/bioetl/domain/schemas/chembl/assay.py`

______________________________________________________________________

## 2. Конфигурация

Текущий unified config использует следующие поверхности:

- `schema.column_groups`: `system`, `business`, `dq`
- `quality.entity_field_validations`: `assay_id`, `assay_type`, `confidence_score`, `relationship_type`
- `quality.entity_cross_field_validations`: `assay_id` + `assay_description`
- `filters.extraction_params`:
  - `assay_type__in: B,F`
  - `confidence_score__gte: 8`
  - `relationship_type: D`
  - `target_chembl_id__isnull: false`
  - `src_id: 1`
- `filters.silver_filters.required_fields`:
  - `assay_id`
  - `assay_type`
  - `assay_description`
  - `target_id`
  - `publication_id`
  - `bao_format`
  - `assay_type_description`
  - `relationship_type`
  - `confidence_score`
- `filters.gold_filters`:
  - `assay_type in {B, F}`
  - `confidence_score in {8, 9}`
  - `relationship_type = D`

______________________________________________________________________

## 3. Silver surface

### 3.1. Обязательные поля контракта

В текущем коде и схемах для Silver жёстко отражены как не-null:

| Поле                     | Где закреплено                  |
| ------------------------ | ------------------------------- |
| `assay_id`               | YAML required + Arrow + Pandera |
| `assay_type`             | YAML required + Arrow + Pandera |
| `assay_description`      | YAML required + Arrow + Pandera |
| `target_id`              | YAML required + Arrow + Pandera |
| `publication_id`         | YAML required + Arrow + Pandera |
| `bao_format`             | YAML required + Arrow + Pandera |
| `assay_type_description` | YAML required + Pandera         |
| `relationship_type`      | YAML required + Pandera         |
| `confidence_score`       | YAML required + Pandera         |

### 3.2. Дополнительные бизнес-поля

Трансформер также маппит и/или нормализует:

- идентификаторы: `publication_id`, `cell_id`, `tissue_id`, `src_id`, `src_assay_id`, `aidx`
- классификацию: `assay_type_description`, `assay_category`, `assay_test_type`, `assay_group`
- биологический контекст: `assay_organism`, `assay_taxonomy_id`, `assay_cell_type`, `assay_tissue`, `assay_strain`, `assay_subcellular_fraction`
- качество: `confidence_score`, `confidence_description`, `relationship_type`, `relationship_description`, `assay_pref_name`, `score`
- variant-поля: `variant_accession`, `variant_isoform`, `variant_mutation`, `variant_organism`, `variant_sequence`, `variant_taxonomy_id`

### 3.3. JSON-строки

В Silver complex-поля сериализуются как строки:

- `assay_classifications`
- `assay_parameters`
- `variant_sequence_json`

Это поведение задаётся непосредственно в `AssayTransformer`, а Arrow/Pandera
схемы ожидают строковый surface, а не вложенные `list`/`dict`.

### 3.4. Системные поля

Persisted system columns для Silver/Gold row contract:

- `entity_id`
- `content_hash`
- `_source`
- `_index`

Документация не фиксирует буквальную формулу `entity_id`; текущая реализация
делегирует вычисление identity/hash в общий базовый transformer/service слой.
Occurrence-scoped provenance (`_run_id`, `_run_type`, `_source_batch_id`,
`_ingestion_ts`) публикуется отдельно через sidecar/control-plane artifacts.

______________________________________________________________________

## 4. Как трансформер строит запись

`src/bioetl/application/pipelines/chembl/assay_transformer.py` делает следующее:

1. Поддерживает legacy alias: если пришёл `assay_chembl_id`, он подставляется в `assay_id`.
1. Маппит плоские поля через declarative field groups.
1. Разворачивает вложенный `variant_sequence` через `flatten_nested_dict()`.
1. Нормализует `assay_tax_id -> assay_taxonomy_id` и `variant_tax_id -> variant_taxonomy_id`.
1. Канонизирует `bao_format` в форму `BAO_########`.
1. Нормализует `bao_label` по evidence-backed BAO mapping, а при неизвестном формате делает trim/lowercase passthrough.
1. Нормализует `assay_organism` как display field: trim, whitespace collapse, удаление trailing strain annotations.
1. Сериализует `variant_sequence`, `assay_classifications`, `assay_parameters` в JSON-строки.
1. Передаёт итоговые business fields в базовый ChEMBL transformer для вычисления identity, content hash и system fields.

______________________________________________________________________

## 5. Валидация

### 5.1. Arrow schema

Silver Arrow schema находится в
`src/bioetl/infrastructure/schemas/silver_chembl_core.py` как
`CHEMBL_ASSAY_SCHEMA`.

### 5.2. Pandera schema

Silver Pandera schema находится в
`src/bioetl/domain/schemas/chembl/assay.py` как `AssaySchema`.

Обе схемы отражают строковый surface для JSON-полей. Pandera schema также
закрепляет non-null ограничения для:

- `assay_id`
- `assay_type`
- `assay_description`
- `target_id`
- `publication_id`
- `bao_format`
- `assay_type_description`
- `relationship_type`
- `confidence_score`

______________________________________________________________________

## 6. Gold-поведение

Gold-отбор для текущего pipeline задаётся исключительно config-слоем:

- `assay_type in {B, F}`
- `confidence_score in {8, 9}`
- `relationship_type = D`
- `src_id = 1`
- `assay_test_type in {In vitro, empty}`
- `assay_strain is empty`
- `bao_format != BAO_0000218`

Gold-filter применяется к канонической Silver-записи, поэтому в required-field
gate используется `assay_description`. Legacy field `description` публикуется
только после `transform_for_gold()`.

Для `assay_test_type` empty-state в runtime обычно представлен как `None`
после normalization, а не как буквальная строка `""`.
Семантические правила из `silver_filters` по текущей compatibility policy
auto-promote'ятся в effective Gold gate.

Если эти значения меняются, source of truth находится в
`configs/entities/chembl/assay.yaml`, а не в этой странице.

______________________________________________________________________

## 7. Связанные файлы

| Компонент            | Путь                                                           |
| -------------------- | -------------------------------------------------------------- |
| Конфигурация         | `configs/entities/chembl/assay.yaml`                           |
| Трансформер          | `src/bioetl/application/pipelines/chembl/assay_transformer.py` |
| Сущность             | `src/bioetl/domain/entities/chembl_activity.py`                |
| Arrow schema         | `src/bioetl/infrastructure/schemas/silver_chembl_core.py`      |
| Pandera schema       | `src/bioetl/domain/schemas/chembl/assay.py`                    |
| Pipeline defs        | `src/bioetl/application/pipelines/chembl/_pipelines.py`        |
| Gold contract export | `docs/04-reference/contracts/gold/chembl_assay_v1.0.json`      |

______________________________________________________________________

## 8. CLI

```bash
bioetl run --pipeline chembl_assay
bioetl run --pipeline chembl_assay --limit 1000
bioetl run --pipeline chembl_assay --run-type rebuild
bioetl run --pipeline chembl_assay --input-csv data/input/assay.csv
```

## Contract References

| Артефакт             | Ссылка                                                                                   |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Gold contract export | [chembl_assay_v1.0.json](../../contracts/gold/chembl_assay_v1.0.json)                    |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                       |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

## Compliance

| Контроль          | Статус | Evidence                                                                                 |
| ----------------- | ------ | ---------------------------------------------------------------------------------------- |
| Metadata          | Pass   | YAML header содержит `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified` |
| Runtime alignment | Pass   | Runtime surface закреплён в `Конфигурация`, `Silver surface`, `Gold-поведение`           |
| Contract linkage  | Pass   | [chembl_assay_v1.0.json](../../contracts/gold/chembl_assay_v1.0.json)                    |
| API governance    | Pass   | См. [API Compliance](#api-compliance)                                                    |

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
