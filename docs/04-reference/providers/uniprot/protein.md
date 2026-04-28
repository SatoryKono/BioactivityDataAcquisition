______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-28'

______________________________________________________________________

# Пайплайн: UniProt Protein

**Имя пайплайна:** `uniprot_protein`
**Провайдер:** `uniprot`
**Сущность:** `protein`

## 1. Описание

Этот пайплайн извлекает данные о белках (`protein`) из API UniProt.

## 2. Конфигурация

**Источник конфигурации:** `configs/entities/uniprot/protein.yaml`

| Параметр                | Значение          | Описание                                  |
| ----------------------- | ----------------- | ----------------------------------------- |
| `pipeline_name`         | `uniprot_protein` | Уникальное имя пайплайна.                 |
| `provider`              | `uniprot`         | Имя провайдера данных.                    |
| `entity_type`           | `protein`         | Тип извлекаемой сущности.                 |
| `business_primary_keys` | `["accession"]`   | Канонический бизнес-ключ для Silver/Gold. |

## 3. Процесс (ETL)

### 3.1. Extract

- **Источник:** UniProt REST API.
- **Стратегия:** `incremental` по `accession`.
- **Auth:** `configs/providers/uniprot.yaml` declares `auth_type: public`.
  `BIOETL_UNIPROT_API_KEY` is optional and only enables the configured
  higher-throughput profile when present.
- **Rate Limit:** 10 запросов в секунду по умолчанию, до 100 запросов в секунду с optional API key.

### 3.2. Transform

- Дедупликация записей.
- Валидация схемы.

### 3.3. Load

| Слой       | Формат                  | Стратегия              | Таблица/Путь                 |
| ---------- | ----------------------- | ---------------------- | ---------------------------- |
| **Bronze** | `jsonl` (сжатый `zstd`) | Append-only            | `bronze/uniprot/protein/...` |
| **Silver** | `delta`                 | Merge (по `accession`) | `uniprot_protein`            |
| **Gold**   | `delta`                 | -                      | `dim_target`                 |

## 4. Качество Данных (DQ)

- **Strict Mode:** `false` — ошибки валидации не приведут к падению пайплайна, а будут отправлены в карантин.

## 5. См. также

- [Running Pipelines](../../../03-guides/running-pipelines.md) - Запуск пайплайнов
- [ChEMBL Activity](../chembl/activity.md) - Детальная документация (пример)
- [Project Rules](../../../00-project/RULES.md) - Правила обработки данных

______________________________________________________________________

## Contract References

| Артефакт             | Ссылка                                                                                   |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Gold contract export | [uniprot_protein_v1.0.json](../../contracts/gold/uniprot_protein_v1.0.json)              |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                       |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

______________________________________________________________________

## Compliance

| Контроль          | Статус | Evidence                                                                                 |
| ----------------- | ------ | ---------------------------------------------------------------------------------------- |
| Metadata          | Pass   | YAML header содержит `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified` |
| Runtime alignment | Pass   | Активный config/runtime surface описан в разделах `Конфигурация` и `Процесс (ETL)`       |
| Contract linkage  | Pass   | [uniprot_protein_v1.0.json](../../contracts/gold/uniprot_protein_v1.0.json)              |
| API governance    | Pass   | См. [API Compliance](#api-compliance)                                                    |

______________________________________________________________________

## API Compliance

### Rate limits & retries

Официально доступные retrievable источники подтверждают, что UniProt REST API свободно доступен и не требует login/authentication, но не публикуют числовой rate limit. Клиент SHOULD использовать bounded exponential backoff и MUST NOT рассматривать внутренние project-config лимиты как provider contract. Provider-published numeric retry budget — [неуточнено].

### 429 handling policy

Явная HTTP `429` policy для `rest.uniprot.org` в доступных официальных источниках — [неуточнено]. При throttle или transient failures клиент SHOULD уменьшать частоту запросов и использовать backoff.

### Authentication model

UniProt explicitly describes the website REST API as free to use and states that there is no login or authentication requirement.

### ToS URL

- [неуточнено]

### Data license

UniProt publishes its RDF data under CC BY 4.0. The canonical REST API help/license page exists, but its machine-readable contents were not retrievable during this audit.

### Personal data notes

REST API data are protein-centric rather than user-centric. API-specific personal-data handling is [неуточнено] in the accessible official docs.

### Official sources

- [UniProt website API paper](https://academic.oup.com/nar/article/53/W1/W547/8126256)
- [UniProt API documentation](https://www.uniprot.org/api-documentation)
- [UniProt license page](https://www.uniprot.org/help/license)
- [UniProt copyright page](https://www.uniprot.org/help/copyright)
- [UniProt RDF void metadata](https://sparql.uniprot.org/.well-known/void)

*Последнее обновление: 2026-04-28*
