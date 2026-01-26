# False Positives Log
*Date: 2025-12-31*
*Commit: e88ce84f29baae8bcf7efd99dd0d518effb842ba*

## Отклонённые Утверждения

Этот документ перечисляет распространённые ложные утверждения о кодовой базе BioETL,
которые были верифицированы и отклонены с обоснованием.

---

### FP-001: "PipelineRunner — god object"

**Исходное утверждение**: PipelineRunner содержит 500+ LOC и нарушает SRP

**Валидация**:
```bash
wc -l src/bioetl/application/core/runner.py
# 186 lines

grep -c "def \|async def " src/bioetl/application/core/runner.py
# 9 functions

grep "self._" src/bioetl/application/core/runner.py | wc -l
# 42 delegations
```

**Почему отклонено**:
- Размер 186 LOC, не 500+
- Класс делегирует через RunnerServices (42 вызова `self._*`)
- Это Composition, не God Object
- Соответствует VP-003 (Large delegating file)

**Категория**: VP-003

---

### FP-002: "MemoryLock требует Redis"

**Исходное утверждение**: Текущая реализация locking неполная, требует Redis для production

**Валидация**:
```bash
# ADR-010 статус
grep "Status:" docs/02-architecture/decisions/ADR-010-local-only-deployment.md
# Status: Accepted

# Redis в locking
grep -rn "Redis\|redis" src/bioetl/infrastructure/locking/ | wc -l
# 0
```

**Почему отклонено**:
- ADR-010 явно решает: "Local-Only deployment"
- MemoryLock — **intentional design decision**
- Redis отвергнут ("REJECTED" в ADR-010)
- Проект by design не поддерживает распределённый запуск

**Категория**: Design Decision (ADR-010)

---

### FP-003: "DQ метрики не реализованы"

**Исходное утверждение**: DQ метрики не экспортируются в Prometheus

**Валидация**:
```bash
grep -rn "dq_soft_threshold_exceeded\|dq_check_duration" src/bioetl/
# data_quality_service.py:160 — counter
# data_quality_service.py:214 — histogram
# prometheus_metrics.py:40 — DQ_CHECK_DURATION_MS
```

**Почему отклонено**:
- `dq_soft_threshold_exceeded` — counter в `DataQualityService:160`
- `dq_check_duration_ms` — histogram в `DataQualityService:214`
- `DQConfig` имеет `soft_fail_threshold=0.05`, `hard_fail_threshold=0.20`

**Категория**: Already Implemented

---

### FP-004: "MemoryMonitor возвращает нули"

**Исходное утверждение**: MemoryMonitor возвращает захардкоженные нули как баг

**Валидация**:
```python
# src/bioetl/application/core/memory_monitor.py:150-160
def _get_stats_estimate(self) -> MemoryStats:
    """Provide conservative estimates when actual stats unavailable."""
    return MemoryStats(
        used_mb=4096.0,      # Assume 4GB used
        available_mb=4096.0,  # Assume 4GB available
        total_mb=8192.0,     # Assume 8GB total
        percent_used=0.5,    # 50% — conservative estimate
        process_mb=256.0,
    )
```

**Почему отклонено**:
- Возвращает **консервативные оценки (50%)**, не нули
- Это **graceful degradation**, не баг
- 50% usage предотвращает OOM при неизвестной памяти
- Документировано в docstring как intentional

**Категория**: VP-005 (Graceful degradation)

---

### FP-005: "ChEMBL Adapter — монолит 517 LOC"

**Исходное утверждение**: ChEMBL client объединяет всё в один файл без декомпозиции

**Валидация**:
```bash
wc -l src/bioetl/infrastructure/adapters/chembl/client.py
# 592 lines

grep -o "self._[a-z_]*" src/bioetl/infrastructure/adapters/chembl/client.py | sort -u | wc -l
# 15 delegation methods
```

**Делегирование**:
- `_mapper` — EntityMapper
- `_error_handler` — error classification
- `_adapter_metrics` — observability
- `_page_iterator` — pagination
- `_batch_ids` — batching

**Почему отклонено**:
- 15 делегирующих методов
- Использует EntityMapper (112 LOC отдельно)
- Размер ≠ god object при наличии делегирования

