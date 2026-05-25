# CLAUDE.md

*Статус: internal-published (Internal / Extended)*

Справочник для Claude Code при работе с репозиторием BioETL.

*Синхронизировано с RULES.md v6.1.3 (2026-04-29) | Дедублирование: ссылки на RULES.md вместо копий | Версия: 6.7.0*

> **Runtime-specific note:** orchestration guidance for Claude lives in
> runtime-specific orchestration copy. Codex keeps its own runtime-specific
> source-of-truth in `.codex/agents/ORCHESTRATION.md`, so version skew between
> those files is not automatically a docs defect.

______________________________________________________________________

## TL;DR — Быстрый Старт

```bash
# Поддерживаемый bootstrap path
make install
make test-deps
make setup-plugins

# Проверка перед работой
make lint && make test

# Основные команды
make install          # Создание venv и установка зависимостей
make test             # Локальный стабильный прогон (без E2E)
make lint             # ruff + mypy
make run-local        # Сэмпловый pipeline-run (chembl_activity, limit=10)

# После изменений
make lint && make test
```

`scripts/engineering/dev/dev_setup.sh` остаётся legacy placeholder и не считается
поддерживаемым onboarding path.

### Mixed Windows + WSL checkout

Если один и тот же checkout используется из PowerShell и WSL, не дели одну
`.venv` между ОС. Поддерживаемый путь:

```powershell
.\scripts\engineering\dev\setup_env_windows.ps1
.\scripts\engineering\dev\run_pytest.ps1 tests\ --timeout=120 -n 4 --lf
.\scripts\engineering\dev\run_mypy.ps1
```

```bash
bash scripts/engineering/dev/setup_env_wsl.sh
bash scripts/engineering/dev/run_pytest.sh tests/ --timeout=120 -n 4 --lf
bash scripts/engineering/dev/run_mypy.sh
```

В mixed checkout `make lint` и `make test` остаются валидными repository checks,
но wrappers предпочтительнее, потому что используют OS-specific окружение:
`.venv-win` в PowerShell и `${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}` в WSL.

**Главные ресурсы:**

1. `docs/00-project/RULES.md` — Конституция проекта (RFC 2119 keywords)
1. `docs/00-project/ai/memory/agent-memory.md` — Компактный контекст
1. `AGENT.md` — Детальные инструкции для агента
1. `docs/03-guides/dashboards/dashboard-extension-llm.md` — если задача затрагивает `grafana/dashboards/*.json`, links или drilldown в Grafana
1. `docs/99-archive/refactoring-plan.md` — Архив плана рефакторинга (исторический справочник, optional)

> ⚠️ **ОБЯЗАТЕЛЬНО**: Перед предложением задач рефакторинга опирайся на код,
> active docs в `docs/00-05` и текущие review artifacts. Архивный
> `docs/99-archive/refactoring-plan.md` можно использовать только как historical context.

______________________________________________________________________

## 0. 🛡️ Протокол Обязательной Двойной Верификации (MUST)

> **Цель**: Исключить ложные утверждения о состоянии кодовой базы.
> **Причина**: Анализ 2025-12-27 выявил ~50% ложных утверждений в планах рефакторинга.
> **Регламент**: См. `docs/00-project/RULES.md` §7 "Протокол Архитектурных Обзоров" (REQ-ARCH-040)

### Двойная Верификация

При архитектурных обзорах **КАЖДАЯ** найденная проблема проверяется **ДВАЖДЫ**:

| Этап                   | Когда                             | Что проверяется                                             |
| ---------------------- | --------------------------------- | ----------------------------------------------------------- |
| **Первая верификация** | Сразу при обнаружении             | Размер, структура, делегирование, список ложных утверждений |
| **Вторая верификация** | При написании итогового документа | Точные ссылки `файл:строка`, актуальность, дата проверки    |

### 0.1. Перед Любым Утверждением об Архитектуре

**ЗАПРЕЩЕНО** утверждать о компоненте без верификации кодом:

```bash
# Пример: перед утверждением "PipelineRunner — god object"
grep -n "class PipelineRunner" src/bioetl/application/core/runner.py
wc -l src/bioetl/application/core/runner.py  # Проверить размер
grep -n "def " src/bioetl/application/core/runner.py  # Проверить методы
```

### 0.2. Чек-лист Верификации Перед Рефакторингом

