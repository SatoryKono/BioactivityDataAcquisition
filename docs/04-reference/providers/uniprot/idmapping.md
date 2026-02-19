# Пайплайн: UniProt ID Mapping

**Имя пайплайна:** `uniprot-idmapping`
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
- **DQ Warning:** Записи без маппинга (`not-found`) сохраняются с `-dq-warn=True`
- **Bronze Disabled:** Данные идут напрямую из API, минуя Bronze-слой

---

## 2. Ключевые Поля

### Идентификаторы

| Поле | Тип | Nullable | Описание |
|------|-----|----------|----------|
| `entity-id` | `str` | ❌ | Формат: `chembl:uniprot:{target-chembl-id}` |
| `target-chembl-id` | `str` | ❌ | ChEMBL Target ID (e.g., CHEMBL204) — первичный ключ |
| `uniprot-accession` | `str` | ✅ | UniProt Accession (e.g., P00742), null если не найден |

### Статус маппинга

| Поле | Тип | Значения | Описание |
|------|-----|----------|----------|
| `mapping-status` | `str` | `found`, `not-found`, `error` | Результат маппинга |
| `-dq-warn` | `bool` | `True`, `False` | DQ предупреждение (`True` для `not-found`) |

### Lineage Metadata

| Поле | Тип | Описание |
|------|-----|----------|
| `content-hash` | `str` | SHA256 от business data |
| `-run-id` | `str` | UUID запуска пайплайна |
| `-run-type` | `str` | `incremental`, `backfill`, `rebuild` |
| `-ingestion-ts` | `str` | Timestamp ingestion (ISO 8601) |
| `-index` | `int` | Порядковый номер записи |

---

## 3. Конфигурация

**Источник:** `configs/pipelines/uniprot/idmapping.yaml`

```yaml
pipeline-name: uniprot-idmapping
provider: uniprot
entity-type: idmapping
version: "1.0.0"

primary-keys: ["target-chembl-id"]
silver-table: "uniprot-idmapping"
gold-table: "uniprot-idmapping"

source:
  type: file
  input-path: data/input/target.csv
  api:
    base-url: https://rest.uniprot.org
    from-db: ChEMBL
    to-db: UniProtKB

# Elevated thresholds for ID mapping
dq-overrides:
  soft-fail-threshold: 0.30  # 30% not-found acceptable
  hard-fail-threshold: 0.80  # 80% not-found → hard failure

rate-limit:
  requests-per-second: 10.0
  burst: 20

gold-filters:
  required-fields:
    - target-chembl-id
    - mapping-status
```

---

## 4. Процесс (ETL)

### 4.1. Extract

- **Источник:** UniProt ID Mapping REST API (`https://rest.uniprot.org/idmapping`)
- **Input:** CSV файл с колонкой `target-chembl-id`
- **Batch Size:** 500 IDs per job
- **API Flow:**
  1. `POST /idmapping/run` — submit job, получить `jobId`
  2. `GET /idmapping/status/{jobId}` — poll пока `FINISHED`
  3. `GET /idmapping/results/{jobId}` — fetch results (с пагинацией)

### 4.2. Transform

**Transformer:** `src/bioetl/application/pipelines/uniprot/idmapping-transformer.py`

1. Извлечение `target-chembl-id` и `uniprot-accession` из API response
2. Определение `mapping-status`: `found` | `not-found`
3. Генерация `entity-id`: `chembl:uniprot:{target-chembl-id}`
4. Вычисление `content-hash` (SHA256)
5. Установка `-dq-warn=True` для `not-found`

### 4.3. Load

| Слой | Формат | Стратегия | Путь |
|------|--------|-----------|------|
| **Bronze** | — | Disabled | — |
| **Silver** | `delta` | Merge по `target-chembl-id` | `data/output/silver/uniprot/idmapping` |
| **Gold** | `delta` | Overwrite | `data/output/gold/uniprot/idmapping` |

---

## 5. Качество Данных (DQ)

### Пороги

| Порог | Значение | Действие |
|-------|----------|----------|
| **Soft** | 30% `not-found` | Warning в логах |
| **Hard** | 80% `not-found` | Fail batch |

### Обоснование elevated thresholds

Многие ChEMBL targets не имеют прямого маппинга на UniProt:
- Комплексные мишени (multi-protein complexes)
- Семейства белков (protein families)
- Non-protein targets (nucleic acids, lipids)

---

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
await client.health-check()  # Returns HealthStatus.HEALTHY
```

---

## 7. Примеры

### Входные данные (CSV)

```csv
target-chembl-id
CHEMBL204
CHEMBL2034
CHEMBL9999999
```

### Выходные данные (Silver)

```json
[
  {
    "entity-id": "chembl:uniprot:CHEMBL204",
    "target-chembl-id": "CHEMBL204",
    "uniprot-accession": "P00742",
    "mapping-status": "found",
    "-dq-warn": false,
    "-run-id": "...",
    "-ingestion-ts": "2026-01-06T..."
  },
  {
    "entity-id": "chembl:uniprot:CHEMBL9999999",
    "target-chembl-id": "CHEMBL9999999",
    "uniprot-accession": null,
    "mapping-status": "not-found",
    "-dq-warn": true,
    "-run-id": "...",
    "-ingestion-ts": "2026-01-06T..."
  }
]
```

---

## 8. Связанные Компоненты

| Компонент | Путь |
|-----------|------|
| **Config** | `configs/pipelines/uniprot/idmapping.yaml` |
| **Transformer** | `src/bioetl/application/pipelines/uniprot/idmapping-transformer.py` |
| **Client** | `src/bioetl/infrastructure/adapters/uniprot/idmapping-client.py` |
| **Silver Schema** | `src/bioetl/infrastructure/schemas/silver.py:134-154` |
| **Gold Schema** | `src/bioetl/infrastructure/schemas/gold.py:166-198` |
| **Unit Tests** | `tests/unit/application/pipelines/test-idmapping-transformer.py` |
| **Integration Tests** | `tests/integration/adapters/test-uniprot-idmapping.py` |

---

## 9. См. также

- [UniProt Protein](./protein.md) — Пайплайн для белковых записей
- [ChEMBL Target](../chembl/target.md) — Источник Target IDs
- [Running Pipelines](../../03-guides/running-pipelines.md) — Запуск пайплайнов
- [Project Rules](../../00-project/RULES.md) — Правила обработки данных
