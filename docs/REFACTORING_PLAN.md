# План Рефакторинга BioETL

*Версия: 5.4 | Дата: 2025-12-27*

> **⚠️ ПРОТОКОЛ ДВОЙНОЙ ВЕРИФИКАЦИИ (REQ-ARCH-040)**
>
> Все утверждения в этом документе проходят **двойную верификацию** согласно `RULES.md` §7:
> 1. **Первая проверка** — при обнаружении проблемы (размер, структура, делегирование)
> 2. **Вторая проверка** — при документировании (точные ссылки `файл:строка`, дата)
>
> Невыполнение протокола привело к ~50% ложных утверждений в предыдущих планах.

---

## ⚠️ ВЕРИФИЦИРОВАННЫЙ СТАТУС РЕАЛИЗАЦИИ

> **ВАЖНО**: Перед постановкой задач сверьтесь с этой секцией!
> Последняя верификация: 2025-12-27 (обновлено: добавлен протокол двойной верификации REQ-ARCH-040)

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
│                     🔴 КРИТИЧНО (Фаза 1)                        │
├─────────────────────────────────────────────────────────────────┤
│  ✅ D1: HTTP jitter ──────────────────────────┐                 │
│      (domain/resilience.py — MD5 jitter)      │                 │
│                                               ├──▶ D3: Arch test│
│  D2: Gold writer random ──────────────────────┘                 │
│      (gold_writer.py:219,279)                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     🟠 ВЫСОКИЙ (Фаза 2)                         │
├─────────────────────────────────────────────────────────────────┤
│  M1: Silver write mode ───┐                                     │
│  M2: Gold write mode ─────┼──▶ M4: Schema drift handling        │
│  M3: Bronze validation ───┘                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     🟡 СРЕДНИЙ (Фаза 3)                         │
├─────────────────────────────────────────────────────────────────┤
│  T1: PipelineContext.started_at ──▶ T2: RecordProcessor ────┐   │
│                                                             │   │
│  T3: BronzeWriter timestamp ─────────────────────────────┐  │   │
│  T4: Quarantine timestamp ───────────────────────────────┼──┴──▶│
│                                                          │      │
│  T5: Arch test datetime.now ─────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     🟢🔵 ЖЕЛАТЕЛЬНО (Фаза 4-5)                   │
├─────────────────────────────────────────────────────────────────┤
│  O1-O4: Tracing/Observer    │    A1-A3: RULES + ADR + CI        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Фаза 1: Детерминизм Ретраев и Временных Меток 🔴

### Цель
Обеспечить воспроизводимость запуска пайплайна при одинаковых входных данных.

### Проблема
Источники недетерминизма в кодовой базе:

| Файл | Строка | Паттерн | Контекст | Статус |
|------|--------|---------|----------|--------|
| ~~`infrastructure/adapters/http/client.py`~~ | ~~13, 53~~ | ~~`import random`, `random.uniform()`~~ | ~~Jitter ретраев~~ | ✅ Исправлено в `domain/resilience.py` |
| `infrastructure/storage/gold_writer.py` | 21, 219, 279 | `import random`, `random.uniform()` | Write backoff | ❌ Требует исправления |

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

### D2: Удаление random из Gold Writer

**Файл:** `src/bioetl/infrastructure/storage/gold_writer.py`

#### Текущее состояние

```python
# Строка 21
import random

# Строка 219
await asyncio.sleep(random.uniform(0, 0.1))

# Строка 279
await asyncio.sleep(random.uniform(0, 0.1))
```

#### Требуемые изменения

| № | Изменение | Строки | Описание |
|---|-----------|--------|----------|
| 1 | Удалить import | 21 | `import random` → удалить |
| 2 | Фиксированный backoff | 219 | `random.uniform(0, 0.1)` → `0.05` |
| 3 | Фиксированный backoff | 279 | `random.uniform(0, 0.1)` → `0.05` |

#### Альтернатива: параметризованный backoff

```python
@dataclass
class GoldWriter:
    base_path: str | Path
    csv_exporter: CsvExporter | None = None
    write_backoff: float = 0.05  # NEW: фиксированный вместо random

    async def _write_with_backoff(self, ...):
        await asyncio.sleep(self.write_backoff)  # Детерминистично
```

#### Критерии приёмки

- [ ] `import random` отсутствует в gold_writer.py
- [ ] `random.uniform` не используется в storage writers
- [ ] Тест `test_gold_writer_deterministic_backoff` проверяет фиксированную задержку
- [ ] `make lint && make test` проходят

---

### D3: Архитектурный тест на random в writers

**Файл:** `tests/architecture/test_no_random_in_writers.py` (новый)

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