| Шаг | Действие                                           | Команда                               |
| --- | -------------------------------------------------- | ------------------------------------- |
| 1   | Проверить активные docs и текущие review artifacts | RULES / ADR / task report             |
| 2   | Прочитать целевой файл                             | `Read` tool или `cat`                 |
| 3   | Измерить размер компонента                         | `wc -l`, `grep -c "def "`             |
| 4   | Проверить делегирование                            | `grep` по вызовам сервисов            |
| 5   | Найти существующие тесты                           | `tests/unit/` и `tests/architecture/` |

### 0.3. Формат Верифицированного Утверждения

**❌ НЕ делай так:**

> "bootstrap-pipeline смешивает ответственности и требует декомпозиции"

**✅ Делай так:**

> "bootstrap-pipeline рефакторирован в `composition/bootstrap/` (directory),
> делегирует через sub-modules: `assembly/`, `cli/`, `runtime/`.
>
> **Вывод**: Уже декомпозирован, задача не требуется."

### 0.4. Обязательные Проверки Перед Созданием Задачи

- [ ] Утверждение подкреплено ссылками на `файл:строка`
- [ ] Проверено по коду и active docs
- [ ] При необходимости сверено с historical false-positive ledger
- [ ] Измерен размер компонента (строки, методы)
- [ ] Проверено делегирование (какие сервисы вызываются)

### 0.5. Команды Быстрой Верификации

```bash
# Размер файла и количество функций
wc -l src/bioetl/application/core/runner.py
grep -c "def \|async def " src/bioetl/application/core/runner.py

# Проверка делегирования
grep -n "self\.-.*\." src/bioetl/application/core/runner.py | head -20

# Проверка импортов (зависимости)
grep "^from\|^import" src/bioetl/application/core/runner.py

# Существующие тесты
ls tests/unit/application/core/test-runner*.py
ls tests/architecture/test-*.py
```

______________________________________________________________________

## 1. Описание Проекта

**BioETL** — фреймворк для сбора, нормализации и обработки биоактивных данных из публичных репозиториев (ChEMBL, PubChem, UniProt, CrossRef, OpenAlex, PubMed, SemanticScholar) в унифицированное Delta Lake хранилище.

| Аспект                 | Описание                                 |
| ---------------------- | ---------------------------------------- |
| **Архитектура**        | Ports & Adapters (Hexagonal) + Medallion |
| **Язык**               | Python 3.11+                             |
| **Стиль документации** | Русский, RFC 2119 keywords               |

### 1.1. Ориентиры Кодовой Базы (проверять live)

| Метрика                   | Значение                                                                                                    |
| ------------------------- | ----------------------------------------------------------------------------------------------------------- |
| **Python-файлы**          | Считай live для текущей ветки; для быстрого total используй `find ... -name '*.py'` с последующим подсчётом |
| **Строки кода**           | Не полагайся на snapshot-оценки; измеряй live только для конкретного scope                                  |
| **Тестовый объём**        | Проверяй live через `pytest --collect-only` или подсчёт `test_`-функций в целевом дереве                    |
| **ADR**                   | Используй текущий список файлов в `docs/02-architecture/decisions/`, не фиксируй диапазон без live-проверки |
| **Провайдеров**           | 7                                                                                                           |
| **Pipeline-конфигурации** | Сверяй live по `configs/entities/` и `configs/composites/`                                                  |
| **Конфиг-файлы всего**    | Считай live по актуальному набору `configs/**/*.yaml`                                                       |

______________________________________________________________________

## 2. Архитектура Слоёв

> **Полная документация**: См. `docs/00-project/RULES.md` §1 "Архитектура и Слои"

```
src/bioetl/
├── domain/          # Чистая логика, Protocols (Ports), бизнес-модели. БЕЗ I/O.
├── application/     # Пайплайны, Use Cases, оркестрация
├── composition/     # Composition Root (DI-контейнер, factories, bootstrap)
├── infrastructure/  # Адаптеры (HTTP, локальное хранилище), реализация портов
└── interfaces/      # CLI, PipelineRunner
```

**Ключевые ограничения** (детали в `RULES.md` §1.1):

- **Матрица импортов**: `domain` ← `application` ← `composition` → `infrastructure`; `interfaces` может импортировать `domain`, `application` и `composition`, но не `infrastructure` напрямую
- **Нарушение = Блокер PR**. Проверяется `import-linter` и `tests/architecture/`
- **DI**: Зависимости передаются в конструктор. `composition/bootstrap/` — единственное место сборки

