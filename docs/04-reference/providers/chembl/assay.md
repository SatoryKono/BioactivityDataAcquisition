---
Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-29'
---

# Пайплайн: ChEMBL Assay

**Имя пайплайна:** `chembl_assay`
**Провайдер:** `chembl`
**Сущность:** `assay`

---

## 1. Что делает пайплайн

`chembl_assay` поднимает определения биоанализов из ChEMBL и нормализует их в
Silver-запись `Assay`. Источник поведения для текущей реализации:

- `configs/entities/chembl/assay.yaml`
- `src/bioetl/application/pipelines/chembl/assay_transformer.py`
- `src/bioetl/domain/entities/chembl_activity.py`
- `src/bioetl/infrastructure/schemas/silver_chembl_core.py`
- `src/bioetl/domain/schemas/chembl/assay.py`

---

## 2. Конфигурация

Текущий unified config использует следующие поверхности:

- `schema.column_groups`: `system`, `business`, `dq`
- `quality.entity_field_validations`: `assay_id`, `assay_type`, `confidence_score`, `relationship_type`
- `quality.entity_cross_field_validations`: `assay_id` + `description`
- `filters.extraction_params`:
  - `assay_type__in: B,F`
  - `confidence_score__gte: 8`
  - `relationship_type: D`
  - `target_chembl_id__isnull: false`
  - `src_id: 1`
- `filters.silver_filters.required_fields`:
  - `assay_id`
  - `assay_type`
  - `description`
  - `target_id`
- `filters.gold_filters`:
  - `assay_type in {B, F}`
  - `confidence_score in {8, 9}`
  - `relationship_type = D`

---

## 3. Silver surface

### 3.1. Обязательные поля контракта

В текущем коде и схемах для Silver жёстко отражены как не-null:

| Поле | Где закреплено |
|------|----------------|
| `assay_id` | YAML required + Arrow + Pandera |
| `assay_type` | YAML required + Arrow + Pandera |
| `description` | YAML required + Arrow + Pandera |
| `target_id` | YAML required + Arrow + Pandera |

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

Системные колонки добавляются runtime/base-transformer слоем:

- `entity_id`
- `content_hash`
- `_run_id`
- `_run_type`
- `_source_batch_id`
- `_ingestion_ts`
- `_index`

Документация не фиксирует буквальную формулу `entity_id`; текущая реализация
делегирует вычисление identity/hash в общий базовый transformer/service слой.

---

## 4. Как трансформер строит запись

`src/bioetl/application/pipelines/chembl/assay_transformer.py` делает следующее:

1. Поддерживает legacy alias: если пришёл `assay_chembl_id`, он подставляется в `assay_id`.
2. Маппит плоские поля через declarative field groups.
3. Разворачивает вложенный `variant_sequence` через `flatten_nested_dict()`.
4. Нормализует `assay_tax_id -> assay_taxonomy_id` и `variant_tax_id -> variant_taxonomy_id`.
5. Сериализует `variant_sequence`, `assay_classifications`, `assay_parameters` в JSON-строки.
6. Передаёт итоговые business fields в базовый ChEMBL transformer для вычисления identity, content hash и system fields.

---

## 5. Валидация

### 5.1. Arrow schema

Silver Arrow schema находится в
`src/bioetl/infrastructure/schemas/silver_chembl_core.py` как
`CHEMBL_ASSAY_SCHEMA`.

### 5.2. Pandera schema

Silver Pandera schema находится в
`src/bioetl/domain/schemas/chembl/assay.py` как `AssaySchema`.

Обе схемы отражают строковый surface для JSON-полей и non-null ограничения для
`assay_id`, `assay_type`, `description`, `target_id`.

---

## 6. Gold-поведение

Gold-отбор для текущего pipeline задаётся исключительно config-слоем:

- `assay_type in {B, F}`
- `confidence_score in {8, 9}`
- `relationship_type = D`

Если эти значения меняются, source of truth находится в
`configs/entities/chembl/assay.yaml`, а не в этой странице.

---

## 7. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/entities/chembl/assay.yaml` |
| Трансформер | `src/bioetl/application/pipelines/chembl/assay_transformer.py` |
| Сущность | `src/bioetl/domain/entities/chembl_activity.py` |
| Arrow schema | `src/bioetl/infrastructure/schemas/silver_chembl_core.py` |
| Pandera schema | `src/bioetl/domain/schemas/chembl/assay.py` |
| Pipeline defs | `src/bioetl/application/pipelines/chembl/_pipelines.py` |
| Gold contract export | `docs/04-reference/contracts/gold/chembl_assay_v1.0.json` |

---

## 8. CLI

```bash
bioetl run --pipeline chembl_assay
bioetl run --pipeline chembl_assay --limit 1000
bioetl run --pipeline chembl_assay --run-type rebuild
bioetl run --pipeline chembl_assay --input-csv data/input/assay.csv
```
