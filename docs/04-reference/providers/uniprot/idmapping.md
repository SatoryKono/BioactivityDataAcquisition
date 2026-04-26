______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# Пайплайн: UniProt ID Mapping

**Имя пайплайна:** `uniprot_idmapping`
**Провайдер:** `uniprot`
**Сущность:** `idmapping`
**Версия схемы:** 1.0.0

______________________________________________________________________

## 1. Описание

Пайплайн выполняет маппинг идентификаторов ChEMBL Target на UniProt Accession через UniProt ID Mapping REST API. Используется для связывания биоактивных мишеней ChEMBL с белковыми последовательностями UniProt.

### Основные сценарии использования

1. **Маппинг ChEMBL → UniProt** — получение UniProt accession для ChEMBL targets
1. **Обогащение данных об активности** — связь bioactivity records с белковыми структурами
1. **Graceful Not Found** — корректная обработка targets без маппинга

### Особенности реализации

- **Job-based API:** Асинхронный трёхэтапный процесс (submit → poll → fetch)
- **Batch Processing:** До 500 IDs за один API job
- **DQ Warning:** Записи без маппинга (`not_found`) сохраняются с `_dq_warn=True`
- **Bronze Disabled:** Данные идут напрямую из API, минуя Bronze-слой

______________________________________________________________________

## 2. Ключевые Поля

### Идентификаторы

| Поле                | Тип   | Nullable | Описание                                              |
| ------------------- | ----- | -------- | ----------------------------------------------------- |
| `entity_id`         | `str` | ❌       | Формат: `chembl:uniprot:{target_id}`                  |
| `target_id`         | `str` | ❌       | ChEMBL Target ID (e.g., CHEMBL204) — первичный ключ   |
| `uniprot_accession` | `str` | ✅       | UniProt Accession (e.g., P00742), null если не найден |

### Статус маппинга

| Поле             | Тип    | Значения                                  | Описание                                   |
| ---------------- | ------ | ----------------------------------------- | ------------------------------------------ |
| `mapping_status` | `str`  | `found`, `not_found`, `error`, `multiple` | Результат маппинга                         |
| `_dq_warn`       | `bool` | `True`, `False`                           | DQ предупреждение (`True` для `not_found`) |

### Occurrence-Scoped Provenance

| Поле           | Тип   | Описание                |
| -------------- | ----- | ----------------------- |
| `content_hash` | `str` | SHA256 от business data |
| `_index`       | `int` | Порядковый номер записи |

`run_id`, `run_type`, `source_batch_id` и `ingestion_ts` не входят в
persisted Silver/Gold row contract. Эти occurrence-scoped anchors публикуются
через metadata sidecar, lineage fragments, run manifest и run ledger.

______________________________________________________________________

## 3. Конфигурация

**Источник:** `configs/entities/uniprot/idmapping.yaml`

```yaml
version: 1.0.0
provider: uniprot
entity: idmapping

pipeline:
  pipeline_name: uniprot_idmapping
  provider: uniprot
  entity_type: idmapping
  source:
    api:
      base_url: https://rest.uniprot.org
      from_db: ChEMBL
      to_db: UniProtKB

quality:
  thresholds:
    soft_fail: 0.30  # 30% not_found acceptable
    hard_fail: 0.80  # 80% not_found -> hard failure

filters:
  input_filter:
    enabled: false
    source_path: data/input/target.csv
    column_name: target_chembl_id
    filter_field: target_id
  gold_filters:
    required_fields:
      - target_id
      - mapping_status
```

______________________________________________________________________

## 4. Процесс (ETL)

### 4.1. Extract

- **Источник:** UniProt ID Mapping REST API (`https://rest.uniprot.org/idmapping`)
- **Input:** CSV файл с колонкой `target_id`
- **Batch Size:** 500 IDs per job
- **API Flow:**
  1. `POST /idmapping/run` — submit job, получить `jobId`
  1. `GET /idmapping/status/{jobId}` — poll пока `FINISHED`
  1. `GET /idmapping/results/{jobId}` — fetch results (с пагинацией)

### 4.2. Transform

**Transformer:** `src/bioetl/application/pipelines/uniprot/idmapping_transformer.py`

1. Извлечение `target_id` и `uniprot_accession` из API response
1. Определение `mapping_status`: `found` | `not_found`
1. Генерация `entity_id`: `chembl:uniprot:{target_id}`
1. Вычисление `content_hash` (SHA256)
1. Установка `_dq_warn=True` для `not_found`