### 2.3. ⚠️ Архитектурные Пояснения (Избегай Ложных Выводов)

> **КРИТИЧЕСКИ ВАЖНО**: Эти утверждения часто делаются ошибочно.
> Перед предложением рефакторинга — **ОБЯЗАТЕЛЬНО проверь код**!

| Компонент                   | ❌ Ложное утверждение                                     | ✅ Реальность                                                                                                                                                                                                |
| --------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Email в config/adapters** | "PII поля (email) требуют хэширования HashService"        | **НЕ PII**: `default-email` — технический идентификатор для NCBI API, не персональные данные. NCBI требует email для идентификации инструмента. См. `config.py:364-371`, `pubmed_client.py:38-42`            |
| **PipelineRunner**          | "God object, слишком много ответственностей"              | **189 строк**, делегирует через `PipelineServices` bundle (`runner.py:54,89`)                                                                                                                                |
| **bootstrap-pipeline**      | "Смешивает сборку и бизнес-логику"                        | Тонкий фасад, делегирует фабрикам: `factory.create-runner()`                                                                                                                                                 |
| **ChEMBL Adapter**          | "Монолит 517 строк, объединяет всё"                       | **1124 строки**, делегирует через `EntityMapper`, `ErrorClassifier`, `AdapterMetrics`, `BaseHttpAdapter` (`client.py`)                                                                                       |
| **GoldWriter**              | "Монолит 593 строки, требует декомпозиции"                | **938 строк**, делегирует CSV в `CsvExporter`, audit в `AuditPort`. Режимы OVERWRITE/APPEND/SCD2 — когезивны (`gold_writer.py`)                                                                              |
| **CLI**                     | "Содержит бизнес-логику подтверждений"                    | Подтверждения — **законная** ответственность interfaces слоя                                                                                                                                                 |
| **WriteModePolicy default** | "DeltaWriter нарушает DI"                                 | Опциональный параметр с default — валидный паттерн для value objects                                                                                                                                         |
| **BaseTransformer**         | "Нет DQ-валидации"                                        | By design: Template Method. DQ — ответственность конкретных трансформеров                                                                                                                                    |
| **MedallionLifecycle**      | "Не использует политики"                                  | Использует `MedallionPolicy.should-clear-silver/gold`                                                                                                                                                        |
| **BronzeWriter**            | "Нет observability"                                       | Имеет структурированное логирование (`bronze_writer.py:197-205`)                                                                                                                                             |
| **DQ/Medallion политики**   | "Нет автоматизации"                                       | Реализовано: `MedallionPolicy`, `DQConfig`, `SilverWriteMode`, `GoldWriteMode` enums                                                                                                                         |
| **bootstrap-pipeline**      | "140+ строк, усложняет тестирование"                      | Рефакторинг в `composition/bootstrap/` (directory с `assembly/`, `cli/`, `runtime/`), делегирует через фабрики и helper-функции                                                                              |
| **RecordProcessor**         | "Совмещает метрики/карантин/запись"                       | **Делегирует** в `BatchMetricsRecorder`, `BatchTransformer`, `BatchWriter`, `QuarantineManager` (`record_processor.py:59-85`)                                                                                |
| **PipelineRunner**          | "Не выпускает метрики по стадиям"                         | Использует `PipelineObserver` через `PipelineServices` (`runner.py:89`)                                                                                                                                      |
| **Write mode validation**   | "Нет валидации через Enum"                                | **Реализовано**: `SilverWriteMode`, `GoldWriteMode` enums (`delta_writer.py:53-64`, `gold_writer.py:42-54`)                                                                                                  |
| **Архитектурные тесты**     | "Не связаны с метриками"                                  | Архитектурные проверки живут в `tests/architecture/`; локально используется `make test-architecture`, в CI — `pytest tests/architecture/` и отдельные targeted gates                                         |
| **MemoryLock**              | "Требуется Redis для распределённых блокировок"           | **MemoryLock достаточен** для локального запуска. Проект **by design** использует локальные пайплайны. См. §5 Блокировки.                                                                                    |
| **MemoryMonitor**           | "Возвращает захардкоженные нули, баг"                     | **Graceful degradation** — возвращает консервативные оценки (50% использования), не нули. Это **валидный паттерн** при недоступности psutil. См. `memory_monitor.py:170-180`                                 |
| **DQ метрики**              | "Не экспортируются в Prometheus"                          | **УЖЕ РЕАЛИЗОВАНО**: `postrun_service.py:158-163` эмитит `dq-soft-threshold-exceeded` (counter), `dq-check-duration-ms` (histogram). `DQConfig` имеет `soft-fail-threshold=0.05`, `hard-fail-threshold=0.20` |
| **protocols.py**            | "Пустой файл с нулевым покрытием"                         | Содержит 4 Protocol: `TransformCallback`, `GoldFilterCallback`, `GoldTransformCallback`, `TransformerPort`. См. `application/core/protocols.py`                                                              |
| **Coverage gate**           | "Нет coverage gate в CI, нужно добавить --cov-fail-under" | **УЖЕ РЕАЛИЗОВАНО**: `Makefile:63` (`--cov-fail-under=85`), `.github/workflows/tests.yml:158`. Верификация: 2026-01-06                                                                                       |
| **OTLPSpanExporter**        | "Ошибка Optional-аннотации, mypy --strict падает"         | **ОШИБОК НЕТ**: `uv run mypy src/bioetl --strict` → "Success: no issues found in 326 source files". Код в `tracing.py:36-44` корректен. Верификация: 2025-12-31                                              |
| **OpenTelemetryTracer**     | "Типизация сломана, mypy --strict не проходит"            | **ОШИБОК НЕТ**: mypy strict проходит без ошибок. Верификация: 2025-12-31                                                                                                                                     |

