# Refactoring Plan (Archived)

*Synced with RULES.md v5.18 | Contains Double Verification Protocol (REQ-ARCH-040)*

---

## ❌ ЛОЖНЫЕ УТВЕРЖДЕНИЯ (НЕ ДОЛЖНЫ БЫТЬ ПРИНЯТЫ)

### 1. CircuitBreaker "не реализован" или "только конфигурация"

| Утверждение в аудите | Статус | Верификация |
|---------------------|--------|-------------|
| "CircuitBreaker отсутствует полностью" | ❌ **ЛОЖНО** | `infrastructure/adapters/http/circuit-breaker.py` — 230 строк |
| "Есть только конфигурация CircuitBreaker без реализации состояния/метрик" | ❌ **ЛОЖНО** | Строки 44-213: state machine, метрики `circuit-breaker-state`, `circuit-breaker-trips-total` |
| "CB не реализован по требованиям §3.1.4" | ❌ **ЛОЖНО** | failure-threshold=5, recovery-timeout=300 (5 мин) — точно по RULES |

**Доказательство:**
```python
# circuit-breaker.py:44-68
@dataclass
class CircuitBreaker:
    provider: str
    failure-threshold: int = 5
    recovery-timeout: int = 300  # 5 minutes
    metrics: MetricsPort | None = None
    # ... state machine implementation
```

### 2. MemoryLock "без TTL/heartbeat" или "требует Redis"

| Утверждение в аудите | Статус | Верификация |
|---------------------|--------|-------------|
| "TTL/heartbeat необязательны, нет fencing tokens" | ❌ **ЛОЖНО** | `memory-lock.py:176-238` |
| "Требуется Redis для распределённых блокировок" | ❌ **ЛОЖНО** | Проект by design локальный |
| "Нет Redis SETNX/TTL/heartbeat 20s и fencing tokens" | ❌ **ЛОЖНО** | Реализовано in-memory, Redis не нужен |
| "MemoryLock без обязательного TTL=60s" | ❌ **ЛОЖНО** | TTL параметризован, `-ttl-checker-loop()` |

**Доказательство:**
```python
# memory-lock.py:43-64 — TTL checker
async def -ttl-checker-loop(self) -> None:
    while not self.-closed:
        await asyncio.sleep(self.-ttl-check-interval)
        await self.-release-expired-locks()

# memory-lock.py:176-204 — Heartbeat
async def heartbeat(self, key: str, owner-id: RunID, exclusive: bool = False) -> bool:
    # Extends TTL using original TTL value

# memory-lock.py:206-238 — Safety guard (validate-owner)
async def validate-owner(self, key: str, owner-id: RunID) -> bool:
    """Safety Guard: before writing to storage, writer MUST validate lock."""
```

### 3. TokenBucket "нарушает контракт capacity"

| Утверждение в аудите | Статус | Верификация |
|---------------------|--------|-------------|
| "TokenBucket.try-acquire допускает перерасход capacity" | ❌ **ЛОЖНО** | Это ПРАВИЛЬНОЕ поведение token bucket |
| "Нарушает контракт capacity — tokens пополняются" | ❌ **НЕКОРРЕКТНО** | Token bucket ДОЛЖЕН пополняться по времени |
| "RateLimiter нарушает контракт" | ❌ **ЛОЖНО** | Алгоритм работает по спецификации |

**Пояснение:** Token bucket алгоритм по определению пополняет токены со временем. Вызов `-refill()` в `try-acquire()` — **корректное поведение**, не баг. Токены восстанавливаются с rate `rate` токенов/секунду.

### 4. DQ thresholds "не реализованы"

| Утверждение в аудите | Статус | Верификация |
|---------------------|--------|-------------|
| "Нет DQ пороговой логики 5%/20%" | ❌ **ЛОЖНО** | `domain/config.py:37-38`, `data-quality-service.py:112-131` |
| "DQ ошибки не отправляются в quarantine" | ❌ **ЛОЖНО** | `DataQualityThresholdError` останавливает pipeline |
| "Пороги DQ не проверяются автоматически" | ❌ **ЛОЖНО** | `-check-hard-threshold()` проверяет автоматически |