- [ ] Тест добавлен в `tests/architecture/`
- [ ] Тест падает при добавлении `import random` в любой storage writer
- [ ] `make arch-test` включает новый тест
- [ ] CI запускает архитектурные тесты

---

### Зависимости Фазы 1

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

## Фаза 2: Укрепление Medallion-Инвариантов 🟠

### Цель
Строгое соответствие Bronze/Silver/Gold режимам записи и форматам.

---

### M1: Валидация режимов записи в Silver Writer

**Файл:** `src/bioetl/infrastructure/storage/delta_writer.py`

#### Требуемые изменения

| № | Изменение | Строки | Описание |
|---|-----------|--------|----------|
| 1 | Добавить Enum | 1-10 | `class SilverWriteMode(Enum): MERGE, APPEND, DELETE` |
| 2 | Валидация в `write_silver()` | 154-167 | Raise `ValueError` при недопустимом режиме |
| 3 | Проверка required fields | 167 | Явная проверка `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts` |

#### Целевой код

```python
from enum import Enum

class SilverWriteMode(str, Enum):
    """Allowed write modes for Silver layer."""
    MERGE = "merge"
    APPEND = "append"
    DELETE = "delete"


async def write_silver(
    self,
    table_name: str,
    records: list[dict[str, Any]],
    primary_keys: list[str],
    schema: Any,
    mode: str,
    partition_cols: list[str] | None = None,
) -> None:
    # Validate mode
    try:
        validated_mode = SilverWriteMode(mode)
    except ValueError:
        valid_modes = [m.value for m in SilverWriteMode]
        raise ValueError(
            f"Invalid Silver write mode '{mode}'. "
            f"Allowed: {valid_modes}"
        )

    # Validate required metadata fields
    required_fields = {"_run_id", "_run_type", "_source_batch_id", "_ingestion_ts"}
    if records:
        first_record = records[0]
        missing = required_fields - set(first_record.keys())
        if missing:
            raise ValueError(
                f"Silver records missing required metadata fields: {missing}"
            )

    # ... rest of implementation
```

#### Критерии приёмки

- [ ] `write_silver(mode="invalid")` вызывает `ValueError` с описанием допустимых режимов
- [ ] Записи без `_run_id` отклоняются с понятной ошибкой
- [ ] Тесты покрывают все допустимые режимы

---

### M2: Валидация режимов записи в Gold Writer

**Файл:** `src/bioetl/infrastructure/storage/gold_writer.py`

#### Требуемые изменения

| № | Изменение | Строки | Описание |
|---|-----------|--------|----------|
| 1 | Добавить Enum | 1-10 | `class GoldWriteMode(Enum): OVERWRITE, APPEND, SCD2` |
| 2 | Валидация в `write_gold()` | 61-75 | Raise при недопустимом режиме |
| 3 | Строгая проверка schema | 75-84 | Enforce `strict=True` для Gold |

#### Целевой код

```python
class GoldWriteMode(str, Enum):
    """Allowed write modes for Gold layer."""
    OVERWRITE = "overwrite"
    APPEND = "append"
    SCD2 = "scd2"


async def write_gold(
    self,
    table_name: str,
    records: list[dict[str, Any]],
    primary_keys: list[str],
    schema: Any | None = None,
    mode: str = "overwrite",
    partition_cols: list[str] | None = None,
    scd_config: Any | None = None,
) -> None:
    # Validate mode
    try:
        validated_mode = GoldWriteMode(mode)
    except ValueError:
        valid_modes = [m.value for m in GoldWriteMode]
        raise ValueError(
            f"Invalid Gold write mode '{mode}'. Allowed: {valid_modes}"
        )

    # Enforce strict schema for Gold
    if schema is not None:
        if not getattr(schema, "strict", False):
            self.logger.warning(
                "Gold layer schema should have strict=True for data quality",
                extra={"table": table_name},
            )

    # SCD2 requires scd_config
    if validated_mode == GoldWriteMode.SCD2 and scd_config is None:
        raise ValueError("SCD2 mode requires scd_config parameter")

    # ... rest of implementation
```

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

### M4: Schema Drift обработка

**Файл:** `src/bioetl/infrastructure/storage/delta_writer.py`

#### Требуемые изменения

| № | Изменение | Строки | Описание |
|---|-----------|--------|----------|
| 1 | Добавить параметр | 56-72 | `on_schema_mismatch: Literal["error", "evolve", "ignore"] = "error"` |
| 2 | Реализовать detection | 200-210 | Сравнение incoming vs existing schema |
| 3 | Реализовать evolution | 210-220 | Добавление новых колонок при `evolve` |
| 4 | Логирование drift | 215 | Warning с деталями изменений |

#### Целевой код

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

### Критерии приёмки Фазы 2