**Паттерны, которые НЕ являются нарушениями:**

1. **Optional parameters с defaults** (`policy: Policy | None = None`):

   - Валидный DI паттерн для конфигурационных value objects
   - Аналогично `timeout: float = 30.0`

1. **NoOp implementations** (`NoOpTracing`, `NoOpMetrics`):

   - Null Object Pattern для опциональной observability
   - Позволяет domain слою не зависеть от конкретных реализаций

1. **Подтверждения в CLI** (dry-run, confirmation prompts):

   - Ответственность interfaces слоя
   - Другие интерфейсы имеют свои механизмы

1. **Backward-compatibility shims** (`from module import X; __all__ = ["X"]`):

   - Re-export для совместимости — НЕ дублирование
   - Пример: `application/services/medallion_lifecycle.py`

1. **Большой файл с делегированием** (500+ LOC):

   - Размер ≠ god object, если есть делегирование
   - Проверять через `grep "self.-" file.py | sort -u`

1. **Graceful degradation в MemoryMonitor**:

   - При недоступности psutil возвращает **консервативные оценки** (50% памяти), не нули

1. **Test scaffolding и stdlib/value-object construction**:

   - `MagicMock`, `AsyncMock`, `SimpleNamespace`, direct state/value-object setup
     в `tests/**` не являются `AP-001`
   - `Path(...)` / `str(...)` / simple normalization helpers не являются
     hard-coded DI, если не создают service dependency
   - создание `TracerProvider`, `AnomalyDetector`, `ArrowDataConverter`,
     `RetentionPolicy` внутри `infrastructure/**` само по себе не является
     DI-нарушением
   - Это **безопасный fallback** — лучше переоценить нагрузку, чем недооценить
   - Реализация: `memory_monitor.py:170-180` (`-get-stats-estimate`)
   - **НЕ баг**, а продуманное поведение для кросс-платформенности

1. **DQ метрики уже реализованы**:

   - `DQConfig` в `domain/config.py:28-40` с `soft-fail-threshold=0.05`, `hard-fail-threshold=0.20`
   - `postrun_service.py:122-163` проверяет пороги и эмитит метрики
   - Счётчик `dq-soft-threshold-exceeded` и гистограмма `dq-check-duration-ms`
   - **НЕ требуется** дополнительная реализация

1. **Click для CLI (а не Typer)**:

   - **Осознанный выбор**: Click — зрелый, стабильный CLI-фреймворк
   - **Причины**: (1) Меньше зависимостей (Typer зависит от Click), (2) Обширная документация и community support, (3) Стабильность API между версиями
   - Реализация: `src/bioetl/interfaces/cli/` — все команды используют `@click.command()`, `@click.option()`
   - **НЕ** "альтернатива Typer", а продуманный выбор

