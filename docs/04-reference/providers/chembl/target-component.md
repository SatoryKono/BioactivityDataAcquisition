______________________________________________________________________

Version: 1.2.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# Пайплайн: ChEMBL Target Component

**Имя пайплайна:** `chembl_target_component`
**Провайдер:** `chembl`
**Сущность:** `target_component`
**Версия схемы:** 1.2.0

______________________________________________________________________

## 1. Описание

Пайплайн извлекает данные о компонентах мишеней из API ChEMBL. Компоненты мишеней — это отдельные белки или субъединицы, входящие в состав сложных мишеней.

______________________________________________________________________

## 2. Ключевые поля

### Идентификаторы

| Поле             | Тип   | Описание                       |
| ---------------- | ----- | ------------------------------ |
| `component_id`   | `int` | Уникальный ID компонента       |
| `accession`      | `str` | UniProt accession              |
| `component_type` | `str` | Тип компонента (PROTEIN, etc.) |

### Описание

| Поле          | Тип   | Описание                          |
| ------------- | ----- | --------------------------------- |
| `description` | `str` | Описание компонента               |
| `sequence`    | `str` | Аминокислотная последовательность |

### Таксономия

| Поле          | Тип   | Описание         |
| ------------- | ----- | ---------------- |
| `organism`    | `str` | Организм         |
| `taxonomy_id` | `int` | NCBI Taxonomy ID |

### Классификация белков

| Поле                      | Тип          | Описание                |
| ------------------------- | ------------ | ----------------------- |
| `protein_classifications` | `list[dict]` | Классификация по ChEMBL |

`target_component_xrefs` persists as a canonical JSON string surface in Silver,
and nested `xref_src_db` namespaces are validated against the shared registry
`configs/vocab/chembl_reference_sources.yaml`.

______________________________________________________________________

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/target_component_transformer.py`

### Entity ID

```python
entity_id = f"chembl:{component_id}"
```

______________________________________________________________________

## 4. Использование CLI

```bash
# Инкрементальная загрузка
bioetl run --pipeline chembl_target_component

# С ограничением
bioetl run --pipeline chembl_target_component --limit 500
```

______________________________________________________________________

## 5. Связанные файлы

| Компонент    | Путь                                                                      |
| ------------ | ------------------------------------------------------------------------- |
| Конфигурация | `configs/entities/chembl/target_component.yaml`                           |
| Трансформер  | `src/bioetl/application/pipelines/chembl/target_component_transformer.py` |

______________________________________________________________________

## Contract References

| Артефакт             | Ссылка                                                                                      |
| -------------------- | ------------------------------------------------------------------------------------------- |
| Gold contract export | [chembl_target_component_v1.0.json](../../contracts/gold/chembl_target_component_v1.0.json) |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                          |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md)    |

## Compliance

| Контроль          | Статус | Evidence                                                                                                       |
| ----------------- | ------ | -------------------------------------------------------------------------------------------------------------- |
| Metadata          | Pass   | YAML header содержит `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified`                       |
| Runtime alignment | Pass   | Активный config/runtime surface задокументирован в разделах `Конфигурация`, `Трансформация`, `Связанные файлы` |
| Contract linkage  | Pass   | [chembl_target_component_v1.0.json](../../contracts/gold/chembl_target_component_v1.0.json)                    |
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
