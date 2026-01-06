# Пайплайн: UniProt ID Mapping

**Имя пайплайна:** `uniprot_idmapping`
**Провайдер:** `uniprot`
**Сущность:** `idmapping`
**Версия схемы:** 1.0.0

---

## 1. Описание

Пайплайн выполняет маппинг идентификаторов ChEMBL Target на UniProt Accession через UniProt ID Mapping REST API. Используется для связывания биоактивных мишеней ChEMBL с белковыми последовательностями UniProt.

### Основные сценарии использования

1. **Маппинг ChEMBL → UniProt** — получение UniProt accession для ChEMBL targets
2. **Обогащение данных об активности** — связь bioactivity records с белковыми структурами
3. **Graceful Not Found** — корректная обработка targets без маппинга

### Особенности реализации

- **Job-based API:** Асинхронный трёхэтапный процесс (submit → poll → fetch)
- **Batch Processing:** До 500 IDs за один API job
- **DQ Warning:** Записи без маппинга (`not_found`) сохраняются с `_dq_warn=True`
- **Bronze Disabled:** Данные идут напрямую из API, минуя Bronze-слой

---

## 2. Ключевые Поля

### Идентификаторы

| Поле | Тип | Nullable | Описание |
|------|-----|----------|----------|
| `entity_id` | `str` | ❌ | Формат: `chembl:uniprot:{target_chembl_id}` |
| `target_chembl_id` | `str` | ❌ | ChEMBL Target ID (e.g., CHEMBL204) — первичный ключ |
| `uniprot_accession` | `str` | ✅ | UniProt Accession (e.g., P00742), null если не найден |

### Статус маппинга

| Поле | Тип | Значения | Описание |
|------|-----|----------|----------|
| `mapping_status` | `str` | `found`, `not_found`, `error` | Результат маппинга |
| `_dq_warn` | `bool` | `True`, `False` | DQ предупреждение (`True` для `not_found`) |

### Lineage Metadata

| Поле | Тип | Описание |
|------|-----|----------|
| `content_hash` | `str` | SHA256 от business data |
| `_run_id` | `str` | UUID запуска пайплайна |
| `_run_type` | `str` | `incremental`, `backfill`, `rebuild` |
| `_ingestion_ts` | `str` | Timestamp ingestion (ISO 8601) |
| `_index` | `int` | Порядковый номер записи |

---

## 3. Конфигурация

**Источник:** `configs/pipelines/uniprot/idmapping.yaml`

```yaml
pipeline_name: uniprot_idmapping
provider: uniprot
entity_type: idmapping
version: "1.0.0"

primary_keys: ["target_chembl_id"]
silver_table: "uniprot_idmapping"
gold_table: "uniprot_idmapping"

source:
  type: file
  input_path: data/input/target.csv
  api:
    base_url: https://rest.uniprot.org
    from_db: ChEMBL
    to_db: UniProtKB

# Elevated thresholds for ID mapping
dq_rules:
  soft_fail_threshold: 0.30  # 30% not_found acceptable
  hard_fail_threshold: 0.80  # 80% not_found → hard failure

rate_limit:
  requests_per_second: 10.0
  burst: 20

gold_filters:
  required_fields:
    - target_chembl_id
    - mapping_status
```

---

## 4. Процесс (ETL)

### 4.1. Extract

- **Источник:** UniProt ID Mapping REST API (`https://rest.uniprot.org/idmapping`)
- **Input:** CSV файл с колонкой `target_chembl_id`
- **Batch Size:** 500 IDs per job
- **API Flow:**
  1. `POST /idmapping/run` — submit job, получить `jobId`
  2. `GET /idmapping/status/{jobId}` — poll пока `FINISHED`
  3. `GET /idmapping/results/{jobId}` — fetch results (с пагинацией)

### 4.2. Transform

**Transformer:** `src/bioetl/application/pipelines/uniprot/idmapping_transformer.py`

1. Извлечение `target_chembl_id` и `uniprot_accession` из API response
2. Определение `mapping_status`: `found` | `not_found`
3. Генерация `entity_id`: `chembl:uniprot:{target_chembl_id}`
4. Вычисление `content_hash` (SHA256)
5. Установка `_dq_warn=True` для `not_found`

### 4.3. Load

| Слой | Формат | Стратегия | Путь |
|------|--------|-----------|------|
| **Bronze** | — | Disabled | — |
| **Silver** | `delta` | Merge по `target_chembl_id` | `data/output/silver/uniprot/idmapping` |
| **Gold** | `delta` | Overwrite | `data/output/gold/uniprot/idmapping` |

---

## 5. Качество Данных (DQ)

### Пороги

| Порог | Значение | Действие |
|-------|----------|----------|
| **Soft** | 30% `not_found` | Warning в логах |
| **Hard** | 80% `not_found` | Fail batch |

### Обоснование elevated thresholds

Многие ChEMBL targets не имеют прямого маппинга на UniProt:
- Комплексные мишени (multi-protein complexes)
- Семейства белков (protein families)
- Non-protein targets (nucleic acids, lipids)

---

## 6. API Reference

### UniProt ID Mapping API

**Документация:** https://www.uniprot.org/help/id_mapping

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

---

## 7. Примеры

### Входные данные (CSV)

```csv
target_chembl_id
CHEMBL204
CHEMBL2034
CHEMBL9999999
```

### Выходные данные (Silver)

```json
[
  {
    "entity_id": "chembl:uniprot:CHEMBL204",
    "target_chembl_id": "CHEMBL204",
    "uniprot_accession": "P00742",
    "mapping_status": "found",
    "_dq_warn": false,
    "_run_id": "...",
    "_ingestion_ts": "2026-01-06T..."
  },
  {
    "entity_id": "chembl:uniprot:CHEMBL9999999",
    "target_chembl_id": "CHEMBL9999999",
    "uniprot_accession": null,
    "mapping_status": "not_found",
    "_dq_warn": true,
    "_run_id": "...",
    "_ingestion_ts": "2026-01-06T..."
  }
]
```

---

## 8. Связанные Компоненты

| Компонент | Путь |
|-----------|------|
| **Config** | `configs/pipelines/uniprot/idmapping.yaml` |
| **Transformer** | `src/bioetl/application/pipelines/uniprot/idmapping_transformer.py` |
| **Client** | `src/bioetl/infrastructure/adapters/uniprot/idmapping_client.py` |
| **Silver Schema** | `src/bioetl/infrastructure/schemas/silver.py:134-154` |
| **Gold Schema** | `src/bioetl/infrastructure/schemas/gold.py:166-198` |
| **Unit Tests** | `tests/unit/application/pipelines/test_idmapping_transformer.py` |
| **Integration Tests** | `tests/integration/adapters/test_uniprot_idmapping.py` |

---

## 9. См. также

- [UniProt Protein](./protein.md) — Пайплайн для белковых записей
- [ChEMBL Target](../chembl/target.md) — Источник Target IDs
- [Running Pipelines](../../03-guides/running-pipelines.md) — Запуск пайплайнов
- [Project Rules](../../RULES.md) — Правила обработки данных
