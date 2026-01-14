# План Рефакторинга: Дублирующаяся Логика в BioETL

*Дата: 2026-01-14 | Analyst: Claude Code*

---

## Executive Summary (TL;DR)

- **Найдено дублирований**: 1 значительный паттерн
- **Потенциальное сокращение**: ~90 строк кода
- **Приоритетные**: Консолидация `BaseHttpAdapter` и `BaseSyncAdapter`
- **Риски**: Низкие (изменения внутренние, без breaking changes)
- **Вердикт**: Кодовая база **хорошо спроектирована**. Большинство потенциальных дублирований уже извлечены в базовые классы/миксины.

---

## Методология Анализа

### Инструменты
```bash
# Поиск повторяющихся сигнатур методов
rg "def \w+\(" src/bioetl/ -o --no-filename | sort | uniq -c | sort -rn

# Поиск дублирующихся async методов
rg "async def \w+\(" src/bioetl/ -o --no-filename | sort | uniq -c | sort -rn

# Сравнение похожих файлов
diff -u base.py sync_base.py

# Размеры файлов
wc -l src/bioetl/**/*.py | sort -rn
```

### Статистика Кодовой Базы
| Метрика | Значение |
|---------|----------|
| Python-файлов | 392 |
| Строк кода | ~72,554 |
| Адаптеров | 8 (chembl, pubchem, uniprot, pubmed, crossref, openalex, semanticscholar, idmapping) |
| Transformer-классов | 20+ |

---

## Детальный Анализ

### Паттерн 1: Дублирование в Base Adapter Classes

#### Severity: MEDIUM
#### Impact: ~90 строк дублированного кода

#### Locations (file:lines)
1. `src/bioetl/infrastructure/adapters/base.py:117-237` (120 строк)
2. `src/bioetl/infrastructure/adapters/sync_base.py:132-246` (114 строк)

#### Verification Commands
```bash
# Сравнение health_check методов
diff -u <(sed -n '117,140p' src/bioetl/infrastructure/adapters/base.py) \
        <(sed -n '132,155p' src/bioetl/infrastructure/adapters/sync_base.py)

# Сравнение check_health методов
diff -u <(sed -n '142,190p' src/bioetl/infrastructure/adapters/base.py) \
        <(sed -n '157,199p' src/bioetl/infrastructure/adapters/sync_base.py)

# Сравнение fallback и error_context методов
diff -u <(sed -n '204,237p' src/bioetl/infrastructure/adapters/base.py) \
        <(sed -n '213,246p' src/bioetl/infrastructure/adapters/sync_base.py)
```

#### Metrics
- **Количество дублирований**: 2 класса
- **Дублированные методы**: 5 (`health_check`, `check_health`, `_probe_health`, `_fallback_health_status`, `_get_error_context`)
- **Строк на каждый метод**: ~20-48 строк
- **Общая избыточность**: ~90 строк

#### Current Implementation

**BaseHttpAdapter (base.py:117-140)**:
```python
async def health_check(self) -> HealthStatus:
    ctx = self._start_health_check()
    try:
        status = await self._probe_health()
        self._handle_health_check_success(ctx, status)
        return status
    except Exception as e:
        fallback_status = self._fallback_health_status()
        self._handle_health_check_failure(ctx, e)
        return fallback_status
```

**BaseSyncAdapter (sync_base.py:132-155)** - IDENTICAL logic, different circuit breaker access:
```python
async def health_check(self) -> HealthStatus:
    ctx = self._start_health_check()
    try:
        status = await self._probe_health()
        self._handle_health_check_success(ctx, status)
        return status
    except Exception as e:
        fallback_status = self._fallback_health_status()
        self._handle_health_check_failure(ctx, e)
        return fallback_status
```

#### Differences Between Implementations
| Aspect | BaseHttpAdapter | BaseSyncAdapter |
|--------|----------------|-----------------|
| Circuit Breaker Access | `self.http_client.circuit_breaker` | `self.circuit_breaker` |
| HTTP Client | `UnifiedHTTPClient` | `ThreadPoolExecutor` + rate limiter |
| Context Manager | Delegates to http_client | Self-managed |

