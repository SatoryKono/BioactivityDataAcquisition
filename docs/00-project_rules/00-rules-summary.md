# Rules Summary
*Синхронизировано с RULES.md v5.0 (2025-12-15)*

## Уровни Требований (RFC 2119)
- **MUST** (Обязательно): Нарушение = дефект/блокер релиза.
- **SHOULD** (Рекомендуется): Отклонение требует обоснования в PR.
- **MAY** (Опционально): На усмотрение разработчика.

## Quick Reference
| Задача | Раздел | Инструмент |
|--------|--------|------------|
| Создать новый пайплайн | §1, App D | YAML config |
| Добавить поле в схему | §3.1 | Pandera + Schema Evolution |
| Ошибка в проде (Alert) | App C | Runbook |
| Удалить битые данные | §3.3 | `make quarantine-purge` |
| Развернуть на Staging | §5.3 | CI/CD |
| Восстановление при аварии | §5.2 | DR Runbook |
| Откат релиза | §6 | Rollback Strategy |
| Backfill с эксклюзивной блокировкой | §4.3 | Lock Mechanism |
| Deprecation поля | §6, App E | Schema Evolution |

## 1. Архитектура и структура

- Hexagonal (Ports & Adapters) + DDD.
- Слои: `domain`, `application`, `infrastructure`, `interfaces`.
- Пайплайны: `src/bioetl/application/pipelines/<provider>/<entity>/`.
- Документация: kebab-case с NN- префиксом; пайплайны в `docs/application/pipelines/<provider>/<entity>/`.
- **Инварианты**: одна сущность → один публичный пайплайн; строгая последовательность `extract→transform→validate→export`.
- **Контракты (§1.1.1)**: Интерфейсы через `typing.Protocol` в `domain/ports.py`. Design-time: `mypy --strict`. Runtime: `@runtime_checkable` только для критичных адаптеров.

## 2. Именование

| Элемент | Формат | Пример |
|---------|--------|--------|
| Классы | `PascalCase` + суффикс | `ChemblDataClientImpl` |
| Модули | `snake_case` | `unified_api_client.py` |
| Функции | `snake_case` + префикс | `fetch_chembl_page()` |
| Документация | `kebab-case` | `01-pipeline-overview.md` |
| Pipeline docs | `NN-<entity>-<provider>-<topic>.md` | `01-activity-chembl-extract.md` |

- Naming-linter в CI; исключения через `configs/naming_exceptions.yaml`.

## 3. Данные и Схемы (Medallion Architecture)

### 3.1. Уровни данных
| Уровень | Формат | Валидация | Retention | Идемпотентность |
|---------|--------|-----------|-----------|-----------------|
| **Bronze** | JSONL + zstd | Мин./Нет | 90 дней hot → Archive | Append-only. Path: `bronze/{format_version}/{provider}/{entity}/{date}/` |
| **Silver** | Delta Lake | Мягкая (дрейф схемы) | Постоянно | **Merge/Upsert**. Raw Parquet **MUST NOT**. |
| **Gold** | Delta/Parquet | Строгая (`strict=True`) | Постоянно | SCD Type 2 или партиции по дате |

### 3.2. Schema Drift Policy
| Уровень | Условие | Действие |
|---------|---------|----------|
| Info | Новое опциональное поле | Логируется |
| Warn | >3 новых полей | Требует ревью. SLA: 48ч |
| Critical | Исчезновение ID | Блокирует пайплайн |

### 3.3. Unified Quarantine (`common.quarantine`)
| Поле | Тип | Описание |
|------|-----|----------|
| `ingestion_ts` | Timestamp | Время инцидента |
| `pipeline` | String | `chembl_activity` |
| `error_code` | String | `SCHEMA_VIOLATION` |
| `payload` | JSON | Truncated to 64KB |
| `payload_hash` | String | Дедупликация |
| `bronze_batch_id` | UUID | FK на Bronze |
| `dq_status` | Enum | `NEW` / `IGNORED` / `REPROCESSED` |

- Retention: 30 дней. Triage еженедельно.
- **Sentinel values (-1, "N/A") MUST NOT использоваться.**

### 3.4. Data Lineage
- Silver Record содержит `_source_batch_id` (FK).
- Таблица `sys.lineage_log`: `_source_batch_id` → список Bronze файлов, версия трансформации.

