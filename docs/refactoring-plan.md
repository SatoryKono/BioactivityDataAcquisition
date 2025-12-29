# План Рефакторинга BioETL

*Версия: 5.9 | Дата: 2025-12-29 | Обновлено: Интегрирован консолидированный анализ 4 аудитов*

> **⚠️ ПРОТОКОЛ ДВОЙНОЙ ВЕРИФИКАЦИИ (REQ-ARCH-040)**
>
> Все утверждения в этом документе проходят **двойную верификацию** согласно `RULES.md` §7:
> 1. **Первая проверка** — при обнаружении проблемы (размер, структура, делегирование)
> 2. **Вторая проверка** — при документировании (точные ссылки `файл:строка`, дата)
>
> Невыполнение протокола привело к ~60% ложных утверждений в 4 предыдущих аудитах.
>
> **📊 Консолидированный анализ:** [`reports/consolidated-refactoring-analysis.md`](../reports/consolidated-refactoring-analysis.md)

---

## ⚠️ ВЕРИФИЦИРОВАННЫЙ СТАТУС РЕАЛИЗАЦИИ

> **ВАЖНО**: Перед постановкой задач сверьтесь с этой секцией!
> Последняя верификация: 2025-12-27 (обновлено: T1-T4 помечены ✅ РЕАЛИЗОВАНО)

### ✅ УЖЕ РЕАЛИЗОВАНО (не требует работы)

| Компонент | Файл | Доказательство |
|-----------|------|----------------|
| **PubMedAdapter.health_check()** | `pubmed_client.py:193-273` | Реализованы `health_check()`, `_probe_health()`, `_fallback_health_status()` |
| **VCR кассеты UniProt** | `tests/fixtures/vcr/` | 15+ кассет: `test_uniprot_protein_*.yaml`, `TestUniProtAdapterIntegration.*.yaml` |
| **VCR кассеты PubChem** | `tests/fixtures/vcr/` | `test_pubchem_compound_full_cycle.yaml` |
| **CLI тесты** | `tests/integration/interfaces/` | 7+ тестов: `test_cli_shutdown_integration.py`, `test_cli_run_*.py` и др. |
| **Обработка ошибок ChEMBL** | `client.py:223-267` | `_handle_error()` ВСЕГДА кидает исключения (CriticalError/ChemblApiError) |
| **UnifiedHTTPClient lifecycle** | `client.py:138-162` | Корректный async context manager (`__aenter__`/`__aexit__`) |
| **D1: Детерминистичный HTTP jitter** | `domain/resilience.py:45-84` | MD5-based jitter в `RetryPolicy.calculate_delay()`, 11 тестов в `test_http_client.py` |
| **PipelineRunner DI** | `runner.py:43-88`, `runner_services.py` | RunnerServices bundle инжектируется через конструктор; `build_runner_services()` создаёт сервисы в composition |
| **CLI → Entrypoints** | `cli.py:17-27`, `entrypoints.py` | CLI импортирует только из `composition/entrypoints.py`, не из `bootstrap_*` |
| **D2: Gold Writer детерминизм** | `gold_writer.py:286,359` | Фиксированный backoff `0.5 * (2**attempt) + 0.05` вместо `random.uniform()` |
| **D3: Arch test random** | `tests/architecture/test_no_random_in_writers.py` | 3 теста: import, uniform, choice |
| **M1: SilverWriteMode Enum** | `delta_writer.py:53-64` | `MERGE`, `APPEND`, `DELETE` + валидация в `_validate_write_mode()` |
| **M2: GoldWriteMode Enum** | `gold_writer.py:42-54` | `OVERWRITE`, `APPEND`, `SCD2` + валидация |
| **M4: Schema drift** | `delta_writer.py:303-349` | `_check_schema_drift()` с параметром `on_schema_mismatch: Literal["error", "evolve", "ignore"]` |
| **T5: Arch test datetime.now** | `tests/architecture/test_no_datetime_now_in_infrastructure.py` | 2 теста + список разрешённых исключений |
| **O1: BaseTransformer tracing** | `base_transformer.py:125-187` | Tracing spans, duration histogram, error counters |
| **T1: PipelineContext.started_at** | `context.py:109` | `started_at: datetime = field(default_factory=_now_utc)` |
| **T2: RecordProcessor ingestion_ts** | `record_processor.py:91` | `ingestion_ts = self._context.started_at` |
| **T3: BronzeWriter ingestion_ts** | `bronze_writer.py:211` | `ingestion_ts: datetime` (обязательный параметр) |
| **T4: Quarantine ingestion_ts** | `unified.py:66` | `ingestion_ts: datetime` (keyword-only, required) |
| **M3: Bronze JSON validation** | `bronze_writer.py:151-178` | `_validate_json_records()` с lazy generator и `BronzeValidationError` |

### ❌ ЛОЖНЫЕ УТВЕРЖДЕНИЯ (НЕ ПОВТОРЯТЬ)