#### Proposed Solution

**Option A: Extract Health Check Mixin with Abstract Property (RECOMMENDED)**

Create `HealthCheckProviderMixin` that defines abstract `_get_circuit_breaker()`:

```python
# health_check_mixin.py - add abstract method
class HealthCheckProviderMixin(HealthCheckMixin):
    """Extended mixin with health check implementation."""

    @property
    @abstractmethod
    def _circuit_breaker(self) -> CircuitBreaker:
        """Return circuit breaker for health fallback."""
        ...

    async def health_check(self) -> HealthStatus:
        """Template method for health checks."""
        ctx = self._start_health_check()
        try:
            status = await self._probe_health()
            self._handle_health_check_success(ctx, status)
            return status
        except Exception as e:
            fallback_status = self._fallback_health_status()
            self._handle_health_check_failure(ctx, e)
            return fallback_status

    async def check_health(self) -> HealthCheckResult:
        """Perform health check with detailed result."""
        # ... consolidated implementation

    def _fallback_health_status(self) -> HealthStatus:
        try:
            return assess_health_from_circuit_breaker(self._circuit_breaker)
        except Exception:
            return HealthStatus.UNHEALTHY

    def _get_error_context(self, operation: str) -> dict[str, Any]:
        try:
            cb_state = self._circuit_breaker.get_state().value
            cb_failures = self._circuit_breaker.get_failure_count()
        except Exception:
            cb_state = None
            cb_failures = 0
        return {
            "circuit_breaker_state": cb_state,
            "circuit_breaker_failures": cb_failures,
        }
```

**Changes to existing classes:**

```python
# base.py
class BaseHttpAdapter(HealthCheckProviderMixin, DataSourcePort):
    @property
    def _circuit_breaker(self) -> CircuitBreaker:
        return self.http_client.circuit_breaker

# sync_base.py
class BaseSyncAdapter(HealthCheckProviderMixin, DataSourcePort):
    @property
    def _circuit_breaker(self) -> CircuitBreaker:
        return self.circuit_breaker
```

#### Breaking Changes
- [ ] **No** - Internal refactoring only
- Public interface unchanged (`health_check()`, `check_health()`)

#### Test Strategy
- [ ] Update existing `tests/unit/infrastructure/adapters/test_base_adapter.py`
- [ ] Update existing `tests/unit/infrastructure/adapters/test_sync_adapter.py`
- [ ] Add test for `HealthCheckProviderMixin` abstract method
- [ ] Verify coverage ≥85%

---

## Паттерны НЕ Являющиеся Дублированием

### 1. Transformer Hierarchy
**Verdict**: ✅ Properly Designed (Template Method Pattern)

```
BaseTransformer (674 LOC)
├── BaseChemblTransformer (184 LOC) - 10 ChEMBL transformers
└── BasePublicationTransformer (202 LOC) - 4 publication transformers
```

- `_transform_impl()` - abstract method for entity-specific logic
- `_extract_business_data()` - intentionally different per entity
- Common utilities centralized in base class

### 2. Title Fallback Handlers
**Verdict**: ✅ Already Extracted

Location: `src/bioetl/infrastructure/adapters/common/base_title_fallback.py`

- `BaseTitleFallbackHandler` (182 LOC) provides template
- `CrossRef`, `OpenAlex` adapters implement `_search_by_title()`

### 3. Provider Exception Hierarchies
**Verdict**: ✅ Intentionally Provider-Specific

| Provider | Exceptions | LOC |
|----------|-----------|-----|
| ChEMBL | `ChemblApiError`, `ChemblRateLimitError`, etc. | 120 |
| CrossRef | `CrossRefApiError`, `CrossRefNotFoundError`, etc. | 127 |

**Rationale**: Provider-specific error codes and retry logic require distinct handling.

### 4. `_build_headers()` in Adapters
**Verdict**: ✅ Intentionally Different