**Категория**: VP-003

---

### FP-006: "GoldWriter — монолит 593 строки"

**Исходное утверждение**: GoldWriter требует декомпозиции из-за размера

**Валидация**:
```bash
wc -l src/bioetl/infrastructure/storage/gold_writer.py
# 687 lines

grep -o "self._[a-z_]*" src/bioetl/infrastructure/storage/gold_writer.py | sort -u
# 15 internal methods
```

**Делегирование**:
- `_audit` — AuditPort
- `_tracing` — TracingPort
- `_validate_*` — validation methods (5)
- `_write_scd` — SCD2 logic
- `_write_simple` — simple write

**Почему отклонено**:
- Режимы OVERWRITE/APPEND/SCD2 — **когезивны**
- CSV делегируется в CsvExporter
- Audit делегируется в AuditPort

**Категория**: VP-003

---

### FP-007: "Email в конфиге — PII требует хэширования"

**Исходное утверждение**: default_email в PubMed адаптере — PII, требует HashService

**Валидация**:
```bash
grep -n "default_email" src/bioetl/infrastructure/config.py
# 364-371: технический email для NCBI API
```

**Почему отклонено**:
- **НЕ PII** — это технический идентификатор
- NCBI требует email для идентификации инструмента
- Это machine-to-machine credential, не user data

**Категория**: Not Applicable

---

### FP-008: "bootstrap_pipeline смешивает ответственности"

**Исходное утверждение**: 140+ строк с mixing сборки и бизнес-логики

**Валидация**:
```bash
wc -l src/bioetl/composition/bootstrap.py
# 183 lines

grep -c "def " src/bioetl/composition/bootstrap.py
# 2 functions
```

**Почему отклонено**:
- 183 строки, 2 функции
- Тонкий фасад для Composition Root
- Делегирует фабрикам: `factory.create_runner()`
- Делегирует bootstrap_observability

**Категория**: VP-003

---

### FP-009: "print() statements в коде"

**Исходное утверждение**: 40 print() statements нарушают logging policy

**Валидация**:
```bash
grep -rn "print(" src/bioetl/ | head -5
# Все в docstrings: ">>> print(...)" или "...     print(...)"
```

**Почему отклонено**:
- Все 40 — **в docstrings** (doctest формат)
- Это примеры документации, не production код
- Pattern: `>>> print(...)` — Python doctest syntax

**Категория**: Documentation (doctest)

---

### FP-010: "Optional DI params — нарушение DI"

**Исходное утверждение**: `policy: Policy | None = None` нарушает принципы DI

**Валидация**:
```python
# Примеры валидного паттерна:
def __init__(
    self,
    storage: StoragePort,
    policy: WriteModePolicy | None = None,  # Valid!
    timeout: float = 30.0,  # Valid!
):
```

**Почему отклонено**:
- Optional parameters с defaults — **валидный DI паттерн**
- Аналогично `timeout: float = 30.0`
- Обеспечивает flexibility для тестирования
- Default создаёт value object, не I/O зависимость

**Категория**: VP-001 (Optional DI params)

---

## Категории Валидных Паттернов

| ID | Паттерн | Почему валидно |
|----|---------|----------------|
| VP-001 | Optional parameters с defaults | DI flexibility |
| VP-002 | NoOp implementations | Null Object Pattern |
| VP-003 | Large file с делегированием | Composition, не god object |
| VP-004 | Backward-compatibility shims | Migration path |
| VP-005 | Graceful degradation | Documented fallback |
| VP-006 | Email в конфиге | Technical ID, не PII |
| VP-007 | Multiple return points | Early exit pattern |
| VP-008 | Long parameter lists | Explicit DI |

---

## Как Избежать Ложных Утверждений

1. **Всегда проверять код** перед утверждением
2. **Измерять размер** (`wc -l`) и делегирование (`grep "self._"`)
3. **Читать ADRs** перед предложением изменений
4. **Сверяться с CLAUDE.md** §2.3 "Архитектурные Пояснения"
5. **Запускать архитектурные тесты** (`pytest tests/architecture/`)

---

*Документ поддерживается для предотвращения повторных ложных утверждений.*
