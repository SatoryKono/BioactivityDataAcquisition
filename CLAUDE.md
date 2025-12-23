# CLAUDE.md

Справочник для Claude Code при работе с репозиторием BioETL.

*Синхронизировано с RULES.md v5.1 (2025-12-22)*

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

# После изменений
make lint && make test
```

**Главные ресурсы:**
1. `docs/RULES.md` — Конституция проекта (RFC 2119 keywords)
2. `.claude/PROJECT_CONTEXT.md` — Компактный контекст
3. `AGENT.md` — Детальные инструкции для агента

---

## 1. Описание Проекта

**BioETL** — фреймворк для сбора, нормализации и обработки биоактивных данных из публичных репозиториев (ChEMBL, PubChem, UniProt) в унифицированное Delta Lake хранилище.

| Аспект | Описание |
|--------|----------|
| **Архитектура** | Ports & Adapters (Hexagonal) + Medallion |
| **Язык** | Python 3.11+ |
| **Стиль документации** | Русский, RFC 2119 keywords |

---

## 2. Архитектура Слоёв

```
src/bioetl/
├── domain/          # Чистая логика, Protocols (Ports), бизнес-модели. БЕЗ I/O.
├── application/     # Пайплайны, Use Cases, оркестрация
├── composition/     # Composition Root (DI-контейнер, factories, bootstrap)
├── infrastructure/  # Адаптеры (HTTP, локальное хранилище), реализация портов
└── interfaces/      # CLI, PipelineRunner
```

### 2.1. Матрица Импортов (ОБЯЗАТЕЛЬНО)

| Из ↓ / В → | domain | application | composition | infrastructure | interfaces |
|------------|--------|-------------|-------------|----------------|------------|
| **domain** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **application** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **composition** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **infrastructure** | ✅ | ❌ | ❌ | ✅ | ❌ |
| **interfaces** | ✅ | ✅ | ✅ | ✅ | ✅ |

**Нарушение = Блокер PR.** Проверяется `import-linter` и `tests/architecture/`.

### 2.2. Dependency Injection

- **MUST**: Зависимости передаются в конструктор.
- **MUST NOT**: Создание зависимостей внутри классов (`S3Storage()`, `httpx.AsyncClient()`).
- **Composition Root**: `src/bioetl/composition/bootstrap.py`.

---

## 3. Medallion Architecture

| Уровень | Формат | Хранение | Идемпотентность |
|---------|--------|----------|-----------------|
| **Bronze** | JSONL + zstd | 90d → Archive | Append-only. Path: `bronze/v1/{provider}/{entity}/{date}/` |
| **Silver** | Delta Lake | Permanent | Merge/Upsert по `content_hash`. ACID обязателен. |
| **Gold** | Delta/Parquet | Permanent | SCD Type 2 или партиции по дате |

### 3.1. Delta Lake (MUST)

- **Engine**: `delta-rs` (Rust core)
- **VACUUM**: Еженедельно, `retention_period=7 days`
- **Forensic Retention**: 7d default, 30d для critical таблиц

### 3.2. Content Hash

```
sha256(provider + canonical_json(record))
```

**Нормализация перед хэшем:**
- NaN/Inf → `null`
- Floats → `round(val, 10)`
- Dates → ISO `YYYY-MM-DD`
- Strings → `strip()`
- **Исключить**: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_*`

---

## 4. Обработка Ошибок

### 4.1. Классификация

| Тип | Поведение | Пример |
|-----|-----------|--------|
| **Critical** | Падение пайплайна | Auth failure, schema mismatch (Gold), БД недоступна |
| **Recoverable** | Retry (max 3, backoff 2.0, jitter 0.1-0.5s) | 429 Rate Limit, 502/504 Timeout |
| **Data Quality** | Лог + пропуск записи | Невалидный SMILES, missing field |

### 4.2. Пороги

| Порог | Условие | Действие |
|-------|---------|----------|
| Soft | >5% DQ errors | Warning |
| Hard | >20% DQ errors | Fail Batch |

### 4.3. Circuit Breaker

См. [ADR-007](docs/02-architecture/decisions/ADR-007-circuit-breaker-implementation.md).

- **Trigger**: 5 consecutive errors
- **Open Duration**: 5 мин
- **Recovery**: Half-Open → 1 probe → Closed/Open
- **Observability**: Метрики `circuit_breaker_state`, `trips_total`

### 4.4. Graceful Shutdown

См. [ADR-008](docs/02-architecture/decisions/ADR-008-graceful-shutdown-strategy.md).

При получении SIGTERM/SIGINT:
1. Прекратить извлечение новых записей
2. Дождаться завершения записи текущего батча
3. Сохранить чекпоинт локально
4. Выйти с кодом 0

---

## 5. Блокировки (Locking)

| Параметр | Значение |
|----------|----------|
| Механизм | In-memory (MemoryLock) |
| Область | Локальный процесс |

**Примечание**: Для локального развертывания используется in-memory блокировка.
Распределённые блокировки не требуются, так как пайплайны запускаются локально.

### Lock Keys

- Incremental: `lock:{provider}_{entity}`
- Backfill/Rebuild: `lock:{provider}_{entity}:exclusive`

---

## 6. Тестирование

