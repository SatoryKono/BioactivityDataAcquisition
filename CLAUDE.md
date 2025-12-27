# CLAUDE.md

Справочник для Claude Code при работе с репозиторием BioETL.

*Синхронизировано с RULES.md v5.7 (2025-12-27)*

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
4. `docs/REFACTORING_PLAN.md` — План рефакторинга с верифицированным статусом

> ⚠️ **ОБЯЗАТЕЛЬНО**: Перед предложением задач рефакторинга сверься с секцией
> "ВЕРИФИЦИРОВАННЫЙ СТАТУС РЕАЛИЗАЦИИ" в `docs/REFACTORING_PLAN.md`!

---

## 0. 🛡️ Протокол Обязательной Двойной Верификации (MUST)

> **Цель**: Исключить ложные утверждения о состоянии кодовой базы.
> **Причина**: Анализ 2025-12-27 выявил ~50% ложных утверждений в планах рефакторинга.
> **Регламент**: См. `docs/RULES.md` §7 "Протокол Архитектурных Обзоров" (REQ-ARCH-040)

### Двойная Верификация

При архитектурных обзорах **КАЖДАЯ** найденная проблема проверяется **ДВАЖДЫ**:

| Этап | Когда | Что проверяется |
|------|-------|-----------------|
| **Первая верификация** | Сразу при обнаружении | Размер, структура, делегирование, список ложных утверждений |
| **Вторая верификация** | При написании итогового документа | Точные ссылки `файл:строка`, актуальность, дата проверки |

### 0.1. Перед Любым Утверждением об Архитектуре

**ЗАПРЕЩЕНО** утверждать о компоненте без верификации кодом:

```bash
# Пример: перед утверждением "PipelineRunner — god object"
grep -n "class PipelineRunner" src/bioetl/application/core/runner.py
wc -l src/bioetl/application/core/runner.py  # Проверить размер
grep -n "def " src/bioetl/application/core/runner.py  # Проверить методы
```

### 0.2. Чек-лист Верификации Перед Рефакторингом

| Шаг | Действие | Команда |
|-----|----------|---------|
| 1 | Проверить `REFACTORING_PLAN.md` | Секция "ЛОЖНЫЕ УТВЕРЖДЕНИЯ" |
| 2 | Прочитать целевой файл | `Read` tool или `cat` |
| 3 | Измерить размер компонента | `wc -l`, `grep -c "def "` |
| 4 | Проверить делегирование | `grep` по вызовам сервисов |
| 5 | Найти существующие тесты | `tests/unit/` и `tests/architecture/` |

### 0.3. Формат Верифицированного Утверждения

**❌ НЕ делай так:**
> "bootstrap_pipeline смешивает ответственности и требует декомпозиции"

**✅ Делай так:**
> "bootstrap_pipeline (`bootstrap.py:68-167`, 100 строк) делегирует:
> - `bootstrap_observability()` — строка 108
> - `FilterConfigBuilder.build()` — строка 139
> - `factory.create_runner()` — строка 159
>
> **Вывод**: Уже декомпозирован, задача не требуется."

### 0.4. Обязательные Проверки Перед Созданием Задачи

- [ ] Утверждение подкреплено ссылками на `файл:строка`
- [ ] Проверено в `REFACTORING_PLAN.md` → "ЛОЖНЫЕ УТВЕРЖДЕНИЯ"
- [ ] Проверено в `REFACTORING_PLAN.md` → "УЖЕ РЕАЛИЗОВАНО"
- [ ] Измерен размер компонента (строки, методы)
- [ ] Проверено делегирование (какие сервисы вызываются)

### 0.5. Команды Быстрой Верификации

```bash
# Размер файла и количество функций
wc -l src/bioetl/application/core/runner.py
grep -c "def \|async def " src/bioetl/application/core/runner.py

# Проверка делегирования
grep -n "self\._.*\." src/bioetl/application/core/runner.py | head -20

# Проверка импортов (зависимости)
grep "^from\|^import" src/bioetl/application/core/runner.py

# Существующие тесты
ls tests/unit/application/core/test_runner*.py
ls tests/architecture/test_*.py
```

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

### 2.3. ⚠️ Архитектурные Пояснения (Избегай Ложных Выводов)

> **КРИТИЧЕСКИ ВАЖНО**: Эти утверждения часто делаются ошибочно.
> Перед предложением рефакторинга — **ОБЯЗАТЕЛЬНО проверь код**!