1. **Int→Float coercion в Gold-схемах для nullable integers**:

   - Gold-схемы используют `Series[float]` с `coerce=True` для полей, которые в Silver — `pa.int64()`
   - **Осознанное решение**: Pandas/Polars исторически не поддерживали nullable integers без `Int64` (capital I)
   - Float — единственный способ представить `int + NULL` без потери данных; `NaN` = отсутствующее значение
   - Затронуто ~34 поля: `record-id`, `src-id`, `taxonomy-id`, `year`, `first-approval` и др.
   - См. `docs/00-project/RULES.md` §2.6 "Int→Float Coercion для Nullable Integers"
   - **НЕ баг**, а паттерн для nullable integer handling

### 2.3.1. Причины Ложных Утверждений (Избегать!)

> **Статистика**: Анализ 2025-12-27 выявил ~40% ложных утверждений в 4 планах рефакторинга.
> См. `docs/consolidated-refactoring-analysis.md` для детального анализа.

| Причина                                  | Пример                                | Как избежать                                               |
| ---------------------------------------- | ------------------------------------- | ---------------------------------------------------------- |
| **Отсутствие верификации кодом**         | "Нет валидации X" без `grep`          | Всегда проверять код перед утверждением                    |
| **Ложная корреляция размер → сложность** | "517 LOC = монолит"                   | Проверять делегирование, не только размер                  |
| **Неверная интерпретация паттернов**     | "NoOp default = нарушение DI"         | Знать Null Object Pattern                                  |
| **Устаревшие знания**                    | "Не реализовано" (но уже реализовано) | Сверяться с кодом, active docs и текущими review artifacts |

### 2.3.2. Правило Анализа Делегирования

**ПЕРЕД** утверждением "god object" или "монолит" выполнить:

```bash
# 1. Измерить размер
wc -l src/bioetl/path/to/file.py  # Должно быть > 500 для "монолита"

# 2. Найти делегирование (если много — НЕ монолит!)
grep -o "self\.-[a-z-]*" src/bioetl/path/to/file.py | sort -u

# 3. Проверить импорты внешних компонентов
grep "^from\|^import" src/bioetl/path/to/file.py | grep -v "typing\|dataclass"

# 4. Найти количество публичных методов
grep -c "^    def \|^    async def " src/bioetl/path/to/file.py
```

**Критерии "монолита" (ВСЕ должны выполняться):**

- [ ] 500+ строк
- [ ] Мало делегирования (< 3 вызовов `self.-component.method()`)
- [ ] Много публичных методов с разной ответственностью
- [ ] Низкая когезия (методы не связаны друг с другом)

### 2.4. 🛡️ Протокол Верификации (ОБЯЗАТЕЛЬНО)

> **КРИТИЧЕСКИ ВАЖНО**: Перед любым утверждением о коде — **ПРОВЕРЬ КОД**!

**MUST выполнять перед предложением рефакторинга:**

```bash
# 1. Проверить существование класса/метода
grep -r "class ClassName" src/bioetl/
grep -r "def method-name" src/bioetl/

# 2. Проверить реализованность фичи
grep -r "SilverWriteMode\|GoldWriteMode" src/bioetl/

# 3. Проверить архитектурные тесты
ls tests/architecture/

# 4. При необходимости сверить historical false-positive ledger
cat docs/99-archive/refactoring-plan.md | head -60
```

**Чек-лист перед утверждением:**

| Утверждение             | Верификация                             |
| ----------------------- | --------------------------------------- |
| "Класс X существует"    | `grep -r "class X" src/`                |
| "Метод Y не реализован" | `grep -r "def Y" src/` + прочитать код  |
| "Нет теста для Z"       | `grep -r "test-Z\|Z" tests/`            |
| "Нет валидации W"       | Прочитать файл и найти validation logic |

**При обнаружении расхождения:**

1. Обновить текущий review artifact / task report
1. При необходимости обновить `CLAUDE.md` → секция 2.3 "Архитектурные Пояснения"

### 2.5. DDD Aggregates (ADR-021)

Проект использует DDD-агрегаты для управления бизнес-инвариантами:

| Агрегат           | Файл                                    | Назначение                                 |
| ----------------- | --------------------------------------- | ------------------------------------------ |
| `PipelineRun`     | `domain/aggregates/pipeline_run.py`     | Запуск пайплайна, события жизненного цикла |
| `Batch`           | `domain/aggregates/batch.py`            | Батч записей, состояние обработки          |
| `QuarantineEntry` | `domain/aggregates/quarantine_entry.py` | Карантинные записи                         |

**Паттерны:**

