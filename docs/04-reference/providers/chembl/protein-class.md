______________________________________________________________________

Version: 1.2.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# Пайплайн: ChEMBL Protein Class

**Имя пайплайна:** `chembl_protein_class`
**Провайдер:** `chembl`
**Сущность:** `protein_class`
**Версия схемы:** 1.2.0

______________________________________________________________________

## 1. Описание

Пайплайн извлекает иерархическую классификацию белков из API ChEMBL. Справочная таблица (~1,500 записей) содержит классы ферментов, типы рецепторов и другие категории белков. Используется для аннотации таргетов.

______________________________________________________________________

## 2. Ключевые поля

### Идентификаторы

| Поле               | Тип   | Описание                           |
| ------------------ | ----- | ---------------------------------- |
| `protein_class_id` | `int` | Уникальный идентификатор класса    |
| `parent_id`        | `int` | ID родительского класса (иерархия) |

### Иерархия

| Поле          | Тип   | Описание                         |
| ------------- | ----- | -------------------------------- |
| `class_level` | `int` | Уровень в иерархии (1 = корень)  |
| `sort_order`  | `int` | Порядок сортировки внутри уровня |

### Классификация

| Поле                 | Тип   | Описание                  |
| -------------------- | ----- | ------------------------- |
| `pref_name`          | `str` | Предпочтительное название |
| `short_name`         | `str` | Короткое название         |
| `protein_class_desc` | `str` | Описание класса           |
| `definition`         | `str` | Определение класса        |

### Метаданные

| Поле          | Тип   | Описание                     |
| ------------- | ----- | ---------------------------- |
| `downgraded`  | `int` | Флаг устаревшей записи (0/1) |
| `replaced_by` | `int` | ID заменяющего класса        |

______________________________________________________________________

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/protein_class_transformer.py`

### Entity ID

```python
entity_id = f"chembl:{protein_class_id}"
```

### Иерархическая структура

```
parent_id → protein_class_id
```

Корневые классы имеют `parent_id = None`.

______________________________________________________________________

## 4. Валидация

### DQ-правила

1. **`protein_class_id`** — обязательное (primary key)
1. **`pref_name`** — обязательное (название класса)

### Gold-фильтры

- Обязательные поля: `pref_name`
- Фильтр `downgraded = 0` — исключение устаревших записей

______________________________________________________________________

## 5. Использование CLI

```bash
# Полная загрузка (справочная таблица)
bioetl run --pipeline chembl_protein_class

# С ограничением
bioetl run --pipeline chembl_protein_class --limit 500
```

______________________________________________________________________

## 6. Стратегия загрузки

**Full load** — справочная таблица загружается полностью при каждом запуске. Входной фильтр отключён (`input_filter.enabled: false`).

______________________________________________________________________

## 7. Партиционирование

Silver-таблица партиционируется по полю `class_level` для оптимизации иерархических запросов.

Gold-таблица сортируется по `class_level`, `sort_order`, `protein_class_id`.

______________________________________________________________________

## 8. Связанные файлы

| Компонент     | Путь                                                                   |
| ------------- | ---------------------------------------------------------------------- |
| Конфигурация  | `configs/entities/chembl/protein_class.yaml`                           |
| Трансформер   | `src/bioetl/application/pipelines/chembl/protein_class_transformer.py` |
| Pipeline defs | `src/bioetl/application/pipelines/chembl/_pipelines.py`                |

______________________________________________________________________

## Contract References

| Артефакт             | Ссылка                                                                                   |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Gold contract export | [chembl_protein_class_v1.0.json](../../contracts/gold/chembl_protein_class_v1.0.json)    |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                       |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

## Compliance

| Контроль          | Статус | Evidence                                                                                                       |
| ----------------- | ------ | -------------------------------------------------------------------------------------------------------------- |
| Metadata          | Pass   | YAML header содержит `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified`                       |
| Runtime alignment | Pass   | Активный config/runtime surface задокументирован в разделах `Конфигурация`, `Трансформация`, `Связанные файлы` |
| Contract linkage  | Pass   | [chembl_protein_class_v1.0.json](../../contracts/gold/chembl_protein_class_v1.0.json)                          |
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
