______________________________________________________________________

Version: 1.2.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# Пайплайн: ChEMBL Assay Parameters

**Имя пайплайна:** `chembl_assay_parameters`
**Провайдер:** `chembl`
**Сущность:** `assay_parameters`
**Версия схемы:** 1.2.0

______________________________________________________________________

## 1. Описание

Пайплайн извлекает данные о параметрах экспериментальных анализов из API ChEMBL. Параметры включают условия эксперимента: концентрации, температуру, pH, время инкубации и другие экспериментальные переменные.

______________________________________________________________________

## 2. Ключевые поля

### Идентификаторы

| Поле             | Тип   | Описание                           |
| ---------------- | ----- | ---------------------------------- |
| `assay_param_id` | `int` | Уникальный идентификатор параметра |
| `assay_id`       | `str` | ChEMBL ID связанного анализа       |

### Тип параметра

| Поле   | Тип   | Описание                                    |
| ------ | ----- | ------------------------------------------- |
| `type` | `str` | Тип параметра (нормализованный к uppercase) |

**Известные типы параметров:**

- `CONC` — концентрация
- `PH` — кислотность
- `TEMP` — температура
- `TIME` — время
- `CELL_COUNT` — количество клеток
- `SERUM` — сыворотка
- `DOSE` — доза
- `VOLUME` — объём
- `WAVELENGTH` — длина волны
- `PERCENT` — процент
- `PRESSURE` — давление
- `HUMIDITY` — влажность
- `PASSAGE` — пассаж
- `CELL_DENSITY` — плотность клеток
- `INCUBATION` — инкубация

### Сырые значения

| Поле         | Тип     | Описание                   |
| ------------ | ------- | -------------------------- |
| `value`      | `float` | Числовое значение          |
| `text_value` | `str`   | Текстовое значение         |
| `relation`   | `str`   | Отношение (=, \<, >, etc.) |
| `units`      | `str`   | Единицы измерения          |
| `comments`   | `str`   | Комментарии                |

### Стандартизированные значения

| Поле                  | Тип     | Описание                               |
| --------------------- | ------- | -------------------------------------- |
| `standard_value`      | `float` | Стандартизированное числовое значение  |
| `standard_text_value` | `str`   | Стандартизированное текстовое значение |
| `standard_type`       | `str`   | Стандартизированный тип                |
| `standard_relation`   | `str`   | Стандартизированное отношение          |
| `standard_units`      | `str`   | Стандартизированные единицы            |

### Optional unit ontology companion bundle

`chembl_assay_parameters` now exposes additive nullable ontology companion
fields that mirror the reviewed shape used by `chembl_activity` when
provider/runtime context publishes unit ontology metadata:

- `uo_units`, `uo_unit_iri`, `uo_unit_mapping_status`, `uo_ontology_version`
- `qudt_units`, `qudt_unit_iri`, `qudt_unit_mapping_status`, `qudt_ontology_version`

`standard_units` remains the authoritative token-level analytical surface; the
ontology sidecars extend traceability and DQ without replacing the historical
unit-token contract.

______________________________________________________________________

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/assay_parameters_transformer.py`

### Entity ID

```python
entity_id = f"chembl:{assay_param_id}"
```

### Нормализация типа

```python
type = param_type.upper() if param_type else "UNKNOWN"
```

______________________________________________________________________

## 4. Валидация

### DQ-правила

1. **`assay_param_id`** — обязательное (primary key)
1. **`assay_id`** — обязательное (foreign key)
1. **`type`** — обязательное

### Gold-фильтры

- Обязательные поля: `assay_id`, `type`

______________________________________________________________________

## 5. Использование CLI

```bash
# Инкрементальная загрузка
bioetl run --pipeline chembl_assay_parameters

# С ограничением
bioetl run --pipeline chembl_assay_parameters --limit 1000

# С входным фильтром
bioetl run --pipeline chembl_assay_parameters --input-csv data/input/assay_parameters.csv
```

______________________________________________________________________

## 6. Партиционирование

Silver-таблица партиционируется по полю `type` для оптимизации запросов по типу параметра.

______________________________________________________________________

## 7. Связанные файлы

| Компонент     | Путь                                                                      |
| ------------- | ------------------------------------------------------------------------- |
| Конфигурация  | `configs/entities/chembl/assay_parameters.yaml`                           |
| Трансформер   | `src/bioetl/application/pipelines/chembl/assay_parameters_transformer.py` |
| Pipeline defs | `src/bioetl/application/pipelines/chembl/_pipelines.py`                   |

______________________________________________________________________

## Contract References

| Артефакт             | Ссылка                                                                                      |
| -------------------- | ------------------------------------------------------------------------------------------- |
| Gold contract export | [chembl_assay_parameters_v1.0.json](../../contracts/gold/chembl_assay_parameters_v1.0.json) |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                          |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md)    |

## Compliance

| Контроль          | Статус | Evidence                                                                                                       |
| ----------------- | ------ | -------------------------------------------------------------------------------------------------------------- |
| Metadata          | Pass   | YAML header содержит `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified`                       |
| Runtime alignment | Pass   | Активный config/runtime surface задокументирован в разделах `Конфигурация`, `Трансформация`, `Связанные файлы` |
| Contract linkage  | Pass   | [chembl_assay_parameters_v1.0.json](../../contracts/gold/chembl_assay_parameters_v1.0.json)                    |
| API governance    | Pass   | См. [API Compliance](#api-compliance)                                                                          |

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