| Adapter | Headers |
|---------|---------|
| OpenAlex | `User-Agent: BioETL/1.0 (mailto:{email})` |
| CrossRef | `User-Agent: BioETL/1.0 (mailto:{email})` |
| SemanticScholar | `x-api-key: {api_key}` |

Different providers require different authentication/identification.

### 5. `_probe_health()` Implementations
**Verdict**: ✅ Template Method Pattern

Each adapter implements provider-specific health probe:
- ChEMBL: `/status.json` endpoint
- PubMed: `esearch` with minimal query
- UniProt: Lightweight search probe

### 6. AdapterMetrics Usage
**Verdict**: ✅ Consistent Pattern

All adapters use `self._adapter_metrics.measure_request()` consistently:
```python
with self._adapter_metrics.measure_request("/endpoint"):
    response = await self.http_client.get_once(url)
```

---

## План Реализации

### Phase 1: Подготовка (Pre-merge)
- [ ] Создать feature branch: `refactor/consolidate-health-check-mixin`
- [ ] Убедиться в coverage ≥85%: `pytest --cov=src/bioetl --cov-fail-under=85`

### Phase 2: Рефакторинг
- [ ] Расширить `HealthCheckMixin` в `health_check_mixin.py`
- [ ] Добавить abstract property `_circuit_breaker`
- [ ] Перенести методы из `BaseHttpAdapter`
- [ ] Модифицировать `BaseHttpAdapter` → implement `_circuit_breaker` property
- [ ] Модифицировать `BaseSyncAdapter` → implement `_circuit_breaker` property
- [ ] Удалить дублированный код из обоих классов

### Phase 3: Валидация
- [ ] `pytest tests/unit/infrastructure/adapters/ -v`
- [ ] `pytest tests/architecture/ -v`
- [ ] `mypy src/bioetl/ --strict`
- [ ] `make lint`
- [ ] Coverage ≥85%

---

## Риски и Митигация

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Regression в health checks | Низкая | Существующие тесты покрывают оба класса |
| Abstract method breaks subclasses | Низкая | Только 2 subclass, оба контролируемы |
| Circular imports | Очень низкая | Все в одном модуле adapters |

---

## Rollback Plan
1. `git revert <commit>` - изменения локализованы
2. Нет breaking changes - откат тривиален

---

## Заключение

Кодовая база BioETL **хорошо спроектирована** с точки зрения DRY:

1. **Transformer hierarchy** - правильно использует Template Method
2. **Title fallback** - уже извлечён в базовый класс
3. **Validation utilities** - централизованы в `validation.py`
4. **Adapter metrics** - унифицированы через `AdapterMetrics`

**Единственное значительное дублирование** - health check логика между `BaseHttpAdapter` и `BaseSyncAdapter` (~90 строк). Рекомендуется извлечь в расширенный `HealthCheckProviderMixin`.

**ROI оценка**: Рефакторинг сэкономит ~90 строк и упростит поддержку health check логики в одном месте. Риски минимальны.

---

## Приложения

### A. Команды для Верификации
```bash
# Проверить текущее состояние
wc -l src/bioetl/infrastructure/adapters/base.py
wc -l src/bioetl/infrastructure/adapters/sync_base.py

# Найти использование health_check
rg "async def health_check" src/bioetl/ -l

# Проверить наследование
rg "class.*BaseHttpAdapter|class.*BaseSyncAdapter" src/bioetl/ -A 1
```

### B. Affected Files Matrix
| File | LOC Before | LOC After (est.) | Delta |
|------|------------|------------------|-------|
| `health_check_mixin.py` | 215 | ~300 | +85 |
| `base.py` | 237 | ~150 | -87 |
| `sync_base.py` | 246 | ~160 | -86 |
| **Total** | 698 | ~610 | -88 |

### C. Related Documentation
- `docs/archived/refactoring-plan.md` - historical refactoring status
- `CLAUDE.md` §2.3 - architectural clarifications
- `docs/02-architecture/decisions/ADR-006-logger-metrics-ports.md` - observability architecture
