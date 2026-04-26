______________________________________________________________________

Version: 1.2.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# Пайплайн: ChEMBL Publication Term

**Имя пайплайна:** `chembl_publication_term`
**Провайдер:** `chembl`
**Сущность:** `publication_term`
**Версия схемы:** 1.2.0

______________________________________________________________________

## 1. Описание

Пайплайн извлекает термины (MeSH-дескрипторы, ключевые слова) из записей публикаций ChEMBL API. Это производная сущность — извлекает вложенные данные терминов из ответов API `/document` и преобразует связь 1:M (одна публикация → множество терминов) в плоскую структуру.

**Типы терминов:**

- `MESH_HEADING` — MeSH-дескрипторы
- `MESH_QUALIFIER` — MeSH-квалификаторы/подзаголовки
- `KEYWORD` — Ключевые слова, заданные авторами
- `CONCEPT` — ChEMBL-derived concept terms

______________________________________________________________________

## 2. Ключевые поля

### Композитный ключ

| Поле             | Тип   | Описание                                                    |
| ---------------- | ----- | ----------------------------------------------------------- |
| `publication_id` | `str` | FK → ChEMBL ID родительской публикации                      |
| `term`           | `str` | Текст термина (напр., "Aspirin", "kinase inhibitor")        |
| `term_type`      | `str` | Тип термина: MESH_HEADING, MESH_QUALIFIER, KEYWORD, CONCEPT |

### MeSH-специфичные поля

| Поле        | Тип           | Описание                                  |
| ----------- | ------------- | ----------------------------------------- |
| `mesh_id`   | `str \| None` | MeSH идентификатор (напр., "D001241")     |
| `qualifier` | `str \| None` | MeSH квалификатор (напр., "pharmacology") |

______________________________________________________________________

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/publication_term_transformer.py`

### Entity ID

Entity ID вычисляется как SHA256-хэш композитного ключа:

```python
composite = f"{publication_id}:{term_type}:{normalized_term}"
entity_id = hashlib.sha256(composite.encode()).hexdigest()[:16]
```

**Нормализация термина:** `term` проходит profile `normalize_profile_title`.
`term_type` нормализуется через общий enum source `configs/enums/chembl.yaml`
и schema constant `PUBLICATION_TERM_TYPES`; lowercase и пробельные варианты
канонизируются к одному из `MESH_HEADING`, `MESH_QUALIFIER`, `KEYWORD`,
`CONCEPT`, а неизвестные значения схлопываются в `None` и затем ловятся
DQ/schema контрактом.

### Извлечение терминов

Трансформер извлекает термины из двух полей публикации:

1. `mesh_terms` — массив MeSH-терминов (heading + qualifier)
1. `keywords` — массив ключевых слов авторов

______________________________________________________________________

## 4. Валидация

### DQ-правила

1. **`publication_id`** — обязательное, формат `CHEMBL\d+`
1. **`term`** — обязательное, минимум 1 символ
1. **`term_type`** — обязательное, одно из: MESH_HEADING, MESH_QUALIFIER, KEYWORD, CONCEPT

### Gold-фильтры

```yaml
gold_filters:
  columns:
    term_type: [MESH_HEADING, MESH_QUALIFIER, KEYWORD, CONCEPT]
  required_fields:
    - publication_id
    - term
    - term_type
```

______________________________________________________________________

## 5. Использование CLI

```bash
# Инкрементальная загрузка
bioetl run --pipeline chembl_publication_term

# С ограничением
bioetl run --pipeline chembl_publication_term --limit 1000

# С фильтрацией по публикациям
bioetl run --pipeline chembl_publication_term --input-csv data/input/publication.csv
```

______________________________________________________________________

## 6. Партиционирование

Silver-таблица партиционирована по `term_type` для эффективных запросов по типу термина.

```yaml
sink:
  silver:
    partition_by: ["term_type"]
```

______________________________________________________________________

## 7. Связанные файлы

| Компонент     | Путь                                                                      |
| ------------- | ------------------------------------------------------------------------- |
| Конфигурация  | `configs/entities/chembl/publication_term.yaml`                           |
| Трансформер   | `src/bioetl/application/pipelines/chembl/publication_term_transformer.py` |
| Pipeline defs | `src/bioetl/application/pipelines/chembl/_pipelines.py`                   |
| Сущность      | `src/bioetl/domain/entities/chembl_structures.py` (PublicationTerm)       |
| Схема         | `src/bioetl/domain/schemas/chembl/publication_term.py`                    |

______________________________________________________________________

## 8. Связь с родительской сущностью

`chembl_publication_term` — производная от `chembl_publication`. Для полного покрытия рекомендуется сначала загрузить публикации:

```bash
bioetl run --pipeline chembl_publication --limit 100
bioetl run --pipeline chembl_publication_term --limit 1000
```

______________________________________________________________________

## Contract References

| Артефакт             | Ссылка                                                                                      |
| -------------------- | ------------------------------------------------------------------------------------------- |
| Gold contract export | [chembl_publication_term_v1.0.json](../../contracts/gold/chembl_publication_term_v1.0.json) |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                          |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md)    |

## Compliance

| Контроль          | Статус | Evidence                                                                                                       |
| ----------------- | ------ | -------------------------------------------------------------------------------------------------------------- |
| Metadata          | Pass   | YAML header содержит `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified`                       |
| Runtime alignment | Pass   | Активный config/runtime surface задокументирован в разделах `Конфигурация`, `Трансформация`, `Связанные файлы` |
| Contract linkage  | Pass   | [chembl_publication_term_v1.0.json](../../contracts/gold/chembl_publication_term_v1.0.json)                    |
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