- [ ] Все режимы записи валидируются через Enum
- [ ] Недопустимые режимы вызывают `ValueError` с понятным сообщением
- [ ] Schema drift обнаруживается и обрабатывается согласно настройке
- [ ] Тесты покрывают edge cases для каждого writer

### Риски Фазы 2

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Несовместимость с существующими конфигами | Средняя | Feature flag `BIOETL_STRICT_MEDALLION=true` |
| Падение при schema evolution | Низкая | `on_schema_mismatch="evolve"` как opt-in |

---

## Фаза 3: Единый Источник Времени и Run-Metadata 🟡

### Цель
Все timestamp и metadata формируются в application слое и передаются вниз.

### Проблема
Временные метки создаются в разных местах (недетерминизм):

| Компонент | Файл:Строка | Проблема |
|-----------|-------------|----------|
| RecordProcessor | `record_processor.py:148` | `datetime.now(UTC)` — источник истины |
| BronzeWriter | `bronze_writer.py:103` | **Дублирует** `datetime.now(UTC)` |
| BaseEntity | `entities.py:36` | `datetime.now(UTC)` в factory |
| Quarantine | `unified.py:89` | Отдельный `datetime.now(UTC)` |

---

### T1: Расширение PipelineContext

**Файл:** `src/bioetl/domain/context.py`

#### Текущее состояние (строки 13-34)

```python
@dataclass(frozen=True)
class PipelineContext:
    run_id: RunID
    run_type: RunType
    logger: LoggerPort
    # ← Нет started_at
```

#### Требуемые изменения

```python
from datetime import UTC, datetime

@dataclass(frozen=True)
class PipelineContext:
    """Context object for a pipeline run."""

    run_id: RunID
    run_type: RunType
    logger: LoggerPort
    started_at: datetime  # NEW: единый источник времени

    @classmethod
    def create(
        cls,
        run_id: RunID,
        run_type: RunType,
        logger: LoggerPort,
        started_at: datetime | None = None,
    ) -> "PipelineContext":
        """Create context with automatic timestamp if not provided."""
        return cls(
            run_id=run_id,
            run_type=run_type,
            logger=logger,
            started_at=started_at or datetime.now(UTC),
        )

    def bind_logger(self, **kwargs: Any) -> "PipelineContext":
        """Bind additional context to the logger."""
        new_logger = self.logger.bind(**kwargs)
        return PipelineContext(
            run_id=self.run_id,
            run_type=self.run_type,
            logger=new_logger,
            started_at=self.started_at,  # Preserve timestamp
        )
```

---

### T2: Использование context.started_at в RecordProcessor

**Файл:** `src/bioetl/application/core/record_processor.py`

#### Текущее состояние (строка 148)

```python
async def process_batch(
    self,
    records: list[dict[str, Any]],
    batch_id: BatchID,
) -> BatchResult:
    ingestion_ts = datetime.now(UTC)  # ← Создаёт новый timestamp
```

#### Требуемые изменения

```python
async def process_batch(
    self,
    records: list[dict[str, Any]],
    batch_id: BatchID,
) -> BatchResult:
    # Использовать timestamp из контекста для консистентности
    ingestion_ts = self._context.started_at  # ← Единый источник
```

---

### T3: Удаление datetime.now() из BronzeWriter

**Файл:** `src/bioetl/infrastructure/storage/bronze_writer.py`

#### Текущее состояние (строка 103)

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
    ...
    ingestion_ts = datetime.now(UTC)  # ← Дублирует timestamp!
```

#### Требуемые изменения

Добавить `ingestion_ts` как обязательный параметр:

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
    ingestion_ts: datetime,  # NEW: передаётся из application слоя
) -> Path:
    ...
    # Удалить: ingestion_ts = datetime.now(UTC)
    metadata = {
        "run_id": str(run_id),
        "run_type": run_type.value,
        "ingestion_ts": ingestion_ts.isoformat(),  # Используем переданный
        ...
    }
```

#### Обновление вызовов

**Файл:** `src/bioetl/application/core/record_processor.py:255-263`

```python
await self._storage.write_bronze(
    records=record_bytes,
    provider=self._provider,
    entity=self._entity_type,
    date=ingestion_ts,
    batch_id=batch_id,
    run_id=self._context.run_id,
    run_type=self._context.run_type,
    ingestion_ts=ingestion_ts,  # NEW: явная передача
)
```

---

### T4: Удаление datetime.now() из QuarantineManager

**Файл:** `src/bioetl/infrastructure/quarantine/unified.py`

#### Текущее состояние (строка 89)

```python
async def quarantine_record(...):
    ...
    record_data = {
        ...
        "ingestion_ts": datetime.now(UTC).isoformat(),  # ← Отдельный timestamp
    }
```

