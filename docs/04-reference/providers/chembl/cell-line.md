______________________________________________________________________

Version: 1.2.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# Пайплайн: ChEMBL Cell Line

**Имя пайплайна:** `chembl_cell_line`
**Провайдер:** `chembl`
**Сущность:** `cell_line`
**Версия схемы:** 1.2.0

______________________________________________________________________

## 1. Описание

Пайплайн извлекает данные о клеточных линиях из API ChEMBL. Клеточные линии — это биологические объекты, используемые для in vitro экспериментов. Они имеют связь M:N с сущностью Assay (через FK `assay.cell_id`).

**Источник данных:** ChEMBL REST API, таблица `cell_dictionary`

______________________________________________________________________

## 2. Ключевые поля

### Идентификаторы

| Поле        | Тип   | Описание                                     |
| ----------- | ----- | -------------------------------------------- |
| `cell_id`   | `str` | Уникальный ChEMBL ID клеточной линии (PK)    |
| `cell_name` | `str` | Название клеточной линии (напр., HeLa, MCF7) |

### Метаданные

| Поле               | Тип   | Описание                                      |
| ------------------ | ----- | --------------------------------------------- |
| `cell_description` | `str` | Описание клеточной линии                      |
| `cell_type`        | `str` | Тип клеточной линии (напр., Cancer cell line) |

### Источник

| Поле                      | Тип   | Описание                                |
| ------------------------- | ----- | --------------------------------------- |
| `cell_source_tissue`      | `str` | Ткань-источник (напр., Cervix, Breast)  |
| `cell_source_organism`    | `str` | Организм-источник (напр., Homo sapiens) |
| `cell_source_taxonomy_id` | `int` | NCBI Taxonomy ID организма-источника    |

### Внешние идентификаторы

| Поле             | Тип   | Описание                                                           |
| ---------------- | ----- | ------------------------------------------------------------------ |
| `cellosaurus_id` | `str` | Cellosaurus ID (формат: `CVCL_XXXX`)                               |
| `clo_id`         | `str` | Cell Line Ontology ID (формат: `CLO_XXXXX`)                        |
| `cl_lincs_id`    | `str` | LINCS ID (Library of Integrated Network-Based Cellular Signatures) |
| `efo_id`         | `str` | EFO ontology ID (формат: `EFO_XXXXX`)                              |

______________________________________________________________________

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/cell_line_transformer.py`

### Нормализация данных

- **cell_name:** Строка нормализуется через `normalize_to_string()` (strip whitespace)
- **cell_source_taxonomy_id:** Валидируется через `validate_positive_int()` (должен быть >= 1)
- **Внешние ID:** Пустые строки и whitespace преобразуются в `NULL`

### Entity ID

```python
entity_id = f"chembl:{cell_id}"
```

______________________________________________________________________

## 4. Валидация

### DQ-правила

1. **`cell_id`** — обязательное, формат `^CHEMBL\d+$`
1. **`cell_name`** — обязательное
1. **`cell_source_taxonomy_id`** — если указан, должен быть >= 1
1. **Внешние ID** — если указаны, валидируются по regex:
   - `cellosaurus_id`: `^CVCL_[A-Z0-9]+$`
   - `clo_id`: `^CLO_\d+$`
   - `efo_id`: `^EFO_\d+$`

### Пороги ошибок

| Порог | Условие      | Действие   |
| ----- | ------------ | ---------- |
| Soft  | > 5% ошибок  | WARNING    |
| Hard  | > 20% ошибок | FAIL BATCH |

______________________________________________________________________

## 5. Использование CLI

```bash
# Инкрементальная загрузка
bioetl run --pipeline chembl_cell_line

# С ограничением количества записей
bioetl run --pipeline chembl_cell_line --limit 500

# Полная перезагрузка
bioetl run --pipeline chembl_cell_line --run-type rebuild

# С входным фильтром по списку ID
bioetl run --pipeline chembl_cell_line --input-csv data/input/cell.csv
```

______________________________________________________________________

## 6. Связанные файлы

| Компонент     | Путь                                                               |
| ------------- | ------------------------------------------------------------------ |
| Конфигурация  | `configs/entities/chembl/cell_line.yaml`                           |
| Трансформер   | `src/bioetl/application/pipelines/chembl/cell_line_transformer.py` |
| Pipeline defs | `src/bioetl/application/pipelines/chembl/pipeline_types.py`        |
| Схема         | `src/bioetl/domain/schemas/chembl/cell_line.py`                    |
| Сущность      | `src/bioetl/domain/entities/chembl_structures_foundation.py`       |
| Фабрика       | `src/bioetl/composition/factories/pipeline/registry.py`            |

______________________________________________________________________

## 7. Связи с другими сущностями

```
Cell Line (cell_id)
    └── Assay (cell_id FK) [M:N]
        └── Activity [1:N]
```

______________________________________________________________________

## 8. Примеры данных

### Bronze (raw JSON)

```json
{
  "cell_chembl_id": "CHEMBL3308376",
  "cell_name": "HeLa",
  "cell_description": "Human cervical cancer cell line",
  "cell_source_tissue": "Cervix",
  "cell_source_organism": "Homo sapiens",
  "cell_source_tax_id": 9606,
  "cell_type": "Cancer cell line",
  "cellosaurus_id": "CVCL_0030",
  "clo_id": "CLO_0003684",
  "cl_lincs_id": "LCL-1234",
  "efo_id": "EFO_0001185"
}
```

### Silver (нормализованный)

| cell_id       | cell_name | cell_source_organism | cell_source_taxonomy_id | cellosaurus_id |
| ------------- | --------- | -------------------- | ----------------------- | -------------- |
| CHEMBL3308376 | HeLa      | Homo sapiens         | 9606                    | CVCL_0030      |

______________________________________________________________________

## Contract References

| Артефакт             | Ссылка                                                                                   |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Gold contract export | [chembl_cell_line_v1.0.json](../../contracts/gold/chembl_cell_line_v1.0.json)            |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                       |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

## Compliance

| Контроль          | Статус | Evidence                                                                                                        |
| ----------------- | ------ | --------------------------------------------------------------------------------------------------------------- |
| Metadata          | Pass   | YAML header содержит `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified`                        |
| Runtime alignment | Pass   | Активный config/runtime surface задокументирован в разделах `Конфигурация`, `Процесс (ETL)` и `Связанные файлы` |
| Contract linkage  | Pass   | [chembl_cell_line_v1.0.json](../../contracts/gold/chembl_cell_line_v1.0.json)                                   |
| API governance    | Pass   | См. [API Compliance](#api-compliance)                                                                           |

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
