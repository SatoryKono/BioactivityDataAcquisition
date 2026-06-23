______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# Пайплайн: ChEMBL Tissue

**Имя пайплайна:** `chembl_tissue`
**Провайдер:** `chembl`
**Сущность:** `tissue`
**Версия схемы:** 1.0.0

______________________________________________________________________

## 1. Описание

Пайплайн извлекает данные о тканях и анатомических локациях из API ChEMBL. Ткани используются как контекст для описания условий экспериментов (assays). Сущность Tissue имеет связь 1:N с Assay (через FK `assay.tissue_id`).

**Источник данных:** ChEMBL REST API, эндпоинт `/tissue`

______________________________________________________________________

## 2. Ключевые поля

### Идентификаторы

| Поле        | Тип   | Описание                                            |
| ----------- | ----- | --------------------------------------------------- |
| `tissue_id` | `str` | Уникальный ChEMBL ID ткани (PK, формат `CHEMBL\d+`) |
| `pref_name` | `str` | Предпочтительное название ткани                     |

### Онтологические ссылки

| Поле        | Тип   | Описание                                              |
| ----------- | ----- | ----------------------------------------------------- |
| `bto_id`    | `str` | Brenda Tissue Ontology ID (формат: `BTO_0000000`)     |
| `caloha_id` | `str` | CALIPHO tissue ID (формат: `TS-0000`)                 |
| `efo_id`    | `str` | EFO ontology ID (формат: `EFO_0000000`)               |
| `uberon_id` | `str` | UBERON anatomy ontology ID (формат: `UBERON_0000000`) |

______________________________________________________________________

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/tissue_transformer.py`

### Нормализация данных

- **pref_name:** canonical text/title cleanup
- **Онтологические ID:** входные alias формы вроде `bto:0000068` нормализуются к
  canonical underscore form `BTO_0000068`
- **Companion bundle:** `*_iri`, `*_mapping_status`, `*_ontology_version`
  резолвятся из sibling normalized ontology IDs
- **tissue_id:** валидируется через regex `^CHEMBL\d+$`

### Entity ID

`entity_id` остаётся техническим runtime field. Governance-significant business
identity для ткани задаётся `tissue_id`; ontology IDs влияют на content-hash и
DQ, но не заменяют primary business key.

______________________________________________________________________

## 4. Валидация

### DQ-правила

1. **`tissue_id`** — обязательное, формат `^CHEMBL\d+$`
1. **`pref_name`** — обязательное, длина 1-200 символов
1. **`bto_id`** — если указан, формат `^BTO_\d{7}$`
1. **`caloha_id`** — если указан, формат `^TS-\d{4}$`
1. **`efo_id`** — если указан, формат `^EFO_\d{7}$`
1. **`uberon_id`** — если указан, формат `^UBERON_\d{7}$`

### Пороги ошибок

| Порог | Условие      | Действие   |
| ----- | ------------ | ---------- |
| Soft  | > 5% ошибок  | WARNING    |
| Hard  | > 20% ошибок | FAIL BATCH |

______________________________________________________________________

## 5. Использование CLI

```bash
# Инкрементальная загрузка
bioetl run --pipeline chembl_tissue

# С ограничением количества записей
bioetl run --pipeline chembl_tissue --limit 500

# Полная перезагрузка
bioetl run --pipeline chembl_tissue --run-type rebuild
```

______________________________________________________________________

## 6. Связанные файлы

| Компонент    | Путь                                                            |
| ------------ | --------------------------------------------------------------- |
| Конфигурация | `configs/entities/chembl/tissue.yaml`                           |
| DQ Rules     | `configs/entities/chembl/tissue.yaml#quality`                   |
| Схема        | `configs/entities/chembl/tissue.yaml`                           |
| Трансформер  | `src/bioetl/application/pipelines/chembl/tissue_transformer.py` |

______________________________________________________________________

## 7. Связи с другими сущностями

```
Tissue (tissue_id)
    └── Assay (tissue_id FK) [1:N]
        └── Activity [1:N]
```

______________________________________________________________________

## 8. Примеры данных

### Bronze (raw JSON)

```json
{
  "tissue_id": "CHEMBL3638186",
  "pref_name": "Liver",
  "bto_id": "BTO:0000759",
  "caloha_id": "TS-0564",
  "efo_id": "EFO:0000887",
  "uberon_id": "UBERON:0002107"
}
```

`tissue_chembl_id` is still accepted as a legacy source alias, but the active
normalized contract publishes this field as `tissue_id`.

### Silver (нормализованный)

| tissue_id     | pref_name | bto_id      | uberon_id      |
| ------------- | --------- | ----------- | -------------- |
| CHEMBL3638186 | Liver     | BTO_0000759 | UBERON_0002107 |

______________________________________________________________________

## Contract References

| Артефакт             | Ссылка                                                                                   |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Gold contract export | [chembl_tissue_v1.0.json](../../contracts/gold/chembl_tissue_v1.0.json)                  |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                       |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

## Compliance

| Контроль          | Статус | Evidence                                                                                                       |
| ----------------- | ------ | -------------------------------------------------------------------------------------------------------------- |
| Metadata          | Pass   | YAML header содержит `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified`                       |
| Runtime alignment | Pass   | Активный config/runtime surface задокументирован в разделах `Конфигурация`, `Трансформация`, `Связанные файлы` |
| Contract linkage  | Pass   | [chembl_tissue_v1.0.json](../../contracts/gold/chembl_tissue_v1.0.json)                                        |
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