#### Требуемые изменения

```python
async def quarantine_record(
    self,
    record: dict[str, Any],
    error_type: ErrorType,
    batch_id: BatchID,
    error_message: str,
    ingestion_ts: datetime,  # NEW: передаётся из вызывающего кода
) -> None:
    record_data = {
        ...
        "ingestion_ts": ingestion_ts.isoformat(),  # Используем переданный
    }
```

---

### T5: Архитектурный тест на datetime.now() в infrastructure

**Файл:** `tests/architecture/test_no_datetime_now_in_infrastructure.py` (новый)

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

### Зависимости Фазы 3

```
T1 (PipelineContext) ──▶ T2 (RecordProcessor)
                              │
T3 (BronzeWriter) ────────────┤
                              │
T4 (Quarantine) ──────────────┴──▶ T5 (Arch test)
```

### Критерии приёмки Фазы 3

- [ ] `PipelineContext.started_at` — единственный источник времени для batch
- [ ] `datetime.now()` отсутствует в infrastructure слое
- [ ] Архитектурный тест блокирует добавление `datetime.now()` в infrastructure
- [ ] Все тесты используют фиксированные timestamps для детерминизма

### Риски Фазы 3

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Каскадные изменения сигнатур | Высокая | Постепенный rollout с backward-compatible defaults |
| Пропуск вызовов datetime.now() | Средняя | AST-тест + code review |

---

## Фаза 4: Повышение Наблюдаемости 🟢

### Цель
Консистентные метрики и трейсы через стандартизированные порты.

---

### O1: TracingContext в BaseTransformer

**Файл:** `src/bioetl/application/core/base_transformer.py`

#### Требуемые изменения

| № | Изменение | Описание |
|---|-----------|----------|
| 1 | Добавить span для transform | `with tracer.start_span("transform_record"):` |
| 2 | Добавить метрики duration | Histogram по entity_type |
| 3 | Добавить error tracking | Counter по error_type |

---

### O2: TracingContext в PipelineExecutor

**Файл:** `src/bioetl/application/core/executor.py`

#### Требуемые изменения

| № | Изменение | Описание |
|---|-----------|----------|
| 1 | Root span для batch | `with tracer.start_span(f"batch_{batch_id}"):` |
| 2 | Nested spans | fetch → transform → write_bronze → write_silver → write_gold |
| 3 | Span attributes | batch_id, record_count, run_type |

---

### O3: Graceful shutdown для tracer

**Файл:** `src/bioetl/application/core/runner.py`

#### Требуемые изменения

```python
async def run(self) -> None:
    try:
        await self._execute_pipeline()
    finally:
        await self._cleanup()

async def _cleanup(self) -> None:
    """Cleanup all resources including observability."""
    # Existing cleanup...

    # Flush tracer spans
    if hasattr(self._services, 'tracer') and self._services.tracer:
        try:
            self._services.tracer.close()
        except Exception as e:
            self._context.logger.warning(
                "Failed to close tracer",
                error=str(e),
            )
```

---

### O4: Тесты observer

**Файл:** `tests/unit/application/observability/test_observer.py`

| Тест | Описание |
|------|----------|
| `test_observer_records_duration` | Histogram записывается с корректными labels |
| `test_observer_tracks_errors` | Counter инкрементируется по error_type |
| `test_observer_graceful_shutdown` | Spans flushed при close() |
| `test_observer_handles_close_error` | Ошибка close() не падает pipeline |

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

### Фаза 1 🔴 Завершена Когда:
- [ ] `make test` проходит с детерминистичным джиттером
- [ ] `random` удалён из storage writers
- [ ] Архитектурный тест `test_no_random_in_writers` добавлен и проходит

### Фаза 2 🟠 Завершена Когда:
- [ ] Все режимы записи валидируются через Enum
- [ ] Schema drift обрабатывается явно (error/evolve/ignore)
- [ ] Тесты покрывают edge cases

### Фаза 3 🟡 Завершена Когда:
- [ ] `datetime.now()` отсутствует в infrastructure
- [ ] `PipelineContext.started_at` используется везде
- [ ] Архитектурный тест `test_no_datetime_now_in_infrastructure` проходит

### Фаза 4 🟢 Завершена Когда:
- [ ] Tracing spans покрывают ключевые операции
- [ ] Observer тесты проходят
- [ ] Graceful shutdown работает

### Фаза 5 🔵 Завершена Когда:
- [ ] RULES.md обновлён секцией §6.1 Determinism
- [ ] ADR-014 создан
- [ ] CI включает `make arch-all`

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
- [x] Entrypoints доступны для Prefect/REST

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

*Строй надёжно. Верифицируй перед предложением. Документируй с доказательствами.*