| Уровень | Директория | Правила |
|---------|------------|---------|
| **Unit** | `tests/unit/` | Изолированные, in-memory fakes. **БЕЗ моков** внешних библиотек. |
| **Integration** | `tests/integration/` | VCR.py для HTTP. Очистка секретов из кассет. |
| **E2E** | `tests/e2e/` | `@pytest.mark.e2e`, in-memory инфраструктура |
| **Architecture** | `tests/architecture/` | Проверка слоёв, imports, именования |

**Инструменты:** `pytest`, `pytest-asyncio`, `pytest-cov`, `hypothesis` (property-based)
**Цель покрытия:** >80% line coverage (проверяется в CI через `--cov-fail-under=80`)

### Команды

```bash
make test                 # Все тесты с coverage
make test-unit            # Только unit (быстро)
make test-integration     # Integration с VCR
make arch-test            # Architecture tests
make arch-lint            # import-linter contracts

# Один тест
.venv/Scripts/python -m pytest tests/unit/domain/test_types.py -v
```

### VCR.py (MUST)

- Кассеты: `tests/fixtures/vcr/`
- Санитизация: `Authorization`, `X-API-Key`, PII в `before_record`
- CI: `pytest --vcr-record=none` (падать при отсутствии кассеты)

---

## 7. Стек Технологий

| Категория | Инструмент | Назначение |
|-----------|------------|------------|
| **HTTP** | httpx (async) | HTTP-клиент |
| **Data** | Polars, Delta Lake | Обработка, хранение |
| **Storage** | Локальная ФС | Bronze/Silver/Gold/Checkpoints |
| **Validation** | Pandera | Валидация схем |
| **Linting** | Ruff + mypy | Код и типы |
| **CLI** | Click | Командный интерфейс |

### Legacy Wrappers (MUST)

Библиотеки без async (pubchempy, biopython):
```python
await loop.run_in_executor(None, func, *args)
```

**Строгий режим:** `BIOETL_STRICT_ERROR_HANDLING=true` → raise, иначе warning

---

## 8. Провайдеры

| Provider | Library | Rate Limit | Health Check |
|----------|---------|------------|--------------|
| ChEMBL | chembl_webresource_client | None | `/chembl/api/data/status.json` |
| PubChem | pubchempy | 5 req/sec | Lightweight compound query |
| UniProt | unipressed | 100 req/sec (API key) | Search Probe |

---

## 9. Ключевые Файлы

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
| ADR | `docs/02-architecture/decisions/` |

---

## 10. Governance (RFC 2119)

| Keyword | Значение |
|---------|----------|
| **MUST** | Абсолютное требование. Нарушение = блокер релиза. |
| **SHOULD** | Сильная рекомендация. Отклонение требует обоснования в PR. |
| **MAY** | Опционально. |

---

## 11. Anti-Patterns (ЗАПРЕЩЕНО)

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

## 12. Чек-Лист Self-Review

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

## 13. Git Workflow

### Формат Коммитов (Conventional Commits)

```
<type>(<scope>): <description>
```

| Тип | Описание |
|-----|----------|
| `feat` | Новая функциональность |
| `fix` | Исправление бага |
| `refactor` | Рефакторинг без изменения поведения |
| `docs` | Документация |
| `test` | Тесты |
| `chore` | Прочее (CI, deps) |

**Примеры:**
- `feat(chembl): add activity pipeline`
- `fix(pubchem): handle rate limit 429`

### Перед Коммитом

```bash
make lint
make test
git status
git diff --staged
git commit -m "..."
```

---

## 14. Создание Компонентов

### 14.1. Новый Адаптер

1. **Порт:** Убедись, что в `domain/ports.py` есть подходящий `Protocol`
2. **Адаптер:** Создай класс в `src/bioetl/infrastructure/adapters/{provider}/`
3. **Требования:**
   - **MUST** реализовывать порт
   - **MUST** принимать зависимости в `__init__`
   - **MUST** реализовывать `health_check()`
   - **MUST** соблюдать rate limits провайдера

### 14.2. Новый Пайплайн

1. **Конфиг:** `configs/pipelines/{provider}/{entity}.yaml`
2. **Трансформер:** Наследуй от `BaseTransformer` (`src/bioetl/application/core/base_transformer.py`)
3. **Пайплайн:** `src/bioetl/application/pipelines/`
4. **Фабрика:** `src/bioetl/composition/factories/`
5. **Регистрация:** `PipelineRegistry` (декоратор `@register`)
6. **Тесты:** unit + integration

---

## 15. Диагностика и Эскалация

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `ImportError: cannot import from domain` | Нарушение слоёв | Проверь матрицу импортов |
| `RuntimeError: Event loop is closed` | Блокирующий I/O в async | Используй `run_in_executor` |
| Тесты падают в CI, но не локально | Отсутствует VCR-кассета | Запиши кассету |
| Неясности в задаче | — | **СПРОСИ ПОЛЬЗОВАТЕЛЯ** |

---

## 16. Полная Документация

| Документ | Описание |
|----------|----------|
| `docs/RULES.md` | Конституция проекта v5.1 |
| `docs/REQUIREMENTS.md` | 127 тестируемых требований |
| `docs/CHANGELOG.md` | История изменений |
| `docs/02-architecture/decisions/` | ADR (001-009) |
| `AGENT.md` | Детальные инструкции для агента v2.1 |
| `.claude/PROJECT_CONTEXT.md` | Компактный контекст |

---

*Строй надёжно. Документируй честно. Спрашивай смело.*