| Компонент | ❌ Ложное утверждение | ✅ Реальность |
|-----------|----------------------|---------------|
| **PipelineRunner** | "God object, слишком много ответственностей" | **173 строки**, делегирует через `RunnerServices` bundle (`runner.py:84-88`) |
| **bootstrap_pipeline** | "Смешивает сборку и бизнес-логику" | Тонкий фасад, делегирует фабрикам: `factory.create_runner()` |
| **ChEMBL Adapter** | "Монолит 517 строк, объединяет всё" | **Делегирует** через `EntityMapper` (112 LOC), `ErrorClassifier`, `AdapterMetrics`, `BaseHttpAdapter` (`client.py:30,76-84,90`) |
| **GoldWriter** | "Монолит 593 строки, требует декомпозиции" | **Делегирует** CSV в `CsvExporter`, audit в `AuditPort`. Режимы OVERWRITE/APPEND/SCD2 — когезивны (`gold_writer.py:70-71,87-88`) |
| **CLI** | "Содержит бизнес-логику подтверждений" | Подтверждения — **законная** ответственность interfaces слоя |
| **WriteModePolicy default** | "DeltaWriter нарушает DI" | Опциональный параметр с default — валидный паттерн для value objects |
| **BaseTransformer** | "Нет DQ-валидации" | By design: Template Method. DQ — ответственность конкретных трансформеров |
| **MedallionLifecycle** | "Не использует политики" | Использует `MedallionPolicy.should_clear_silver/gold` |
| **BronzeWriter** | "Нет observability" | Имеет структурированное логирование (`bronze_writer.py:197-205`) |
| **DQ/Medallion политики** | "Нет автоматизации" | Реализовано: `MedallionPolicy`, `DQConfig`, `SilverWriteMode`, `GoldWriteMode` enums |

**Паттерны, которые НЕ являются нарушениями:**

1. **Optional parameters с defaults** (`policy: Policy | None = None`):
   - Валидный DI паттерн для конфигурационных value objects
   - Аналогично `timeout: float = 30.0`

2. **NoOp implementations** (`NoOpTracing`, `NoOpMetrics`):
   - Null Object Pattern для опциональной observability
   - Позволяет domain слою не зависеть от конкретных реализаций

3. **Подтверждения в CLI** (dry-run, confirmation prompts):
   - Ответственность interfaces слоя
   - Другие интерфейсы имеют свои механизмы

4. **Backward-compatibility shims** (`from module import X; __all__ = ["X"]`):
   - Re-export для совместимости — НЕ дублирование
   - Пример: `application/core/medallion_policy.py` (19 строк)

5. **Большой файл с делегированием** (500+ LOC):
   - Размер ≠ god object, если есть делегирование
   - Проверять через `grep "self._" file.py | sort -u`

### 2.3.1. Причины Ложных Утверждений (Избегать!)

> **Статистика**: Анализ 2025-12-27 выявил ~50% ложных утверждений в планах рефакторинга.

| Причина | Пример | Как избежать |
|---------|--------|--------------|
| **Отсутствие верификации кодом** | "Нет валидации X" без `grep` | Всегда проверять код перед утверждением |
| **Ложная корреляция размер → сложность** | "517 LOC = монолит" | Проверять делегирование, не только размер |
| **Неверная интерпретация паттернов** | "NoOp default = нарушение DI" | Знать Null Object Pattern |
| **Устаревшие знания** | "Не реализовано" (но уже реализовано) | Сверяться с `REFACTORING_PLAN.md` |

### 2.3.2. Правило Анализа Делегирования

**ПЕРЕД** утверждением "god object" или "монолит" выполнить:

```bash
# 1. Измерить размер
wc -l src/bioetl/path/to/file.py  # Должно быть > 500 для "монолита"

# 2. Найти делегирование (если много — НЕ монолит!)
grep -o "self\._[a-z_]*" src/bioetl/path/to/file.py | sort -u

# 3. Проверить импорты внешних компонентов
grep "^from\|^import" src/bioetl/path/to/file.py | grep -v "typing\|dataclass"

# 4. Найти количество публичных методов
grep -c "^    def \|^    async def " src/bioetl/path/to/file.py
```

**Критерии "монолита" (ВСЕ должны выполняться):**
- [ ] 500+ строк
- [ ] Мало делегирования (< 3 вызовов `self._component.method()`)
- [ ] Много публичных методов с разной ответственностью
- [ ] Низкая когезия (методы не связаны друг с другом)

### 2.4. 🛡️ Протокол Верификации (ОБЯЗАТЕЛЬНО)

> **КРИТИЧЕСКИ ВАЖНО**: Перед любым утверждением о коде — **ПРОВЕРЬ КОД**!

