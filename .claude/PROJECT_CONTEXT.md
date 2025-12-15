# BioETL: Контекст Проекта для Claude

*Автоматически сгенерировано из RULES.md v5.0*
*Последнее обновление: 2025-12-15*

## Быстрая Справка

### Архитектура
- **Стиль**: Ports & Adapters (Hexagonal), слоистая архитектура
- **Слои**: Infrastructure (адаптеры) → Application (пайплайны) → Domain (чистая логика, без I/O)
- **Контракты**: `typing.Protocol` в `domain/ports.py`, проверка `mypy --strict`

### Medallion Architecture (Поток Данных)

| Слой | Формат | Retention | Идемпотентность |
|------|--------|-----------|-----------------|
| **Bronze** | JSONL + zstd | 90d → Archive | Append-only, путь: `bronze/{version}/{provider}/{entity}/{date}/` |
| **Silver** | Delta Lake | Permanent | Merge/Upsert, ACID обязателен |
| **Gold** | Delta/Parquet | Permanent | SCD Type 2 или партиционирование по дате |

### Критические Инварианты (MUST)

#### Delta Lake
- Engine: `delta-rs` (Rust core)
- VACUUM: **еженедельно** с `retention_period=7 days`
- Forensic retention: 7d default, 30d для critical таблиц