| Ложное утверждение | Почему ложно | Верификация |
|--------------------|--------------|-------------|
| "PubMedAdapter не реализует health_check" | Полностью реализован | `pubmed_client.py:193-273` |
| "Нет VCR для PubChem/UniProt integration" | Кассеты существуют | `tests/fixtures/vcr/` |
| "0 тестов interfaces/оркестрации" | 7+ интеграционных CLI тестов | `tests/integration/interfaces/` |
| "ChemblAdapter._fetch_page глушит ошибки" | `_handle_error()` всегда raises; `return [], False` — мёртвый код | `client.py:145-147, 261-267` |
| "UnifiedHTTPClient нарушает DI" | Создание в `__aenter__` — корректный async pattern | `client.py:138-152` |
| "D1: HTTP jitter не реализован" | MD5-based jitter в `RetryPolicy` с 2025-12-26 | `domain/resilience.py:45-84`, 11 тестов |
| "PipelineRunner — god object" | **173 строки**, делегирует через RunnerServices bundle | `runner.py:53,84-88` |
| "bootstrap_pipeline смешивает ответственности" | Правильно делегирует фабрикам через `factory.create_runner()` | `bootstrap.py:159-166` |
| "ChEMBL адаптер — размытые границы" | Когезивная ответственность: health-aware fetching | `client.py` ~350 строк, использует ErrorClassifier |
| "CLI содержит бизнес-логику подтверждений" | Подтверждения — **законная** ответственность interfaces слоя | По design |
| "DeltaWriter нарушает DI (создаёт WriteModePolicy)" | Опциональный параметр с default — валидный паттерн | `delta_writer.py:98` |
| "BaseTransformer без DQ-валидации" | By design: Template Method, DQ — ответственность конкретных трансформеров | `base_transformer.py` |
| "MedallionLifecycleService без политик" | Использует `MedallionPolicy.should_clear_*` | `medallion_lifecycle.py:71-112` |
| "BronzeWriter без observability" | Имеет структурированное логирование | `bronze_writer.py:197-205` |
| "CLI плотно связан с composition" | CLI использует `entrypoints.py` — это фасад, правильный паттерн | `cli.py:17-24`, `entrypoints.py:7-8` |
| "bootstrap_pipeline агрегирует слишком много" | ~100 строк, делегирует специализированным функциям | `bootstrap.py:68-167` |
| "PipelineRunner.run() концентрирует этапы" | Делегирует: `preflight_service`, `lifecycle_orchestrator`, `postrun_service` | `runner.py:126-142` |
| "D2: gold_writer.py:21,219,279 использует random" | random удалён, фиксированный backoff `0.5 * (2**attempt) + 0.05` | `gold_writer.py:286,359` |
| "GenericPipelineFactory — god object" | 397 строк, 6 методов, делегирует `BaseServicesFactory`, `ServicesBuilder`, `build_runner_services()` | `generic_factory.py:190,299,332` |
| "yaml_config_to_domain нарушает архитектуру" | Матрица импортов разрешает infrastructure → domain. PipelineConfig — value object | `config.py:185-228`, CLAUDE.md §2.1 |
| "PubChemAdapter без observability" | Использует `BaseSyncAdapter` с metrics, CircuitBreaker, health_check() | `sync_base.py:130-134`, `pubchem/client.py:255-313` |
| "ChEMBL adapter — монолит 517 строк" | **Делегирует** через `EntityMapper` (112 LOC), `ErrorClassifier`, `AdapterMetrics`, `BaseHttpAdapter`. Когезивная ответственность. | `client.py:30,76-84,90` |
| "GoldWriter — монолит 593 строки, требует декомпозиции на стратегии" | **Делегирует** CSV в `CsvExporter`, audit в `AuditPort`. Режимы OVERWRITE/APPEND/SCD2 когезивны. | `gold_writer.py:70-71,87-88,351-355` |
| "Нет автоматизации DQ/Medallion политик" | Реализовано: `MedallionPolicy` в `domain/medallion.py`, `DQConfig` в `domain/config.py:25-63`, `SilverWriteMode` / `GoldWriteMode` enums | `medallion.py`, `config.py:36-37` |
| "medallion_policy.py дублирует domain" | Это **shim для backward-compat** (19 строк re-export), НЕ дублирование | `application/core/medallion_policy.py` |
| "Domain использует Pydantic-модели" | Используются **dataclass Value Objects** (`@dataclass(frozen=True)`), не Pydantic | `domain/config.py:25,66,94,176` |
| "bootstrap_pipeline 140+ строк" | **113 строк** (`bootstrap.py:68-180`), делегирует через 4 функции: `register_all_providers()`, `register_all_pipelines()`, `bootstrap_observability()`, `factory.create_runner()` | `bootstrap.py:113-114,122,173` |
| "RecordProcessor совмещает метрики/карантин/запись" | **Делегирует** в `BatchMetricsRecorder`, `BatchTransformer`, `BatchWriter`, `QuarantineManager`. Сам класс — тонкий оркестратор. | `record_processor.py:59-85` |
| "PipelineRunner не выпускает метрики по стадиям" | Использует `PipelineObserver` через `RunnerServices.observer` как context manager | `runner.py:89,117` |
| "Нет валидации write mode через Enum" | **Реализовано**: `SilverWriteMode` enum (`delta_writer.py:53-64`), `GoldWriteMode` enum (`gold_writer.py:42-54`) с валидацией | M1, M2 в этом документе |
| "Архитектурные тесты не связаны с метриками" | 187 архитектурных тестов в `tests/architecture/`, `make arch-test` в CI | `Makefile:arch-test` |
| "Требуется Redis для распределённых блокировок" | **MemoryLock достаточен** для локального запуска. Проект by design использует локальные пайплайны. Redis нужен только при масштабировании на несколько workers. | `CLAUDE.md` §5, `memory_lock.py` (256 строк, полный функционал) |
| "MemoryMonitor возвращает захардкоженные нули/значения — баг" | **Graceful degradation** — при недоступности psutil возвращает консервативные оценки (50% использования), не нули. Это валидный паттерн для кросс-платформенности. | `memory_monitor.py:170-180` (`_get_stats_estimate`) |
| "DQ метрики не экспортируются в Prometheus" | **УЖЕ РЕАЛИЗОВАНО**: `postrun_service.py:158-163` эмитит `dq_soft_threshold_exceeded` (counter), `dq_check_duration_ms` (histogram). | `domain/config.py:28-40` (`DQConfig`), `postrun_service.py:122-163` |
| "protocols.py пустой файл с нулевым покрытием" | Содержит 4 Protocol: `TransformCallback`, `GoldFilterCallback`, `GoldTransformCallback`, `TransformerPort` | `application/core/protocols.py` |
| "TTL по умолчанию 3600s не соответствует требованиям" | Фактический TTL = `heartbeat_interval * 3` = 90s по умолчанию. `LockContext.is_valid(ttl_seconds=3600)` — backward-compat check, не фактический TTL. | `domain/config.py:291-293` (`effective_lock_ttl`) |
| "Email в config требует хэширования как PII" | `default_email` — технический идентификатор для NCBI API, **НЕ персональные данные**. NCBI требует email для идентификации инструмента. | `CLAUDE.md` §2.3, `pubmed_client.py:38-42` |
| "Тестовый контур не работает, pytest падает" | **Тесты работают**: 2895 passed, 89% coverage. Проблема была в окружении, не в коде. | `make test` (верификация 2025-12-29) |
| "Parquet разрешён для Silver/Gold" | **Parquet запрещён** валидатором: `ValueError("Silver layer MUST use 'delta' format")` | `pipeline_config.py:261-271` (верификация 2025-12-29) |
| "VACUUM не автоматизирован, требуется планировщик" | **УЖЕ РЕАЛИЗОВАНО**: `PostrunService.run_vacuum_if_enabled()` вызывается автоматически после каждого успешного run | `runner.py:134-136`, `postrun_service.py:244-288` |
| "DQ-пороги не реализованы, только логирование" | **УЖЕ РЕАЛИЗОВАНО**: `DQConfig` (soft=0.05, hard=0.20), `_check_hard_threshold()` выбрасывает `DataQualityThresholdError`, метрики Prometheus | `postrun_service.py:122-163`, `domain/config.py:28-40` |
| "MemoryLock без TTL, требуется Redis" | **MemoryLock полон**: TTL через `_ttl_checker_loop()`, heartbeat через `heartbeat()`, safety guard через `validate_owner()`. Redis — только при масштабировании. | `memory_lock.py:1-256` (верификация 2025-12-29) |
| "Pandera strict=False — баг, нужен strict=True" | `strict=False` — **преднамеренно** для backward-compat. При `strict=True` и отсутствии схемы возвращается ошибка. Это documented behavior, не баг. | `pandera_validator.py:33-44` (верификация 2025-12-29) |
| "Content hash не исключает _ingestion_ts, _run_id" | **Уже исключает**: `META_FIELDS` set в `transformations.py:29-36` содержит `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_*`, `_source_batch_id` | `transformations.py:29-36,83-87` (верификация 2025-12-29) |
| "psutil в MemoryMonitor нарушает DI" | psutil — data source для системных метрик, аналогично `os.environ`. Graceful degradation реализована в `_get_stats_estimate()`. Port добавит accidental complexity. | `memory_monitor.py:86-180` (верификация 2025-12-29) |
| "CLI click.echo нарушает logging" | `click.echo` для human-readable вывода — **корректно** для CLI (interfaces слой). JSON-логи для machine processing, не для CLI interaction. | CLAUDE.md §2.3 (верификация 2025-12-29) |