**MUST выполнять перед предложением рефакторинга:**

```bash
# 1. Проверить существование класса/метода
grep -r "class ClassName" src/bioetl/
grep -r "def method_name" src/bioetl/

# 2. Проверить реализованность фичи
grep -r "SilverWriteMode\|GoldWriteMode" src/bioetl/

# 3. Проверить архитектурные тесты
ls tests/architecture/

# 4. Сверить с REFACTORING_PLAN.md
cat docs/REFACTORING_PLAN.md | head -60
```

**Чек-лист перед утверждением:**

| Утверждение | Верификация |
|-------------|-------------|
| "Класс X существует" | `grep -r "class X" src/` |
| "Метод Y не реализован" | `grep -r "def Y" src/` + прочитать код |
| "Нет теста для Z" | `grep -r "test_Z\|Z" tests/` |
| "Нет валидации W" | Прочитать файл и найти validation logic |

**При обнаружении расхождения:**
1. Обновить `docs/REFACTORING_PLAN.md` → секция "ЛОЖНЫЕ УТВЕРЖДЕНИЯ"
2. Обновить `CLAUDE.md` → секция 2.3 "Архитектурные Пояснения"

---

## 3. Medallion Architecture

| Уровень | Формат | Хранение | Идемпотентность |
|---------|--------|----------|-----------------|
| **Bronze** | JSONL + zstd | 90d → Archive | Append-only. Path: `bronze/v1/{provider}/{entity}/{date}/` |
| **Silver** | Delta Lake | Permanent | Merge/Upsert по `content_hash`. ACID обязателен. |
| **Gold** | Delta/Parquet | Permanent | SCD Type 2 или партиции по дате |

### 3.1. Silver → Gold Transformation

- **Исключение JSON полей**: Конфигурируется в YAML (`gold_filters`)
- **Плоская структура**: Gold содержит только scalar поля
- **Forensic**: Silver сохраняет JSON для расследований
- **Реализация**: `GoldWriter.write_gold()` в `infrastructure/storage/gold_writer.py`

### 3.2. Delta Lake (MUST)

- **Engine**: `delta-rs` (Rust core)
- **VACUUM**: Еженедельно, `retention_period=7 days`
- **Forensic Retention**: 7d default, 30d для critical таблиц

### 3.3. Content Hash

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

| Уровень | Директория | Тестов | Правила |
|---------|------------|--------|---------|
| **Unit** | `tests/unit/` | ~1294 | Изолированные, in-memory fakes предпочтительны, MagicMock допустим. |
| **Integration** | `tests/integration/` | ~80 | VCR.py для HTTP. Очистка секретов из кассет. |
| **E2E** | `tests/e2e/` | - | `@pytest.mark.e2e`, Local-Only архитектура |
| **Architecture** | `tests/architecture/` | 97 | Проверка слоёв, imports, контракты портов |

**Всего тестов:** ~1471+

**Инструменты:** `pytest`, `pytest-asyncio`, `pytest-cov`, `hypothesis` (property-based)
**Цель покрытия:** >80% line coverage (проверяется в CI через `--cov-fail-under=80`)

### Контрактные тесты портов

Файл `tests/architecture/test_port_contracts.py` (51 тест) проверяет:

| Категория | Проверка |
|-----------|----------|
| **Lifecycle** | Все async I/O порты имеют `aclose()` |
| **Observability** | MetricsPort/TracingPort имеют `close()` |
| **Runtime** | Все порты `@runtime_checkable` для isinstance() |
| **Completeness** | Все порты экспортированы в `__all__` |
| **Contracts** | StoragePort, LockPort, CheckpointPort, QuarantinePort методы |

### Тесты детерминизма (REQ-ARCH-030)

Файл `tests/architecture/test_no_random_in_writers.py` проверяет:

| Тест | Проверка |
|------|----------|
| `test_no_random_import_in_storage_writers` | Запрет `import random` и `from random import` в storage writers |
| `test_no_random_uniform_calls_in_storage` | Запрет вызовов `random.uniform()` |
| `test_no_random_choice_calls_in_storage` | Запрет вызовов `random.choice()` |

**Цель:** Гарантировать детерминизм операций записи для воспроизводимости.
См. [ADR-014](docs/02-architecture/decisions/ADR-014-deterministic-writes.md).

Файл `tests/architecture/test_no_datetime_now_in_infrastructure.py` проверяет:

| Тест | Проверка |
|------|----------|
| `test_no_datetime_now_in_infrastructure` | Запрет `datetime.now()` в infrastructure слое |
| `test_allowed_files_still_exist` | Проверка актуальности списка исключений |