- Event Sourcing для аудита изменений
- Immutable Value Objects для состояний
- Factory Methods для создания агрегатов

______________________________________________________________________

## 3. Medallion Architecture и Обработка Ошибок

> **Полная документация**: См. `docs/00-project/RULES.md` §2 (Medallion) и §3 (Ошибки)

**Medallion** (Bronze → Silver → Gold):

- **Bronze**: JSONL + zstd, append-only, 90d retention
- **Silver**: Delta Lake, merge/upsert по `content-hash`, ACID обязателен
- **Gold**: Delta/Parquet, SCD Type 2 или партиции по дате

**Обработка ошибок**:

- **Critical**: Падение пайплайна (auth failure, schema mismatch)
- **Recoverable**: Retry с backoff (429, 502/504)
- **Data Quality**: Лог + пропуск (>5% warning, >20% fail batch)

**Circuit Breaker**: 5 consecutive errors → Open 5 мин (см. [ADR-007](../../../../02-architecture/decisions/ADR-007-circuit-breaker-implementation.md))

**Актуальный набор ADR** определяет архитектурные решения: `docs/02-architecture/decisions/ADR-{NNN}-*.md`
Перед ссылкой на номер ADR проверь текущий список файлов, а не исторический диапазон.
(полный реестр в `docs/00-project/RULES.md` Приложение F)

______________________________________________________________________

## 4. Блокировки (Locking)

| Параметр         | Значение                              |
| ---------------- | ------------------------------------- |
| Механизм         | In-memory (MemoryLock)                |
| Область          | Локальный процесс                     |
| TTL по умолчанию | 90s (настраивается в `RuntimeConfig`) |
| Heartbeat        | 30s (настраивается в `RuntimeConfig`) |

### 5.1. ⚠️ MemoryLock Достаточен для Локального Запуска

> **ВАЖНО**: Это **архитектурное решение**, а не недостаток!

**Почему НЕ нужен Redis:**

1. Пайплайны запускаются **локально** на одной машине
1. Нет распределённых workers — нет split-brain
1. `MemoryLock` полностью реализует `LockPort`:
   - TTL-based автоматическое освобождение (`-ttl-checker-loop`)
   - Heartbeat для продления блокировки (`heartbeat()`)
   - Валидация владельца (`validate-owner()`)
   - Safety guard перед записью (`LockNotHeldError`)

**Реализация:** `src/bioetl/infrastructure/locking/memory_lock.py` (256 строк)

```python
# Полный функционал MemoryLock:
async def acquire(key, owner-id, ttl, wait, wait-timeout, exclusive) -> bool
async def release(key, owner-id, exclusive) -> bool
async def heartbeat(key, owner-id, exclusive) -> bool  # Продление TTL
async def validate-owner(key, owner-id) -> bool        # Safety guard
async def aclose() -> None                             # Graceful shutdown
```

**Когда понадобится Redis:**

- Только при масштабировании на несколько workers
- Текущая архитектура этого не предполагает

### 5.2. Lock Keys

- Incremental: `lock:{provider}-{entity}`
- Backfill/Rebuild: `lock:{provider}-{entity}:exclusive`

______________________________________________________________________

## 5. Тестирование

> **Полная документация**: См. `docs/00-project/RULES.md` §4.2 "Политика Тестирования"

| Уровень          | Директория            | Масштаб      | Правила                          |
| ---------------- | --------------------- | ------------ | -------------------------------- |
| **Unit**         | `tests/unit/`         | live suite   | In-memory fakes предпочтительны  |
| **Integration**  | `tests/integration/`  | live suite   | VCR.py для HTTP                  |
| **Architecture** | `tests/architecture/` | active suite | Проверка слоёв, контракты портов |

**Всего:** не используй статический total; считай live для текущего tree и branch.
**Цель покрытия:** ≥85% (`--cov-fail-under=85`)

### Основные команды

```bash
make test                 # Все тесты с coverage
make test-unit            # Только unit (быстро)
make test-architecture    # Architecture tests
pytest tests/e2e/ -v -m e2e  # E2E тесты
```

### VCR.py (MUST для HTTP)

- Кассеты: `tests/fixtures/vcr/`
- Санитизация секретов в `before-record`
- CI: `pytest --vcr-record=none`

______________________________________________________________________

## 6. Стек Технологий и Провайдеры

> **Полная документация**: См. `docs/00-project/RULES.md` §4.1 (Стек) и Приложение А (Провайдеры)

