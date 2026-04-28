______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# Пайплайн: PubChem Compound

**Имя пайплайна:** `pubchem_compound`
**Провайдер:** `pubchem`
**Сущность:** `compound`

## 1. Описание

Этот пайплайн извлекает данные о химических соединениях (`compound`) из API PubChem.

## 2. Конфигурация

**Источник конфигурации:** `configs/entities/pubchem/compound.yaml`

| Параметр                | Значение           | Описание                                  |
| ----------------------- | ------------------ | ----------------------------------------- |
| `pipeline_name`         | `pubchem_compound` | Уникальное имя пайплайна.                 |
| `provider`              | `pubchem`          | Имя провайдера данных.                    |
| `entity_type`           | `compound`         | Тип извлекаемой сущности.                 |
| `business_primary_keys` | `["molecule_id"]`  | Канонический бизнес-ключ для Silver/Gold. |

## 3. Процесс (ETL)

### 3.1. Extract

- **Источник:** PubChem PUG REST API.
- **Стратегия:** `incremental` по `cid`.
- **Rate Limit:** 5 запросов в секунду.

### 3.2. Transform

- Дедупликация записей.
- Валидация схемы.
- Управляемая стандартизация структур до нормализации, вычисления `content_hash`
  и merge/dedup:
  - policy version: `pubchem-basic-v1`;
  - normalized identifiers: `standardized_canonical_smiles`,
    `standardized_isomeric_smiles`, `standardized_inchi`,
    `standardized_inchi_key`;
  - parent grouping key: `structure_parent_key`;
  - observability fields: `chemical_standardization_status` and
    `chemical_standardization_warnings`.

`pubchem-basic-v1` intentionally does not perform toolkit-based tautomer,
salt/solvent, charge, or parent-structure mutation. Unsupported cases are made
visible with bounded warning codes such as
`multi_component_parent_deferred`, `charge_normalization_deferred`,
`parent_key_from_smiles_without_inchi_key`, and
`structure_parent_key_unavailable`. This keeps the first policy deterministic
and dependency-free while providing a stable extension point for a future
RDKit/OpenBabel-backed policy.

| Status              | Meaning                                                                 |
| ------------------- | ----------------------------------------------------------------------- |
| `standardized`      | At least one structural identifier was normalized without warnings.      |
| `partial`           | A normalized identifier exists, but invalid/deferred cases were found.   |
| `invalid`           | Raw structural identifiers were present, but none passed validation.     |
| `missing_structure` | No SMILES/InChI/InChIKey input was present for the standardization pass. |

### 3.3. Load

| Слой       | Формат                  | Стратегия                | Таблица/Путь                  |
| ---------- | ----------------------- | ------------------------ | ----------------------------- |
| **Bronze** | `jsonl` (сжатый `zstd`) | Append-only              | `bronze/pubchem/compound/...` |
| **Silver** | `delta`                 | Merge (по `molecule_id`) | `pubchem_compound`            |
| **Gold**   | `delta`                 | -                        | `dim_compound`                |

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
| Gold contract export | [pubchem_compound_v1.0.json](../../contracts/gold/pubchem_compound_v1.0.json)            |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                       |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

______________________________________________________________________

## Compliance

| Контроль          | Статус | Evidence                                                                                 |
| ----------------- | ------ | ---------------------------------------------------------------------------------------- |
| Metadata          | Pass   | YAML header содержит `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified` |
| Runtime alignment | Pass   | Активный config/runtime surface описан в разделах `Конфигурация` и `Процесс (ETL)`       |
| Contract linkage  | Pass   | [pubchem_compound_v1.0.json](../../contracts/gold/pubchem_compound_v1.0.json)            |
| API governance    | Pass   | См. [API Compliance](#api-compliance)                                                    |

______________________________________________________________________

## API Compliance

### Rate limits & retries

PubChem publishes a dynamic request throttling page, but fixed numeric thresholds are not retrievable in the accessible official docs. Because PubChem is hosted on NCBI infrastructure, clients SHOULD stay within conservative NCBI scripting guidance and SHOULD batch requests where possible; provider-specific hard limits remain [неуточнено].

### 429 handling policy

PubChem documents dynamic throttling conceptually, but the accessible official references do not expose a stable HTTP `429` / `Retry-After` contract. При throttle клиент SHOULD уменьшать concurrency и увеличивать backoff.

### Authentication model

Standard PUG-REST examples are published as public requests; an account-based authentication requirement for routine retrieval was not found in the accessible official docs.

### ToS URL

- https://www.ncbi.nlm.nih.gov/home/about/policies/

### Data license

PubChem content is mixed and source-specific. NCBI policies explicitly note that PubChem may include copyrighted or otherwise licensed third-party content obtained under contract or legal agreement.

### Personal data notes

NCBI states that it does not collect personally identifiable information about visitors, but it does collect visit metadata to improve and secure services. API-specific personal-data guidance for PubChem query payloads is [неуточнено].

### Official sources

- [PubChem PUG-REST tutorial](https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest-tutorial)
- [PubChem dynamic request throttling](https://pubchem.ncbi.nlm.nih.gov/docs/dynamic-request-throttling)
- [NCBI policies and disclaimers](https://www.ncbi.nlm.nih.gov/home/about/policies/)

*Последнее обновление: 2026-03-30*