#### ID Generation
- Entity ID: стабильный бизнес-ключ (`chembl_id`) или Content Hash
- Content Hash: `sha256(provider + canonical_json(record))`
- Нормализация перед хэшем: NaN/Inf → null, floats → round(10), dates → ISO, strings → strip()
- Исключить из хэша: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_*`

#### Schema Drift SLA
- Info: новые опциональные поля → log
- Warn: >3 новых поля → review (SLA 48h)
- Critical: исчезновение ID → block pipeline

#### Backfill Locks
- Incremental: `lock:{provider}_{entity}`
- Backfill/Rebuild: `lock:{provider}_{entity}:exclusive`
- TTL: 60s, Heartbeat: 20s, Max Duration: 4h
- Fencing Token: `owner_id` (run_id)
- **Invariant**: Потеря lock = аварийное завершение ДО commit

#### Quarantine (Dead Letter Queue)
- Unified таблица: `common.quarantine`
- Payload: truncated to 64KB
- Retention: 30 дней
- Linkage: обязательна ссылка на Bronze (`bronze_file_uri` или `batch_id`)

### Обработка Ошибок

#### Классификация
- **Critical**: Auth fail, schema mismatch (Gold), DB down → Fail pipeline
- **Recoverable**: 429, 502/504, network → Retry (Max: 3, Multiplier: 2.0, Jitter: 0.1-0.5s)
- **Data Quality**: Invalid SMILES, missing field → Log + Skip record (не роняет батч)

#### Пороги (Thresholds)
- Soft: >5% DQ errors → Warning
- Hard: >20% DQ errors → Fail Batch

#### Circuit Breaker
- Trigger: 5 consecutive errors
- Open Duration: 5 min
- Recovery: Half-Open → 1 probe request
- Metric: `circuit_breaker_state` (0=Closed, 1=Half-Open, 2=Open)

### Observability

#### Log Schema (MUST)
```json
{
  "ts": "2025-12-15T10:00:00Z",
  "level": "INFO",
  "run_id": "uuid",
  "pipeline": "chembl_activity",
  "stage": "extract|transform|load",
  "dataset": "chembl.activity",  // SHOULD
  "record_count": 1000           // SHOULD
}
```

#### Retention
- Logs: 30 дней
- Metrics: 90 дней

#### Provider Health
- Healthy: 0 errors
- Degraded: 1-2 errors → Timeout ×2, batch_size ÷2
- Unhealthy: ≥3 errors → Pause, Alert P2

### Security

#### PII Handling
- Bronze: как есть (Internal)
- Silver: `sha256(lowercase(value) + SALT)` — **salted обязательно**
- Gold: исключить или агрегировать

#### Salt Rotation (Dual-Salt Period)
1. Day 0: Generate `SALT_NEXT`
2. Days 1-7: Write с `SALT_NEXT`, Read проверяет оба
3. Day 8+: `SALT_CURRENT` = `SALT_NEXT`
4. Alert если >1% не мигрировано после 14d

#### Secrets
- Source: `os.environ`
- Format: `BIOETL_{PROVIDER}_{KEY}`
- **MUST NOT**: hardcode, `.env` в git

### Disaster Recovery

- **RPO**: 24 hours
- **RTO**: 4 hours
- Game Days: ежегодно (SHOULD)

### Партиционирование

- Bronze: по `ingestion_date` (YYYY-MM-DD)
- Soft Limit: >10K партиций или >100 файлов/партицию → Warning
- Hard Limit: >50K партиций → Fail
- **MUST NOT**: UUID, Hash, Free-text как ключи партиционирования
- Альтернатива: Z-ORDER для высокой кардинальности

### Стек (MUST)

- HTTP: **httpx** (async)
- Validation: **Pandera**
- Linter: **Ruff**
- Delta: **delta-rs**
- Legacy libs без async: `await loop.run_in_executor(thread_pool, func)`

### Тестирование

- Unit: доменная логика, in-memory fakes, **БЕЗ моков** внешних библиотек
- Integration: **VCR.py** (`tests/fixtures/vcr/`)
  - Санитизация: `Authorization`, `X-API-Key`, PII в `before_record`
  - CI: `pytest --vcr-record=none` (падать при отсутствии cassette)
- Contract Tests: ежемесячно против реальных API

### Graceful Shutdown

При SIGTERM/SIGINT:
1. Прекратить fetch новых записей
2. Дождаться записи текущего батча
3. Сохранить чекпоинт в S3 (с If-Match/ETag)
4. Exit code 0

### Checkpoint Recovery

- `--resume`: продолжить с `last_processed_id + 1`
- Без флага при найденном чекпоинте → Warning
- После успеха → удалить чекпоинт

### Data Contracts

- Реестр: `docs/contracts/gold/{entity}.json`
- Версионирование: `{entity}_v{major}.{minor}`
- Minor: добавление nullable полей
- Major: удаление/переименование, изменение типов
- PR с breaking change → лейбл `breaking-change`
- Deprecation период: 2 недели

### Rollback

- Auto: Error Rate > 10%
- **MUST NOT**: DQ ошибки не триггерят rollback
- Manual: `make rollback VERSION=...`

### Developer Experience

```bash
make install       # venv + dependencies
make test          # unit + integration
make lint          # ruff + mypy
make run-local     # sample pipeline
make docker-reset  # clean start
```

### Провайдеры (Rate Limits)

| Provider | Library | Rate Limit | Auth |
|----------|---------|------------|------|
| ChEMBL | chembl_webresource_client | None | Public |
| PubChem | pubchempy | 5 req/s | Public |
| UniProt | unipressed | 100 req/s | API Key |
| OpenAlex | pyalex | 10 req/s | Email |
| Semantic Scholar | semanticscholar | 100 req/5min | API Key |
| PubMed | biopython | 3 req/s (10 w/ key) | API Key |
| Crossref | habanero | 50 req/s | Email |

### Governance (RFC 2119)

- **MUST**: абсолютное требование, нарушение = блокер релиза
- **SHOULD**: сильная рекомендация, отклонение требует обоснования в PR
- **MAY**: опционально

---

## Полная Документация

- **RULES.md**: Полная спецификация v5.0 (Production Ready)
- **REQUIREMENTS.md**: 127 тестируемых требований (123 MUST, 4 SHOULD)
- **CHANGELOG.md**: История изменений

## Важные Пути

- Domain Ports: `src/bioetl/domain/ports.py`
- Adapters: `src/bioetl/infrastructure/adapters/{provider}/`
- Pipelines: `src/bioetl/application/pipelines/`
- Tests: `tests/` (unit + integration)
- VCR Cassettes: `tests/fixtures/vcr/`
- Configs: `configs/pipelines/{pipeline}.yaml`

## Приоритеты при Разработке

1. **Безопасность**: Секреты, PII, IAM
2. **Надежность**: Lock invariants, graceful shutdown, idempotency
3. **Observability**: Structured logs, metrics, correlation ID
4. **Производительность**: Delta VACUUM, партиционирование, rate limiting
5. **Поддерживаемость**: Type safety, contracts, testing

---

*Этот файл автоматически обновляется при изменении RULES.md*