**Ключевые инструменты:** httpx (`UnifiedHTTPClient`), Polars, Delta Lake, Pandera, Ruff + mypy, Click

**HTTP-адаптеры**: Все используют `BaseHttpAdapter` с Rate Limiter, Circuit Breaker, Retry Logic
**Legacy Wrappers**: `BaseSyncAdapter` с `run-in-executor` для библиотек без async (pubchempy)

**Провайдеры:** ChEMBL, PubChem (5 req/sec), UniProt (100 req/sec), CrossRef, OpenAlex, PubMed (3 req/sec), SemanticScholar

**Безопасность:** `make security` — osv-scanner + pip-audit + Bandit

______________________________________________________________________

## 7. Ключевые Файлы

| Артефакт     | Путь                                             |
| ------------ | ------------------------------------------------ |
| Domain Ports | `src/bioetl/domain/ports/`                       |
| Adapters     | `src/bioetl/infrastructure/adapters/{provider}/` |
| Pipelines    | `src/bioetl/application/pipelines/`              |
| Bootstrap    | `src/bioetl/composition/bootstrap/`              |
| CLI          | `src/bioetl/interfaces/cli/`                     |
| Configs      | `configs/entities/{provider}/{entity}.yaml`      |
| Tests        | `tests/`                                         |
| ADR          | `docs/02-architecture/decisions/`                |

______________________________________________________________________

## 8. Anti-Patterns и Чек-лист

> **Полный чек-лист**: См. `docs/00-project/RULES.md` и `AGENT.md` §9 "Чек-Лист Ревью"

**Критичные запреты:**

- ❌ Импорт `infrastructure` в `domain`/`application`
- ❌ Создание зависимостей внутри классов (нарушение DI)
- ❌ Прямой импорт `structlog` в `application`/`interfaces` → `LoggerPort`
- ❌ Sentinel values (`-1`, `"N/A"`) → `None`
- ❌ Блокирующий I/O в async → `run-in-executor`
- ❌ HTTP без VCR-кассет

**Перед коммитом:** `make lint && make test`

______________________________________________________________________

## 9. Git Workflow и Создание Компонентов

> **Полная документация**: См. `docs/00-project/RULES.md` §8 (Git) и `AGENT.md` §7 (Компоненты)

**Conventional Commits:** `<type>(<scope>): <description>`

- Типы: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

**Новый адаптер:** `domain/ports/` Protocol → `infrastructure/adapters/{provider}/` → `health_check()` + DI

**Новый пайплайн:** Config YAML → `BaseTransformer` → Pipeline → Factory → `@register` → Tests

______________________________________________________________________

## 10. Диагностика

| Ошибка                                   | Решение                                    |
| ---------------------------------------- | ------------------------------------------ |
| `ImportError: cannot import from domain` | Проверь матрицу импортов (`RULES.md` §1.1) |
| `RuntimeError: Event loop is closed`     | `run-in-executor` для блокирующего I/O     |
| Тесты падают в CI                        | Запиши VCR-кассету                         |
| Неясности в задаче                       | **СПРОСИ ПОЛЬЗОВАТЕЛЯ**                    |

______________________________________________________________________

## 11. Полная Документация

| Документ                                    | Описание                                                                        |
| ------------------------------------------- | ------------------------------------------------------------------------------- |
| `docs/00-project/RULES.md`                  | **Конституция проекта** — единственный источник истины для архитектурных правил |
| `docs/00-project/ai/agents/guides/AGENT.md` | Инструкции для агента (персона, workflow, специфика работы)                     |
| `docs/00-project/ai/memory/agent-memory.md` | Компактный контекст для быстрой справки                                         |
| `docs/02-architecture/decisions/`           | Актуальный набор ADR — архитектурные решения                                    |
| `docs/01-requirements/REQUIREMENTS.md`      | Тестируемые требования; при ссылке на total проверяй live по текущему документу |

> **Иерархия документации**: При противоречиях приоритет имеет `docs/00-project/RULES.md`.
> CLAUDE файл (`docs/00-project/ai/agents/guides/CLAUDE.md`) содержит специфику для Claude Code и протокол верификации.

______________________________________________________________________

*Строй надёжно. Документируй честно. Спрашивай смело.*

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
- Если задача требует изменения `.env`, исполнитель должен остановиться и сначала запросить явное разрешение пользователя.