### 4.3. Load

| Слой       | Формат  | Стратегия            | Путь                                   |
| ---------- | ------- | -------------------- | -------------------------------------- |
| **Bronze** | —       | Disabled             | —                                      |
| **Silver** | `delta` | Merge по `target_id` | `data/output/silver/uniprot/idmapping` |
| **Gold**   | `delta` | Overwrite            | `data/output/gold/uniprot/idmapping`   |

______________________________________________________________________

## 5. Качество Данных (DQ)

### Пороги

| Порог    | Значение        | Действие        |
| -------- | --------------- | --------------- |
| **Soft** | 30% `not_found` | Warning в логах |
| **Hard** | 80% `not_found` | Fail batch      |

### Обоснование elevated thresholds

Многие ChEMBL targets не имеют прямого маппинга на UniProt:

- Комплексные мишени (multi-protein complexes)
- Семейства белков (protein families)
- Non-protein targets (nucleic acids, lipids)

______________________________________________________________________

## 6. API Reference

### UniProt ID Mapping API

**Документация:** https://www.uniprot.org/help/id-mapping

**Поддерживаемые базы данных:**

- `ChEMBL` → `UniProtKB` (основной сценарий)
- Полный список: GET `/configure/idmapping/fields`

**Ограничения:**

- Max 100,000 IDs per job
- Job results хранятся 7 дней
- Min polling interval: 3 секунды

### Health Check

```python
# Endpoint: GET /configure/idmapping/fields
await client.health_check()  # Returns HealthStatus.HEALTHY
```

______________________________________________________________________

## 7. Примеры

### Входные данные (CSV)

```csv
target_id
CHEMBL204
CHEMBL2034
CHEMBL9999999
```

### Выходные данные (Silver)

```json
[
  {
    "entity_id": "chembl:uniprot:CHEMBL204",
    "target_id": "CHEMBL204",
    "uniprot_accession": "P00742",
    "mapping_status": "found",
    "_dq_warn": false,
    "content_hash": "sha256:..."
  },
  {
    "entity_id": "chembl:uniprot:CHEMBL9999999",
    "target_id": "CHEMBL9999999",
    "uniprot_accession": null,
    "mapping_status": "not_found",
    "_dq_warn": true,
    "content_hash": "sha256:..."
  }
]
```

______________________________________________________________________

## 8. Связанные Компоненты

| Компонент             | Путь                                                                |
| --------------------- | ------------------------------------------------------------------- |
| **Config**            | `configs/entities/uniprot/idmapping.yaml`                           |
| **Transformer**       | `src/bioetl/application/pipelines/uniprot/idmapping_transformer.py` |
| **Client**            | `src/bioetl/infrastructure/adapters/uniprot/idmapping_client.py`    |
| **Silver Schema**     | `src/bioetl/domain/schemas/uniprot/idmapping.py`                    |
| **Gold Schema**       | `src/bioetl/domain/schemas/uniprot/idmapping.py`                    |
| **Unit Tests**        | `tests/unit/application/pipelines/test_idmapping_transformer.py`    |
| **Integration Tests** | `tests/integration/adapters/test_uniprot_idmapping.py`              |

______________________________________________________________________

## 9. См. также

- [UniProt Protein](./protein.md) — Пайплайн для белковых записей
- [ChEMBL Target](../chembl/target.md) — Источник Target IDs
- [Running Pipelines](../../../03-guides/running-pipelines.md) — Запуск пайплайнов
- [Project Rules](../../../00-project/RULES.md) — Правила обработки данных

______________________________________________________________________

## Contract References

| Артефакт             | Ссылка                                                                                   |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Gold contract export | [uniprot_idmapping_v1.0.json](../../contracts/gold/uniprot_idmapping_v1.0.json)          |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                       |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

______________________________________________________________________

## Compliance

| Контроль          | Статус | Evidence                                                                                                  |
| ----------------- | ------ | --------------------------------------------------------------------------------------------------------- |
| Metadata          | Pass   | YAML header содержит `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified`                  |
| Runtime alignment | Pass   | Активный config/runtime surface описан в разделах `Конфигурация`, `Процесс (ETL)`, `Связанные Компоненты` |
| Contract linkage  | Pass   | [uniprot_idmapping_v1.0.json](../../contracts/gold/uniprot_idmapping_v1.0.json)                           |
| API governance    | Pass   | См. [API Compliance](#api-compliance)                                                                     |

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

*Последнее обновление: 2026-03-30*