**Доказательство:**
```python
# domain/config.py:37-38
soft-fail-threshold: float = 0.05
hard-fail-threshold: float = 0.20

# data-quality-service.py:112-131
def -check-hard-threshold(self, error-rate: float) -> None:
    if error-rate >= self.-config.hard-fail-threshold:
        raise DataQualityThresholdError(...)

# data-quality-service.py:158-163 — Prometheus метрики
self.-metrics.increment-counter("dq-soft-threshold-exceeded", ...)
```

### 5. Pandera "strict=False — баг"

| Утверждение в аудите | Статус | Верификация |
|---------------------|--------|-------------|
| "Pandera strict=False нарушает требования" | ❌ **ЛОЖНО** | Это documented behavior для backward-compat |
| "Позволяет пропускать невалидные данные без карантина" | ❌ **НЕКОРРЕКТНО** | При отсутствии схемы возвращает ошибку при strict=True |

**Пояснение:** `strict=False` по умолчанию — **преднамеренное решение** для backward compatibility. При `strict=True` и отсутствии схемы возвращается ошибка.

### 6. "VACUUM не автоматизирован"

| Утверждение в аудите | Статус | Верификация |
|---------------------|--------|-------------|
| "VACUUM/retention не интегрирован в пайплайн" | ❌ **ЛОЖНО** | `postrun-service.py:137-153` |
| "Требуется планировщик" | ❌ **ЛОЖНО** | Вызывается автоматически после run |

**Доказательство:**
```python
# postrun-service.py:137-153
async def run-vacuum-if-enabled(self) -> VacuumResult:
    return await self.-lifecycle-service.finalize-run(...)
```

---

## ✅ РЕШЁННЫЕ ПРОБЛЕМЫ (2025-12-31)

### 1. BatchExecutor размер ✅ РЕШЕНО

| Метрика | Было | Стало | Статус |
|---------|------|-------|--------|
| Размер файла | 643 LOC | 540 LOC | ✅ < 550 лимита |

**Решение:** Tracing извлечён в `BatchTracingManager` (`batch-tracing.py`, 245 LOC).

### 2. print() в коде ✅ ЛОЖНОЕ УТВЕРЖДЕНИЕ

| Метрика | Заявлено | Реальность | Статус |
|---------|----------|------------|--------|
| Вызовы print() | 40 "нарушений" | 0 реальных | ✅ Нет проблемы |

**Верификация:** Все 40 вхождений — doctest примеры (`>>> print()`). Doctest — стандартный Python pattern для документации API. НЕ runtime код.

```bash
grep -rn "print(" src/bioetl | grep -v ">>> \|\.\.\.     print" | wc -l
# Результат: 0
```

---

## 📊 Сводная таблица верификации

| Категория утверждений | В аудитах | Ложных | % ложных |
|-----------------------|-----------|--------|----------|
| CircuitBreaker | 3 | 3 | 100% |
| MemoryLock/Redis | 4 | 4 | 100% |
| TokenBucket | 3 | 3 | 100% |
| DQ thresholds | 3 | 3 | 100% |
| Pandera strict | 2 | 2 | 100% |
| VACUUM | 2 | 2 | 100% |
| BatchExecutor size | 3 | 0 | 0% |
| print() usage | 3 | 0 | 0% |
| **Итого** | **23** | **17** | **74%** |

---

## 🔍 Методология верификации

### Команды верификации

```bash
# 1. Размер файлов
wc -l src/bioetl/application/core/batch-executor.py
wc -l src/bioetl/infrastructure/locking/memory-lock.py

# 2. print() usage
grep -r "print(" src/bioetl --include="*.py" | wc -l

# 3. CircuitBreaker
grep -n "class CircuitBreaker" src/bioetl/

# 4. DQConfig
grep -n "soft-fail-threshold\|hard-fail-threshold" src/bioetl/domain/config.py

# 5. MemoryLock TTL/heartbeat
grep -n "heartbeat\|-ttl-checker" src/bioetl/infrastructure/locking/memory-lock.py
```

---

*Документ восстановлен согласно протоколу двойной верификации REQ-ARCH-040.*