### 3.5. Content Hash (Entity ID)
- Алгоритм: `sha256(provider + canonical_json_dumps(record))`.
- Canonical JSON: `sort_keys=True`, `separators=(',', ':')`, `ensure_ascii=True`.
- **Float Precision**: `round(val, 10)`.
- **Исключения из хэша**: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_*`.

## 4. Обработка Ошибок и Наблюдаемость

### 4.1. Классификация ошибок
| Тип | Поведение | Пример |
|-----|-----------|--------|
| Critical | Падение пайплайна | Auth failure, Gold schema mismatch |
| Recoverable | Retry N раз (Backoff) | 429, 502/504, сетевой сбой |
| Data Quality | Лог + Пропуск записи | Невалидный SMILES |

### 4.2. Thresholds
- Soft: >5% DQ errors → Warning.
- Hard: >20% → Fail Batch.

### 4.3. Concurrency & Locks (Redis)
| Параметр | Значение |
|----------|----------|
| Механизм | Redis `SETNX` + `EXPIRE` |
| TTL | 60 секунд |
| Heartbeat | Каждые 20 сек |
| Fencing Token | `owner_id` (run_id воркера) |
| Max Duration | 4 часа |

- **Invariant**: Потеря блокировки = Потеря права на запись.
- **Safety Guard**: Валидация `owner_id` перед записью в S3/Delta.

### 4.4. Circuit Breaker
| Параметр | Значение |
|----------|----------|
| Trigger | 5 consecutive errors |
| Open Duration | 5 минут |
| Recovery | Half-Open → 1 пробный запрос |
| Metrics | `circuit_breaker_state` (0/1/2), `trips_total` |

### 4.5. DQ Metrics (Prometheus)
- `dq_validation_score{check, column}`: NULL rate, unique count, schema violations.
- `data_freshness_seconds`: `now() - max(updated_at)`.
- **Anomaly Detection**: Baseline = MA(30 дней). Warning: >2x baseline. Critical: >5x baseline.
- **Cold Start**: Days 1-7 silence, 8-30 warning only, 30+ full alerting.

### 4.6. Provider Health Monitoring
| Status | Условие | Действие |
|--------|---------|----------|
| Healthy | 0 errors за 5 мин | Normal |
| Degraded | 1-2 consecutive errors | Timeout ×2, batch_size ÷2 |
| Unhealthy | ≥3 errors | Pause, Alert P2 |

## 5. Операции

### 5.1. Секреты
- Источник: `os.environ`.
- Формат: `BIOETL_{PROVIDER}_{KEY}`.
- **Хардкод MUST NOT. Файлы .env в git MUST NOT.**

### 5.2. Disaster Recovery
| Параметр | Значение |
|----------|----------|
| RPO | 24 часа |
| RTO | 4 часа |
| Game Days | **SHOULD** ежегодно |

**DR Procedures**:
| Сценарий | Действие |
|----------|----------|
| Повреждение Bronze/Silver | Stop → S3 Point-in-Time Restore → `--full-rebuild` |
| Потеря чекпоинта | `--ignore-checkpoint` (дедупликация в Silver исправит) |
| Отказ региона AWS | DNS Failover → Terraform в резервном регионе |

### 5.3. Environment Isolation
| Среда | S3 | Redis | Доступ к Prod-секретам |
|-------|-----|-------|------------------------|
| Dev | `bioetl-dev` | db0 | Нет |
| Staging | `bioetl-staging` | db1 | Нет |
| Prod | `bioetl-prod` | db2 | Только CI Runner |

### 5.4. Graceful Shutdown (SIGTERM/SIGINT)
1. Прекратить fetch новых записей.
2. Дождаться завершения текущего батча.
3. Сохранить чекпоинт в S3 (If-Match/ETag).
4. Выйти с кодом 0.
- **Guarantee**: At-Least-Once + Дедупликация в Silver.

### 5.5. Sensitive Data Policy
| Уровень | Действие |
|---------|----------|
| Bronze | Хранить как есть (Internal) |
| Silver | Хэшировать PII: `sha256(lowercase(value) + SALT)` |
| Gold | PII исключается или агрегируется |

- **PII fields MUST be salted.**
- **Salt Rotation**: Dual-Salt Period (7 дней transition).

## 6. Управление Изменениями

### 6.1. Schema Evolution
- Minor: добавление nullable полей.
- Major: удаление/переименование, изменение типов.

### 6.2. Field Deprecation Workflow
| День | Действие |
|------|----------|
| 0 | Пометить `deprecated: true` + `replacement` |
| 1-14 | Dual-write (оба поля) |
| 15 | Удаление, bump major version, ADR |

### 6.3. Rollback Strategy
- **Infrastructure/Code**: Auto Rollback при Error Rate >10%.
- **Data DQ**: Ручной анализ и replay. Не триггерит автоматический откат.

## 7. Код и Качество

- PEP8, Black, Ruff, Mypy (strict).
- Логирование: `UnifiedLogger` (структурный JSON). **print() MUST NOT.**
- Тесты: Unit (mock net), Integration (VCR.py), Golden. Coverage ≥85%.
- Zero-sum class count при дублировании.
- Чек-лист ревью: `docs/templates/pipeline-review-checklist.md`.

## 8. Рефакторинг модулей

### 8.1. Обязательные шаги
1. Карта зависимостей (grep imports, usages, tests, re-exports).
2. Coverage >80% перед началом.
3. Тесты обновляются ДО изменения реализации.
4. Breaking changes → `CHANGELOG.md` + ADR.

### 8.2. Валидация после рефакторинга
- [ ] Все тесты: `pytest tests/ -v --tb=short`
- [ ] Mypy: `mypy src/bioetl/ --strict`
- [ ] Circular imports: `python -c "from bioetl.domain import *"`
- [ ] Документация обновлена
- [ ] `__init__.py` exports актуальны
- [ ] Deprecation warnings добавлены
- [ ] CHANGELOG обновлён
- [ ] PR description содержит breaking changes

## TL;DR

1. RFC 2119: MUST = блокер, SHOULD = обоснование в PR, MAY = опционально.
2. Medallion: Bronze (JSONL) → Silver (Delta Lake, merge) → Gold (strict).
3. Quarantine: `common.quarantine`, retention 30 дней, sentinel values запрещены.
4. Locks: Redis SETNX, TTL 60s, Heartbeat 20s, Fencing Token, Max 4h.
5. DR: RPO 24h, RTO 4h, Game Days ежегодно.
6. Schema Evolution: 14-дневный deprecation period, dual-write.
7. Coverage ≥85%, mypy --strict, zero-sum class count.
