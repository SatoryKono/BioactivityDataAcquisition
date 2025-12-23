# BioETL: Контекст Проекта для Claude

*Синхронизировано с CLAUDE.md и RULES.md v5.2*
*Последнее обновление: 2025-12-23*

---

## TL;DR — Быстрый Старт

```bash
# Проверка перед работой
make lint && make test

# Основные команды
make install          # Создание venv, установка зависимостей
make test             # Все тесты (unit + integration)
make lint             # ruff + mypy
make run-local        # Запуск на фикстурах
```

**Главные ресурсы:**
1. `CLAUDE.md` — Справочник для Claude Code
2. `AGENT.md` — Детальные инструкции для агента
3. `docs/RULES.md` — Конституция проекта (RFC 2119)

---

## 1. Архитектура Слоёв

```
src/bioetl/
├── domain/          # Чистая логика, Protocols (Ports). БЕЗ I/O.
├── application/     # Пайплайны, Use Cases, оркестрация
├── composition/     # Composition Root (DI-контейнер, factories, bootstrap)
├── infrastructure/  # Адаптеры (HTTP, локальное хранилище), реализация портов
└── interfaces/      # CLI, PipelineRunner
```

### 1.1. Матрица Импортов (ОБЯЗАТЕЛЬНО)

| Из ↓ / В → | domain | application | composition | infrastructure | interfaces |
|------------|--------|-------------|-------------|----------------|------------|
| **domain** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **application** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **composition** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **infrastructure** | ✅ | ❌ | ❌ | ✅ | ❌ |
| **interfaces** | ✅ | ✅ | ✅ | ✅ | ✅ |

**Нарушение = Блокер PR.** Проверяется `import-linter` и `tests/architecture/`.

### 1.2. Dependency Injection

- **MUST**: Зависимости передаются в конструктор
- **MUST NOT**: Создание зависимостей внутри классов
- **Composition Root**: `src/bioetl/composition/bootstrap.py`

---

## 2. Medallion Architecture

| Уровень | Формат | Хранение | Идемпотентность |
|---------|--------|----------|-----------------|
| **Bronze** | JSONL + zstd | 90d → Archive | Append-only. Path: `bronze/v1/{provider}/{entity}/{date}/` |
| **Silver** | Delta Lake | Permanent | Merge/Upsert по `content_hash`. ACID обязателен. |
| **Gold** | Delta/Parquet | Permanent | SCD Type 2 или партиции по дате |

### 2.1. Delta Lake (MUST)

- **Engine**: `delta-rs` (Rust core)
- **VACUUM**: Еженедельно, `retention_period=7 days`
- **Forensic Retention**: 7d default, 30d для critical таблиц

### 2.2. Content Hash

```
sha256(provider + canonical_json(record))
```