### 🔴 ПОДТВЕРЖДЁННЫЕ ПРОБЛЕМЫ (актуальные задачи)

| Проблема | Файл:строки | Описание |
|----------|-------------|----------|
| ~~**PipelineRunner создаёт сервисы**~~ | ~~`runner.py:90-126`~~ | ✅ ВЫПОЛНЕНО: DI через `RunnerServices` bundle (2025-12-26) |
| ~~**CLI вызывает bootstrap напрямую**~~ | ~~`cli.py:224,265,337`~~ | ✅ ВЫПОЛНЕНО: CLI использует `composition/entrypoints.py` (верифицировано 2025-12-26) |
| ~~**Мёртвый код в ChemblAdapter**~~ | ~~`client.py:147`~~ | ✅ ВЫПОЛНЕНО: Удалён в коммите `9214cfb` |

> **Все критические проблемы решены.** Актуальный план см. в "Фаза 5" ниже.

---

## Обзор

Этот документ описывает план рефакторинга с фокусом на **детерминизм**, **Medallion-инварианты** и **единый источник метаданных**. Каждая задача включает конкретные изменения файлов с указанием строк, критерии приёмки и оценку рисков.

### Приоритеты

| Уровень | Фаза | Цель |
|---------|------|------|
| 🔴 **Критично** | D1-D3 | Детерминизм ретраев и временных меток |
| 🟠 **Высокий** | M1-M4 | Укрепление Medallion-инвариантов |
| 🟡 **Средний** | T1-T5 | Единый источник времени и run-metadata |
| 🟢 **Желательно** | O1-O4 | Повышение наблюдаемости |
| 🔵 **Желательно** | A1-A3 | Документация и автоматизация проверок |

### Порядок выполнения

```
┌─────────────────────────────────────────────────────────────────┐
│              ✅ КРИТИЧНО (Фаза 1) — ЗАВЕРШЕНА                    │
├─────────────────────────────────────────────────────────────────┤
│  ✅ D1: HTTP jitter (domain/resilience.py — MD5 jitter)         │
│  ✅ D2: Gold writer random (фиксированный backoff)              │
│  ✅ D3: Arch test (test_no_random_in_writers.py)                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              ✅ ВЫСОКИЙ (Фаза 2) — ЗАВЕРШЕНА                     │
├─────────────────────────────────────────────────────────────────┤
│  ✅ M1: Silver write mode (SilverWriteMode enum)                │
│  ✅ M2: Gold write mode (GoldWriteMode enum)                    │
│  ✅ M4: Schema drift handling (on_schema_mismatch)              │
│  ✅ M3: Bronze validation (bronze_writer.py:151-178)             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              ✅ СРЕДНИЙ (Фаза 3) — ЗАВЕРШЕНА                     │
├─────────────────────────────────────────────────────────────────┤
│  ✅ T1: PipelineContext.started_at                              │
│  ✅ T2: RecordProcessor                                         │
│  ✅ T3: BronzeWriter timestamp                                  │
│  ✅ T4: Quarantine timestamp                                    │
│  ✅ T5: Arch test datetime.now                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              🟢🔵 ЖЕЛАТЕЛЬНО (Фаза 4-5) — Частично               │
├─────────────────────────────────────────────────────────────────┤
│  ✅ O1: BaseTransformer tracing    │  ✅ A2: ADR-014            │
│  ⏳ O2-O4: Observer/Shutdown       │  ⏳ A1, A3: RULES + CI     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Фаза 1: Детерминизм Ретраев и Временных Меток ✅ ЗАВЕРШЕНА

### Цель
Обеспечить воспроизводимость запуска пайплайна при одинаковых входных данных.

### Проблема
Источники недетерминизма в кодовой базе:

| Файл | Строка | Паттерн | Контекст | Статус |
|------|--------|---------|----------|--------|
| ~~`infrastructure/adapters/http/client.py`~~ | ~~13, 53~~ | ~~`import random`, `random.uniform()`~~ | ~~Jitter ретраев~~ | ✅ Исправлено в `domain/resilience.py` |
| ~~`infrastructure/storage/gold_writer.py`~~ | ~~21, 219, 279~~ | ~~`import random`, `random.uniform()`~~ | ~~Write backoff~~ | ✅ Исправлено: `0.5 * (2**attempt) + 0.05` (`gold_writer.py:348`) |

---

### D1: Детерминистичный джиттер в HTTP-клиенте ✅ РЕАЛИЗОВАНО

> **Статус:** Реализовано в `domain/resilience.py:45-84`
> **Дата верификации:** 2025-12-26

**Файл:** `src/bioetl/domain/resilience.py` (перенесено из `infrastructure/adapters/http/client.py`)

#### Реализованное решение

`RetryPolicy` в domain слое использует MD5-based детерминистичный джиттер:

```python
@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    multiplier: float = 2.0
    jitter: float = 0.1
    deterministic: bool = True  # По умолчанию детерминистичный
    jitter_seed: int | None = None

    def calculate_delay(self, attempt: int, url: str = "") -> float:
        delay = self.base_delay * (self.multiplier**attempt)
        delay = min(delay, self.max_delay)
        jitter_range = delay * self.jitter

        if self.deterministic:
            # MD5-based для кросс-процессной стабильности (ADR-014)
            hash_input = f"{attempt}:{url}:{self.jitter_seed or 0}"
            digest = hashlib.md5(hash_input.encode(), usedforsecurity=False).hexdigest()
            jitter_factor = int(digest[:8], 16) / 0xFFFFFFFF
            delay += jitter_range * (jitter_factor * 2 - 1)
        else:
            # Deprecated: random.uniform() с DeprecationWarning
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0.0, delay)
```

#### Ключевые улучшения

| Аспект | Реализация |
|--------|------------|
| **Алгоритм** | MD5 вместо `hash()` для кросс-процессной стабильности |
| **Default** | `deterministic=True` (безопаснее чем предложенный `False`) |
| **Deprecation** | `deterministic=False` выдаёт `DeprecationWarning` |
| **Расположение** | Domain слой (`domain/resilience.py`), не infrastructure |

#### Тесты (11 тестов)

| Файл | Тест | Статус |
|------|------|--------|
| `test_http_client.py` | `test_deterministic_jitter_same_input_same_output` | ✅ |
| `test_http_client.py` | `test_deterministic_jitter_different_urls_different_output` | ✅ |
| `test_http_client.py` | `test_non_deterministic_mode_uses_random` | ✅ |
| `test_http_client.py` | `test_deterministic_jitter_cross_process_stability` | ✅ |
| `test_http_client.py` | `test_deterministic_jitter_known_values` | ✅ |

#### Критерии приёмки

- [x] `RetryPolicy(deterministic=True)` даёт одинаковые задержки при одинаковых входных данных
- [x] `RetryPolicy(deterministic=False)` сохраняет прежнее поведение с random
- [x] Тесты покрывают оба режима
- [x] `make lint && make test` проходят

---

### D2: Удаление random из Gold Writer ✅ РЕАЛИЗОВАНО

> **Статус:** Реализовано в `gold_writer.py:346-348`
> **Дата верификации:** 2025-12-27

**Файл:** `src/bioetl/infrastructure/storage/gold_writer.py`

#### Реализованное решение

`random` полностью удалён из `gold_writer.py`. Вместо `random.uniform()` используется фиксированный exponential backoff:

```python
# gold_writer.py:346-348
# Exponential backoff with fixed jitter (Base 0.5s, Multiplier 2)
# Fixed 0.05s jitter for deterministic behavior (see ADR-014)
delay = 0.5 * (2**attempt) + 0.05
await asyncio.sleep(delay)
```

#### Критерии приёмки

- [x] `import random` отсутствует в gold_writer.py
- [x] `random.uniform` не используется в storage writers
- [x] Тест `test_deterministic_write.py` проверяет детерминизм записи
- [x] `make lint && make test` проходят

---

### D3: Архитектурный тест на random в writers ✅ РЕАЛИЗОВАНО

> **Статус:** Реализовано в `tests/architecture/test_no_random_in_writers.py`
> **Дата верификации:** 2025-12-27

**Файл:** `tests/architecture/test_no_random_in_writers.py`

```python
"""Architecture test: запрет random в storage writers без явного флага."""
import ast
from pathlib import Path
import pytest