**Цель:** Timestamps создаются в application слое и передаются как параметры.

### Команды

```bash
make test                 # Все тесты с coverage
make test-unit            # Только unit (быстро)
make test-integration     # Integration с VCR
make arch-test            # Architecture tests
make arch-lint            # import-linter contracts

# E2E тесты
pytest tests/e2e/ -v -m e2e

# Один тест
.venv/Scripts/python -m pytest tests/unit/domain/test_types.py -v
```

### E2E Тесты

E2E тесты проверяют полный цикл пайплайна от fetch до Gold:

```python
from tests.e2e.conftest import create_test_context, assert_silver_table_has_records
from bioetl.composition.bootstrap import bootstrap_pipeline

ctx = create_test_context("chembl_activity", limit=10)
runner = bootstrap_pipeline(ctx)
await runner.run()
assert_silver_table_has_records(data_dir, "chembl_activity", expected_min=1)
```

**Helpers** (`tests/e2e/conftest.py`):
- `create_test_context(pipeline_name, limit, run_type)` - создание контекста
- `assert_bronze_files_exist(data_dir, provider, entity)` - проверка Bronze
- `assert_silver_table_has_records(data_dir, table_name, expected_min)` - проверка Silver
- `assert_gold_table_has_records(data_dir, table_name, expected_min)` - проверка Gold

### VCR.py (MUST)

- Кассеты: `tests/fixtures/vcr/`
- Санитизация: `Authorization`, `X-API-Key`, PII в `before_record`
- CI: `pytest --vcr-record=none` (падать при отсутствии кассеты)

---

## 7. Стек Технологий

| Категория | Инструмент | Назначение |
|-----------|------------|------------|
| **HTTP** | `UnifiedHTTPClient` (httpx) | Унифицированный HTTP-клиент для всех адаптеров |
| **Data** | Polars, Delta Lake | Обработка, хранение |
| **Storage** | Локальная ФС | Bronze/Silver/Gold/Checkpoints |
| **Validation** | Pandera | Валидация схем |
| **Linting** | Ruff + mypy | Код и типы |
| **CLI** | Click | Командный интерфейс |

### Унифицированный HTTP-клиент

**Все адаптеры используют единую HTTP-инфраструктуру:**

| Адаптер | Базовый класс | HTTP-клиент |
|---------|---------------|-------------|
| ChemblAdapter | `BaseHttpAdapter` | `UnifiedHTTPClient` |
| UniProtAdapter | `BaseHttpAdapter` | `UnifiedHTTPClient` |
| PubMedAdapter | `@dataclass` | `UnifiedHTTPClient` |
| PubChemAdapter | `BaseSyncAdapter` | `pubchempy` + ThreadPool |

**Компоненты:** Rate Limiter, Circuit Breaker, Retry Logic, Metrics.

### Legacy Wrappers (MUST)

Библиотеки без async (pubchempy) используют `BaseSyncAdapter`:
```python
# BaseSyncAdapter автоматически оборачивает sync-вызовы
await self._run_in_executor(sync_func, *args)
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
| Domain Ports | `src/bioetl/domain/ports/` (пакет с фасадом `__init__.py`) |
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
- ❌ Прямой импорт `structlog` в `application` или `interfaces` → Использовать `LoggerPort`

### Код
- ❌ Sentinel values (`-1`, `"N/A"`, `9999`) → Использовать `None`
- ❌ Блокирующий I/O в async (`requests.get()`) → `httpx.AsyncClient` или `run_in_executor`
- ❌ Хардкод секретов → `os.environ`, формат: `BIOETL_{PROVIDER}_{KEY}`
- ❌ `print()` → `structlog` с `run_id`

### Тесты
- ⚠️ Мокинг доменных сущностей → Реальные Value Objects предпочтительны, MagicMock допустим
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

1. **Порт:** Убедись, что в `domain/ports/` есть подходящий `Protocol` (импортируй из фасада: `from bioetl.domain.ports import ...`)
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
| `docs/RULES.md` | Конституция проекта v5.2 |
| `docs/REQUIREMENTS.md` | 127 тестируемых требований |
| `docs/CHANGELOG.md` | История изменений |
| `docs/02-architecture/decisions/` | ADR (001-010) |
| `AGENT.md` | Детальные инструкции для агента v2.2 |
| `.claude/PROJECT_CONTEXT.md` | Компактный контекст |

---

*Строй надёжно. Документируй честно. Спрашивай смело.*