**Нормализация перед хэшем:**
- NaN/Inf → `null`
- Floats → `round(val, 10)`
- Dates → ISO `YYYY-MM-DD`
- Strings → `strip()`
- **Исключить**: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_*`

### 2.3. Schema Drift SLA

| Уровень | Условие | Действие |
|---------|---------|----------|
| Info | Новые опциональные поля | Log |
| Warn | >3 новых поля | Review (SLA 48h) |
| Critical | Исчезновение ID | Block pipeline |

---

## 3. Обработка Ошибок

### 3.1. Классификация

| Тип | Поведение | Пример |
|-----|-----------|--------|
| **Critical** | Падение пайплайна | Auth failure, schema mismatch (Gold), БД недоступна |
| **Recoverable** | Retry (max 3, backoff 2.0, jitter 0.1-0.5s) | 429 Rate Limit, 502/504 Timeout |
| **Data Quality** | Лог + пропуск записи | Невалидный SMILES, missing field |

### 3.2. Пороги

| Порог | Условие | Действие |
|-------|---------|----------|
| Soft | >5% DQ errors | Warning |
| Hard | >20% DQ errors | Fail Batch |

### 3.3. Circuit Breaker

См. [ADR-007](docs/02-architecture/decisions/ADR-007-circuit-breaker-implementation.md).

| Параметр | Значение |
|----------|----------|
| Trigger | 5 consecutive errors |
| Open Duration | 5 мин |
| Recovery | Half-Open → 1 probe → Closed/Open |
| Metric | `circuit_breaker_state` (0=Closed, 1=Half-Open, 2=Open) |

### 3.4. Graceful Shutdown

См. [ADR-008](docs/02-architecture/decisions/ADR-008-graceful-shutdown-strategy.md).

При получении SIGTERM/SIGINT:
1. Прекратить извлечение новых записей
2. Дождаться завершения записи текущего батча
3. Сохранить локальный чекпоинт
4. Выйти с кодом 0

---

## 4. Блокировки (Locking)

> **Note: Local-Only Deployment** (см. [ADR-010](docs/02-architecture/decisions/ADR-010-local-only-deployment.md))

| Параметр | Значение |
|----------|----------|
| Механизм | In-memory (`MemoryLock`) |
| Scope | Один процесс Python |
| Max Duration | 4 часа |

**Invariant**: Потеря блокировки = аварийное завершение ДО попытки записи данных.

### Lock Keys

- Incremental: `lock:{provider}_{entity}`
- Backfill/Rebuild: `lock:{provider}_{entity}:exclusive`

---

## 5. Observability

### 5.1. Log Schema (MUST)

```json
{
  "ts": "2025-12-15T10:00:00Z",
  "level": "INFO",
  "run_id": "uuid",
  "pipeline": "chembl_activity",
  "stage": "extract|transform|load",
  "dataset": "chembl.activity",
  "record_count": 1000
}
```

### 5.2. Retention

| Артефакт | Срок |
|----------|------|
| Logs | 30 дней |
| Metrics | 90 дней |

### 5.3. Provider Health

| Status | Условие | Действие |
|--------|---------|----------|
| Healthy | 0 errors | Normal |
| Degraded | 1-2 errors | Timeout ×2, batch_size ÷2 |
| Unhealthy | ≥3 errors | Pause, Alert P2 |

---

## 6. Security

### 6.1. PII Handling

| Слой | Обработка |
|------|-----------|
| Bronze | Как есть (Internal) |
| Silver | `sha256(lowercase(value) + SALT)` — **salted обязательно** |
| Gold | Исключить или агрегировать |

### 6.2. Secrets

- **Source**: `os.environ`
- **Format**: `BIOETL_{PROVIDER}_{KEY}`
- **MUST NOT**: hardcode, `.env` в git

---

## 7. Тестирование

| Уровень | Директория | Правила |
|---------|------------|---------|
| **Unit** | `tests/unit/` | Изолированные, in-memory fakes. **БЕЗ моков** внешних библиотек. |
| **Integration** | `tests/integration/` | VCR.py для HTTP. Очистка секретов из кассет. |
| **E2E** | `tests/e2e/` | `@pytest.mark.e2e`, in-memory инфраструктура |
| **Architecture** | `tests/architecture/` | Проверка слоёв, imports, именования |

**Инструменты:** `pytest`, `pytest-asyncio`, `pytest-cov`, `hypothesis` (property-based)
**Цель покрытия:** >80% line coverage

### Команды

```bash
make test                 # Все тесты с coverage
make test-unit            # Только unit
make test-integration     # Integration с VCR
make arch-test            # Architecture tests
make arch-lint            # import-linter contracts
```

### VCR.py (MUST)

- Кассеты: `tests/fixtures/vcr/`
- Санитизация: `Authorization`, `X-API-Key`, PII в `before_record`
- CI: `pytest --vcr-record=none`

---

## 8. Стек Технологий

> **Note: Local-Only Deployment** (см. [ADR-010](docs/02-architecture/decisions/ADR-010-local-only-deployment.md))

| Категория | Инструмент | Назначение |
|-----------|------------|------------|
| **HTTP** | httpx (async) | HTTP-клиент |
| **Data** | Polars, Delta Lake | Обработка, хранение |
| **Validation** | Pandera | Валидация схем |
| **Linting** | Ruff + mypy | Код и типы |
| **Locks** | MemoryLock (in-process) | Конкурентный доступ |
| **Checkpoints** | LocalCheckpoint | Локальные чекпоинты в JSON |

### Legacy Wrappers (MUST)

```python
await loop.run_in_executor(thread_pool, fetch_func)
```

---

## 9. Провайдеры

| Provider | Library | Rate Limit | Health Check |
|----------|---------|------------|--------------|
| ChEMBL | chembl_webresource_client | None | `/chembl/api/data/status.json` |
| PubChem | pubchempy | 5 req/sec | Lightweight compound query |
| UniProt | unipressed | 100 req/sec (API key) | `/rest/beta/health` |
| OpenAlex | pyalex | 10 req/sec | Generic Probe |
| Semantic Scholar | semanticscholar | 100 req/5min | Generic Probe |
| PubMed | biopython | 3 req/sec (10 w/ key) | Generic Probe |
| Crossref | habanero | 50 req/sec | Generic Probe |

---

## 10. Anti-Patterns (ЗАПРЕЩЕНО)

### Архитектура
- ❌ Импорт `infrastructure` в `domain` или `application`
- ❌ Создание зависимостей внутри классов

### Код
- ❌ Sentinel values (`-1`, `"N/A"`, `9999`) → Использовать `None`
- ❌ Блокирующий I/O в async (`requests.get()`) → `httpx.AsyncClient` или `run_in_executor`
- ❌ Хардкод секретов → `os.environ`, формат: `BIOETL_{PROVIDER}_{KEY}`
- ❌ `print()` → `structlog` с `run_id`

### Тесты
- ❌ Мокинг доменных сущностей → Реальные Value Objects
- ❌ HTTP без VCR → VCR-кассеты обязательны
- ❌ Секреты в кассетах → Очистка в `before_record`

---

## 11. Чек-Лист Self-Review

### Архитектура
- [ ] Нет запрещённых импортов между слоями
- [ ] Зависимости инжектируются через конструктор
- [ ] `composition/` — единственное место сборки

### Код
- [ ] `make lint` проходит без ошибок
- [ ] Типизация полная (нет `Any` без причины)
- [ ] Логирование через `structlog`, везде `run_id`
- [ ] Нет хардкода секретов, путей, конфигурации

### Тесты
- [ ] `make test` проходит ДО и ПОСЛЕ изменений
- [ ] Для новой логики есть unit-тесты
- [ ] Для HTTP есть integration-тесты с VCR
- [ ] VCR-кассеты очищены от секретов

### Документация
- [ ] `docs/` обновлена при изменениях архитектуры/конфигурации
- [ ] Docstrings в Google Style (на русском)

---

## 12. Ключевые Файлы

| Артефакт | Путь |
|----------|------|
| Domain Ports | `src/bioetl/domain/ports.py` |
| Adapters | `src/bioetl/infrastructure/adapters/{provider}/` |
| Pipelines | `src/bioetl/application/pipelines/` |
| Pipeline Core | `src/bioetl/application/core/` |
| BaseTransformer | `src/bioetl/application/core/base_transformer.py` |
| Factories | `src/bioetl/composition/factories/` |
| Bootstrap | `src/bioetl/composition/bootstrap.py` |
| CLI | `src/bioetl/interfaces/cli.py` |
| Configs | `configs/pipelines/{provider}/{entity}.yaml` |
| Tests | `tests/` |
| VCR Cassettes | `tests/fixtures/vcr/` |

---

## 13. Governance (RFC 2119)

| Keyword | Значение |
|---------|----------|
| **MUST** | Абсолютное требование. Нарушение = блокер релиза. |
| **SHOULD** | Сильная рекомендация. Отклонение требует обоснования в PR. |
| **MAY** | Опционально. |

---

## 14. Disaster Recovery

| Параметр | Значение |
|----------|----------|
| RPO | 24 часа |
| RTO | 4 часа |
| Game Days | Ежегодно (SHOULD) |

---

## 15. Git Workflow (Conventional Commits)

```
<type>(<scope>): <description>
```

| Тип | Описание |
|-----|----------|
| `feat` | Новая функциональность |
| `fix` | Исправление бага |
| `refactor` | Рефакторинг |
| `docs` | Документация |
| `test` | Тесты |
| `chore` | Прочее |

---

## 16. Диагностика

| Ошибка | Решение |
|--------|---------|
| `ImportError: cannot import from domain` | Проверь матрицу импортов |
| `RuntimeError: Event loop is closed` | Используй `run_in_executor` |
| Тесты падают в CI | Запиши VCR-кассету |
| Неясности в задаче | **СПРОСИ ПОЛЬЗОВАТЕЛЯ** |

---

## 17. Полная Документация

| Документ | Описание |
|----------|----------|
| `CLAUDE.md` | Справочник для Claude Code |
| `AGENT.md` | Детальные инструкции для агента v2.2 |
| `docs/RULES.md` | Конституция проекта v5.2 |
| `docs/REQUIREMENTS.md` | 127 тестируемых требований |
| `docs/CHANGELOG.md` | История изменений |
| `docs/02-architecture/decisions/` | ADR (001-011) |

---

## Приоритеты при Разработке

1. **Безопасность**: Секреты, PII, IAM
2. **Надёжность**: Lock invariants, graceful shutdown, idempotency
3. **Observability**: Structured logs, metrics, correlation ID
4. **Производительность**: Delta VACUUM, партиционирование, rate limiting
5. **Поддерживаемость**: Type safety, contracts, testing

---

*Строй надёжно. Документируй честно. Спрашивай смело.*