STORAGE_DIR = Path("src/bioetl/infrastructure/storage")
ALLOWED_RANDOM_FILES: set[str] = set()  # Без исключений

def test_no_random_import_in_storage_writers():
    """Storage writers MUST NOT import random module.

    REQ-ARCH-030: Deterministic writes for reproducibility.
    See ADR-014 for rationale.
    """
    violations = []

    for py_file in STORAGE_DIR.glob("*.py"):
        if py_file.name in ALLOWED_RANDOM_FILES:
            continue

        source = py_file.read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "random":
                        violations.append(
                            f"{py_file.name}:{node.lineno}: import random"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module == "random":
                    violations.append(
                        f"{py_file.name}:{node.lineno}: from random import ..."
                    )

    assert not violations, (
        f"Random imports found in storage writers:\n"
        + "\n".join(f"  - {v}" for v in violations)
        + "\n\nStorage writers must be deterministic. "
        "See docs/02-architecture/decisions/ADR-014-deterministic-retries.md"
    )


def test_no_random_uniform_calls_in_storage():
    """Storage writers MUST NOT call random.uniform() directly."""
    violations = []

    for py_file in STORAGE_DIR.glob("*.py"):
        if py_file.name in ALLOWED_RANDOM_FILES:
            continue

        source = py_file.read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr == "uniform":
                        if isinstance(node.func.value, ast.Name):
                            if node.func.value.id == "random":
                                violations.append(
                                    f"{py_file.name}:{node.lineno}: random.uniform()"
                                )

    assert not violations, (
        f"random.uniform() calls found:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )
```

#### Критерии приёмки

- [x] Тест добавлен в `tests/architecture/`
- [x] Тест падает при добавлении `import random` в любой storage writer
- [x] `make arch-test` включает новый тест
- [x] CI запускает архитектурные тесты

---

### Зависимости Фазы 1 ✅ ВСЕ ВЫПОЛНЕНЫ

```
D1 (HTTP jitter) ──┬──▶ D3 (Arch test)
                   │
D2 (Gold random) ──┘
```

### Риски Фазы 1

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Увеличение коллизий при ретраях | Низкая | Hash включает URL и attempt |
| Регрессия в integration тестах | Низкая | VCR кассеты фиксируют поведение |
| Сложность отладки | Низкая | Seed логируется для воспроизведения |

---

## Фаза 2: Укрепление Medallion-Инвариантов ✅ ЗАВЕРШЕНА (M1, M2, M4)

### Цель
Строгое соответствие Bronze/Silver/Gold режимам записи и форматам.

---

### M1: Валидация режимов записи в Silver Writer ✅ РЕАЛИЗОВАНО

> **Статус:** Реализовано в `delta_writer.py:55-66`
> **Дата верификации:** 2025-12-27

**Файл:** `src/bioetl/infrastructure/storage/delta_writer.py`

#### Реализация

`SilverWriteMode` Enum реализован на строках 55-66:

```python
class SilverWriteMode(str, Enum):
    """Allowed write modes for Silver layer."""
    MERGE = "merge"
    APPEND = "append"
    DELETE = "delete"
```

Валидация режима реализована в `_validate_write_mode()`.

#### Критерии приёмки

- [x] `write_silver(mode="invalid")` вызывает `ValueError` с описанием допустимых режимов
- [x] Записи без `_run_id` отклоняются с понятной ошибкой
- [x] Тесты покрывают все допустимые режимы

---

### M2: Валидация режимов записи в Gold Writer ✅ РЕАЛИЗОВАНО

> **Статус:** Реализовано в `gold_writer.py:44-55`
> **Дата верификации:** 2025-12-27

**Файл:** `src/bioetl/infrastructure/storage/gold_writer.py`

#### Реализация

`GoldWriteMode` Enum реализован на строках 44-55:

```python
class GoldWriteMode(str, Enum):
    """Allowed write modes for Gold layer."""
    OVERWRITE = "overwrite"
    APPEND = "append"
    SCD2 = "scd2"
```

Валидация режима и SCD2 конфигурации реализованы в `write_gold()`.

---

### M3: Валидация входных данных Bronze

**Файл:** `src/bioetl/infrastructure/storage/bronze_writer.py`

#### Требуемые изменения

| № | Изменение | Строки | Описание |
|---|-----------|--------|----------|
| 1 | Валидация records | 69-78 | Проверка типа Iterator[bytes] |
| 2 | Валидация metadata | 105-114 | Обязательные поля в metadata |

#### Целевой код

```python
async def write_bronze(
    self,
    records: Iterator[bytes],
    provider: str,
    entity: str,
    date: datetime,
    batch_id: BatchID,
    run_id: RunID,
    run_type: RunType,
) -> Path:
    # Validate provider/entity format
    if not provider or not provider.replace("_", "").isalnum():
        raise ValueError(f"Invalid provider name: '{provider}'")
    if not entity or not entity.replace("_", "").isalnum():
        raise ValueError(f"Invalid entity name: '{entity}'")

    # ... rest of implementation
```

---

### M4: Schema Drift обработка ✅ РЕАЛИЗОВАНО

> **Статус:** Реализовано в `delta_writer.py:303-393`
> **Дата верификации:** 2025-12-27

**Файл:** `src/bioetl/infrastructure/storage/delta_writer.py`

#### Реализация

Параметр `on_schema_mismatch: Literal["error", "evolve", "ignore"]` реализован в `write_silver()` и `_check_schema_drift()`:
- Строки 303-349: `_check_schema_drift()` с детекцией и обработкой
- Строки 364-393: `write_silver()` с параметром `on_schema_mismatch`

#### Целевой код (уже реализован)

```python
from typing import Literal

class DeltaWriter:
    async def write_silver(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        primary_keys: list[str],
        schema: Any,
        mode: str,
        partition_cols: list[str] | None = None,
        on_schema_mismatch: Literal["error", "evolve", "ignore"] = "error",
    ) -> None:
        # Check for schema drift
        existing_schema = await self._get_table_schema(table_name)
        if existing_schema:
            incoming_fields = set(records[0].keys()) if records else set()
            existing_fields = set(existing_schema.names)

            new_fields = incoming_fields - existing_fields
            removed_fields = existing_fields - incoming_fields

            if new_fields or removed_fields:
                self.logger.warning(
                    "Schema drift detected",
                    extra={
                        "table": table_name,
                        "new_fields": list(new_fields),
                        "removed_fields": list(removed_fields),
                        "action": on_schema_mismatch,
                    },
                )

                if on_schema_mismatch == "error":
                    raise SchemaEvolutionError(
                        table=table_name,
                        new_fields=new_fields,
                        removed_fields=removed_fields,
                    )
                elif on_schema_mismatch == "evolve":
                    await self._evolve_schema(table_name, new_fields)
                # "ignore" - proceed without changes

        # ... rest of implementation
```

---

### Критерии приёмки Фазы 2 ✅ ВСЕ ВЫПОЛНЕНЫ

- [x] Все режимы записи валидируются через Enum (`SilverWriteMode`, `GoldWriteMode`)
- [x] Недопустимые режимы вызывают `ValueError` с понятным сообщением
- [x] Schema drift обнаруживается и обрабатывается согласно настройке (`on_schema_mismatch`)
- [x] Тесты покрывают edge cases для каждого writer

### Риски Фазы 2

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Несовместимость с существующими конфигами | Средняя | Feature flag `BIOETL_STRICT_MEDALLION=true` |
| Падение при schema evolution | Низкая | `on_schema_mismatch="evolve"` как opt-in |

---

## Фаза 3: Единый Источник Времени и Run-Metadata ✅ ЗАВЕРШЕНА

### Цель
Все timestamp и metadata формируются в application слое и передаются вниз.

### Статус: ✅ РЕАЛИЗОВАНО (2025-12-27)

| Компонент | Статус | Верификация |
|-----------|--------|-------------|
| T1: PipelineContext.started_at | ✅ | `context.py:109` — `started_at: datetime = field(default_factory=_now_utc)` |
| T2: RecordProcessor | ✅ | `record_processor.py:91` — `ingestion_ts = self._context.started_at` |
| T3: BronzeWriter | ✅ | `bronze_writer.py:211` — `ingestion_ts: datetime` (обязательный параметр) |
| T4: Quarantine | ✅ | `unified.py:66` — `ingestion_ts: datetime` (keyword-only) |
| T5: Arch test | ✅ | `test_no_datetime_now_in_infrastructure.py` |

**Дополнительные доказательства использования `context.started_at`:**
- `base_transformer.py:505` — `ingestion_ts=context.started_at`
- `batch_transformer.py:144,254` — `ingestion_ts=self._context.started_at`
- `batch_writer.py:256` — `ingestion_ts=self._context.started_at`

---

### T1: Расширение PipelineContext ✅ РЕАЛИЗОВАНО

> **Статус:** Реализовано в `context.py:109`
> **Дата верификации:** 2025-12-27

**Файл:** `src/bioetl/domain/context.py`

#### Реализованное решение

`PipelineContext` уже содержит `started_at` как обязательное поле с default factory:

```python
# context.py:109
started_at: datetime = field(default_factory=_now_utc)
```

Метод `create()` принимает `started_at` как опциональный параметр для внешней инициализации.

---

### T2: Использование context.started_at в RecordProcessor ✅ РЕАЛИЗОВАНО

> **Статус:** Реализовано в `record_processor.py:91`
> **Дата верификации:** 2025-12-27

**Файл:** `src/bioetl/application/core/record_processor.py`

#### Реализованное решение

`RecordProcessor` использует `context.started_at` как единый источник времени:

```python
# record_processor.py:91
ingestion_ts = self._context.started_at
```

---

### T3: Удаление datetime.now() из BronzeWriter ✅ РЕАЛИЗОВАНО

> **Статус:** Реализовано в `bronze_writer.py:211`
> **Дата верификации:** 2025-12-27

**Файл:** `src/bioetl/infrastructure/storage/bronze_writer.py`

#### Реализованное решение

`BronzeWriter.write_bronze()` принимает `ingestion_ts` как обязательный параметр:

```python
# bronze_writer.py:211
ingestion_ts: datetime  # обязательный параметр
```

Timestamp передаётся из application слоя, а не создаётся в infrastructure.

---

### T4: Удаление datetime.now() из QuarantineManager ✅ РЕАЛИЗОВАНО

> **Статус:** Реализовано в `unified.py:66`
> **Дата верификации:** 2025-12-27

**Файл:** `src/bioetl/infrastructure/quarantine/unified.py`

#### Реализованное решение

`UnifiedQuarantine.write()` принимает `ingestion_ts` как keyword-only обязательный параметр:

```python
# unified.py:66
async def write(
    ...
    *,
    ingestion_ts: datetime,  # keyword-only, обязательный
) -> None:
```

Docstring (строка 77-78) подтверждает: "Ingestion timestamp from application layer (single source of time per ADR-014). Required."

---

### T5: Архитектурный тест на datetime.now() в infrastructure ✅ РЕАЛИЗОВАНО

> **Статус:** Реализовано в `tests/architecture/test_no_datetime_now_in_infrastructure.py`
> **Дата верификации:** 2025-12-27

**Файл:** `tests/architecture/test_no_datetime_now_in_infrastructure.py`

```python
"""Architecture test: datetime.now() только в application/composition слоях."""
import ast
from pathlib import Path
import pytest

INFRASTRUCTURE_DIR = Path("src/bioetl/infrastructure")
# Исключения (если есть обоснованные случаи)
ALLOWED_FILES: set[str] = set()


def test_no_datetime_now_in_infrastructure():
    """Infrastructure MUST NOT call datetime.now() directly.

    REQ-ARCH-031: Single source of truth for timestamps.
    Timestamps should be created in application layer and passed down.
    """
    violations = []

    for py_file in INFRASTRUCTURE_DIR.rglob("*.py"):
        if py_file.name in ALLOWED_FILES:
            continue

        source = py_file.read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check for datetime.now() or datetime.now(UTC)
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr == "now":
                        if isinstance(node.func.value, ast.Attribute):
                            # datetime.datetime.now()
                            if node.func.value.attr == "datetime":
                                violations.append(
                                    f"{py_file.relative_to(INFRASTRUCTURE_DIR)}:{node.lineno}"
                                )
                        elif isinstance(node.func.value, ast.Name):
                            # datetime.now() after "from datetime import datetime"
                            if node.func.value.id == "datetime":
                                violations.append(
                                    f"{py_file.relative_to(INFRASTRUCTURE_DIR)}:{node.lineno}"
                                )

    assert not violations, (
        f"datetime.now() found in infrastructure layer:\n"
        + "\n".join(f"  - {v}" for v in violations)
        + "\n\nTimestamps should be created in application layer and passed as parameters."
    )
```

---

### Зависимости Фазы 3 ✅ ВСЕ ВЫПОЛНЕНЫ

```
✅ T1 (PipelineContext) ──▶ ✅ T2 (RecordProcessor)
                                   │
✅ T3 (BronzeWriter) ──────────────┤
                                   │
✅ T4 (Quarantine) ────────────────┴──▶ ✅ T5 (Arch test)
```

### Критерии приёмки Фазы 3 ✅ ВСЕ ВЫПОЛНЕНЫ

- [x] `PipelineContext.started_at` — единственный источник времени для batch (`context.py:109`)
- [x] `datetime.now()` отсутствует в infrastructure слое (кроме разрешённых исключений)
- [x] Архитектурный тест блокирует добавление `datetime.now()` в infrastructure
- [x] Все компоненты используют `context.started_at` (верифицировано 2025-12-27)

---

## Фаза 4: Повышение Наблюдаемости 🟢

### Цель
Консистентные метрики и трейсы через стандартизированные порты.

---

### O1: TracingContext в BaseTransformer ✅ РЕАЛИЗОВАНО

> **Статус:** Реализовано в `base_transformer.py:125-187`
> **Дата верификации:** 2025-12-27

**Файл:** `src/bioetl/application/core/base_transformer.py`

#### Реализация

- Tracing spans: строки 125-187
- Duration histogram по entity_type
- Error counters по error_type

---

### O2: TracingContext в PipelineExecutor ✅ РЕАЛИЗОВАНО

> **Статус:** Реализовано в `executor.py:167-189,421-457` (верификация 2025-12-29)

**Файл:** `src/bioetl/application/core/executor.py`

| № | Изменение | Статус | Строки |
|---|-----------|--------|--------|
| 1 | Root span для batch | ✅ | `executor.py:421-433` |
| 2 | Nested spans | ✅ | `executor.py:153-165,409-457` |
| 3 | Span attributes | ✅ | `executor.py:270-276,445-449` |

---

### O3: Graceful shutdown для tracer ✅ РЕАЛИЗОВАНО

> **Статус:** Реализовано в `observer.py:149-160` (верификация 2025-12-29)

**Файл:** `src/bioetl/application/observability/observer.py`

Graceful shutdown реализован в `PipelineObserver.__exit__()`:
- Try/except вокруг span cleanup (строки 150-160)
- Ошибки tracer НЕ проваливают pipeline
- Тест: `test_observer_handles_close_error`

---

### O4: Тесты observer ✅ РЕАЛИЗОВАНО

> **Статус:** Реализовано в `test_observer.py` — 30+ тестов (верификация 2025-12-29)

**Файл:** `tests/unit/application/observability/test_observer.py`

| Тест | Статус | Строки |
|------|--------|--------|
| `test_observer_records_duration` | ✅ | 138-168 |
| `test_observer_tracks_errors` | ✅ | 170-195 |
| `test_observer_graceful_shutdown` | ✅ | 198-222 |
| `test_observer_handles_close_error` | ✅ | 224-246 |
| Lifecycle event tests | ✅ | 249-634 |

---

### Критерии приёмки Фазы 4

- [ ] Tracing spans покрывают ключевые операции (fetch, transform, write)
- [ ] Observer тесты проходят
- [ ] Graceful shutdown работает без потери spans
- [ ] Sampling настраивается для production (1/100)

---

## Фаза 5: Документация и Автоматизация Проверок 🔵

### A1: Обновление RULES.md

**Файл:** `docs/RULES.md`

| Секция | Изменение |
|--------|-----------|
| §4.1 Retry Logic | Добавить требование детерминистичного джиттера |
| §2.1 Medallion | Добавить режимы записи и их ограничения |
| §6.1 Determinism | **Новая секция** с правилами воспроизводимости |

#### Новая секция §6.1

```markdown
## 6.1 Детерминизм и Воспроизводимость

### MUST

1. Storage writers НЕ ДОЛЖНЫ использовать `random` модуль
2. Timestamps ДОЛЖНЫ передаваться из application слоя, не создаваться в infrastructure
3. Retry jitter ДОЛЖЕН быть детерминистичным при `deterministic=True`

### Проверки

- Архитектурный тест `test_no_random_in_writers` блокирует random в storage
- Архитектурный тест `test_no_datetime_now_in_infrastructure` блокирует datetime.now() в infra
```

---

### A2: ADR-014 для детерминизма

**Файл:** `docs/02-architecture/decisions/ADR-014-deterministic-writes.md` (новый)

```markdown
# ADR-014: Детерминистичные записи и ретраи

## Status
Accepted

## Date
2025-12-24

## Context

Для воспроизводимости и отладки пайплайнов необходимо обеспечить детерминизм:
1. Одинаковые входные данные → одинаковый выход
2. Retry delays воспроизводимы при debugging
3. Timestamps консистентны в рамках batch

## Decision

1. **Retry jitter**: Hash-based вместо random.uniform()
   - `hash(f"{attempt}:{url}:{seed}") % 1000 / 1000`
   - Включается через `RetryConfig(deterministic=True)`

2. **Storage writes**: Запрет random в infrastructure/storage/
   - Фиксированный backoff вместо random.uniform()
   - Архитектурный тест блокирует нарушения

3. **Timestamps**: Единый источник в PipelineContext
   - `context.started_at` передаётся во все компоненты
   - Infrastructure не создаёт timestamps

## Consequences

### Positive
- Воспроизводимость запусков для debugging
- Упрощение тестирования (фиксированные значения)
- Консистентные метаданные в Bronze/Silver

### Negative
- Небольшое усложнение API (дополнительные параметры)
- Требуется миграция существующих вызовов

### Neutral
- Production по умолчанию использует random (deterministic=False)
```

---

### A3: Интеграция в CI

**Файл:** `Makefile` (обновить)

```makefile
.PHONY: arch-test
arch-test:
	@echo "Running architecture tests..."
	pytest tests/architecture/ -v --tb=short

.PHONY: arch-lint
arch-lint:
	@echo "Running import-linter..."
	lint-imports

.PHONY: arch-all
arch-all: arch-lint arch-test
	@echo "All architecture checks passed"

.PHONY: ci
ci: lint test arch-all
	@echo "CI checks complete"
```

---

## Матрица Трассировки

| Задача | Файлы | Тесты | ADR |
|--------|-------|-------|-----|
| D1 | `client.py` | `test_http_client.py` | ADR-014 |
| D2 | `gold_writer.py` | `test_deterministic_write.py` | ADR-014 |
| D3 | `test_no_random_in_writers.py` | self | — |
| M1 | `delta_writer.py` | `test_delta_writer.py` | — |
| M2 | `gold_writer.py` | `test_gold_writer.py` | — |
| M4 | `delta_writer.py` | `test_schema_drift.py` | — |
| T1 | `context.py` | `test_context.py` | — |
| T3 | `bronze_writer.py` | `test_bronze_writer.py` | — |
| T5 | `test_no_datetime_now_in_infrastructure.py` | self | — |
| O3 | `runner.py` | `test_runner_cleanup.py` | — |
| A2 | `ADR-014-deterministic-writes.md` | — | self |

---

## Критерии Приёмки по Фазам

### Фаза 1 🔴 ✅ ЗАВЕРШЕНА:
- [x] `make test` проходит с детерминистичным джиттером
- [x] `random` удалён из storage writers
- [x] Архитектурный тест `test_no_random_in_writers` добавлен и проходит

### Фаза 2 🟠 ✅ ЗАВЕРШЕНА:
- [x] Все режимы записи валидируются через Enum (`SilverWriteMode`, `GoldWriteMode`)
- [x] Schema drift обрабатывается явно (`on_schema_mismatch: error/evolve/ignore`)
- [x] Тесты покрывают edge cases

### Фаза 3 🟡 ✅ ЗАВЕРШЕНА:
- [x] `datetime.now()` отсутствует в infrastructure (есть исключения с обоснованием)
- [x] `PipelineContext.started_at` используется везде (верифицировано 2025-12-27)
- [x] Архитектурный тест `test_no_datetime_now_in_infrastructure` проходит
- [x] T1-T4 реализованы: `context.py:109`, `record_processor.py:91`, `bronze_writer.py:211`, `unified.py:66`

### Фаза 4 🟢 ✅ ЗАВЕРШЕНА (O1):
- [x] Tracing spans покрывают ключевые операции (`base_transformer.py:125-187`)
- [ ] Observer тесты проходят
- [ ] Graceful shutdown работает

### Фаза 5 🔵 Частично Завершена:
- [ ] RULES.md обновлён секцией §6.1 Determinism
- [x] ADR-014 создан (`docs/02-architecture/decisions/ADR-014-deterministic-writes.md`)
- [x] CI включает `make arch-all`

---

## Чек-лист перед началом

- [ ] `make lint && make test` проходят на текущем коде
- [ ] Git branch создан для работы
- [ ] Прочитаны `docs/RULES.md` и `.claude/PROJECT_CONTEXT.md`
- [ ] Понятны критерии приёмки каждой задачи

---

## Консолидированный План DI-Рефакторинга

> **Источник**: Анализ 4 планов рефакторинга (2025-12-26)
> **Статус**: Актуальные задачи после верификации

### Приоритет 1: КРИТИЧЕСКИЕ

#### 1.1 ~~Вынести сервисы из PipelineRunner в composition~~ ✅ ВЫПОЛНЕНО

**Статус**: Реализовано (2025-12-26)

**Реализация**:
- `RunnerServices` bundle в `application/core/runner_services.py:19-33`
- `build_runner_services()` фабрика в `composition/factories/runner_services.py:33-103`
- `PipelineRunner` принимает `runner_services` в конструкторе (`runner.py:53`)
- Сервисы извлекаются из bundle (`runner.py:84-88`)

**Тесты**:
- `tests/architecture/test_di_discipline.py` (1 тест) — проверяет отсутствие создания сервисов в application
- `tests/architecture/test_di_compliance.py` (9 тестов) — проверяет DI паттерн
- `tests/unit/application/core/test_runner.py` (17 тестов) — unit тесты runner

**Критерии готовности**:
- [x] PipelineRunner не создаёт сервисы
- [x] `make arch-test` проходит (187 passed)

#### 1.2 ~~Разнести CLI и composition root~~ ✅ ВЫПОЛНЕНО

**Статус**: Реализовано (верифицировано 2025-12-26)

**Реализация**:
- `composition/entrypoints.py` создан с публичным API
- `cli.py:17-27` импортирует только из entrypoints: `RunOptions`, `create_pipeline_runner`, `get_checkpoint_manager`, `get_lifecycle_service`, `get_quarantine_manager`, `preview_cleanup`
- CLI не импортирует `bootstrap_*` напрямую

**Критерии готовности**:
- [x] CLI не импортирует `bootstrap_*`
- [x] Entrypoints доступны для REST API и других оркестраторов

### Приоритет 2: ВЫСОКИЙ

#### 2.1 ~~Удалить мёртвый код в ChemblAdapter~~ ✅ ВЫПОЛНЕНО

**Файл**: `client.py:147` — `return [], False` был недостижим.

**Статус**: ✅ Удалён в коммите `9214cfb` (refactor(chembl): remove unreachable code after _handle_error).

### Приоритет 3: ЖЕЛАТЕЛЬНО

#### 3.1 ~~Arch-тест на DI дисциплину~~ ✅ ВЫПОЛНЕНО

**Файл**: `tests/architecture/test_di_discipline.py`

**Статус**: Реализовано. Тест `test_no_service_creation_in_application` проверяет отсутствие:
- `LockManager.create`
- `PreflightService(`
- `PostrunService(`
- `LifecycleOrchestrator(`

в application layer.

---

## 📝 Протокол Предотвращения Ложных Утверждений

> **ПРИЧИНА**: Анализ 2025-12-27 выявил ~50% ложных утверждений в 4 планах рефакторинга.
> Этот протокол обязателен для исполнения.
>
> **Регламент**: `docs/RULES.md` §7 "Протокол Архитектурных Обзоров" (REQ-ARCH-040)
> Требуется **двойная верификация** каждой проблемы.

### Правило 1: Никаких Утверждений Без Кода

**ЗАПРЕЩЕНО** предлагать рефакторинг без верификации:

| ❌ Неверно | ✅ Верно |
|-----------|----------|
| "PipelineRunner — god object" | "PipelineRunner (`runner.py`, 173 строки, 8 методов) делегирует `preflight_service`, `postrun_service`" |
| "bootstrap_pipeline перегружен" | "bootstrap_pipeline (`bootstrap.py:68-167`, 100 строк) вызывает 3 специализированные функции" |
| "CLI связан с composition" | "CLI (`cli.py:17-24`) импортирует из `entrypoints.py` — это фасад" |

### Правило 2: Обязательные Проверки

Перед созданием задачи рефакторинга:

```bash
# 1. Проверить секцию "ЛОЖНЫЕ УТВЕРЖДЕНИЯ" в этом документе
grep -A3 "Ложное утверждение" docs/REFACTORING_PLAN.md

# 2. Прочитать целевой файл
cat src/bioetl/path/to/file.py | head -100

# 3. Измерить размер и структуру
wc -l src/bioetl/path/to/file.py
grep -c "def \|async def " src/bioetl/path/to/file.py

# 4. Проверить делегирование
grep -n "self\._" src/bioetl/path/to/file.py | head -20

# 5. Найти существующие тесты
find tests -name "*.py" -exec grep -l "ClassName" {} \;
```

### Правило 3: Формат Верифицированного Предложения

Каждое предложение MUST содержать:

```markdown
## Задача: [Название]

### Верификация
- **Файл**: `path/to/file.py:строки` (N строк, M методов)
- **Проверено**: Нет в "ЛОЖНЫЕ УТВЕРЖДЕНИЯ" ✅
- **Дата верификации**: YYYY-MM-DD

### Текущее Состояние
[Описание с ссылками `файл:строка`]

### Проблема
[Конкретное описание проблемы с доказательствами]

### Решение
[Предлагаемое решение]
```

### Правило 4: Обновление Этого Документа

При обнаружении ложного утверждения:

1. **Добавить** в таблицу "❌ ЛОЖНЫЕ УТВЕРЖДЕНИЯ"
2. **Указать** причину, почему утверждение ложно
3. **Добавить** ссылку на код (`файл:строка`)
4. **Обновить** дату верификации
5. **Закоммитить** изменения

При реализации функционала:

1. **Переместить** задачу в "✅ УЖЕ РЕАЛИЗОВАНО"
2. **Добавить** ссылку на коммит или файл
3. **Указать** дату реализации

### Команды Быстрой Верификации

```bash
# Структура компонента
wc -l src/bioetl/application/core/runner.py  # 173 строки
grep -c "def " src/bioetl/application/core/runner.py  # 12 методов

# Делегирование (ищем вызовы сервисов)
grep -o "self\._[a-z_]*\." src/bioetl/application/core/runner.py | sort -u

# Импорты в CLI
grep "^from\|^import" src/bioetl/interfaces/cli.py | head -20

# Тесты для компонента
ls tests/unit/application/core/test_runner*.py
ls tests/architecture/test_di_*.py
```

---

## Фаза 6: Mypy Strict Compliance ✅ ЗАВЕРШЕНА (2025-12-29)

### P1-1: Исправление mypy ошибок ✅ РЕАЛИЗОВАНО

> **Статус:** Реализовано 2025-12-29
> **Верификация:** `mypy src/bioetl --strict` → 0 ошибок

#### Исправленные ошибки

| Файл | Строка | Ошибка | Решение |
|------|--------|--------|---------|
| `domain/schemas/base.py` | 15 | `Class cannot subclass "DataFrameModel"` | `# type: ignore[misc]` (Pandera не имеет полных type stubs) |
| `application/core/base_transformer.py` | 323 | `Returning Any from function declared to return "str \| None"` | Явная типизация: `result: str = orjson.dumps(...).decode("utf-8")` |
| `application/core/base_transformer.py` | 331 | `Returning Any from function declared to return "str \| None"` | Явная типизация: `result_item: str = ...` |
| `application/core/base_transformer.py` | 335 | `Returning Any from function declared to return "str \| None"` | Явная типизация: `result_list: str = ...` |

#### Критерии приёмки

- [x] `mypy src/bioetl --strict` → 0 ошибок
- [x] Все тесты проходят
- [x] CHANGELOG.md обновлён

---

*Строй надёжно. Верифицируй перед предложением. Документируй с доказательствами.*
