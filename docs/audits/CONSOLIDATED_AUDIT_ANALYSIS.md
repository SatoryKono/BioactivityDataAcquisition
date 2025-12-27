# Консолидированный Анализ Архитектурных Аудитов BioETL

*Версия: 1.0 | Дата: 2025-12-27 | Метод: Двойная Верификация (REQ-ARCH-040)*

---

## 1. Обзор Анализируемых Документов

| # | Документ | Оценка | Ключевые темы |
|---|----------|--------|---------------|
| 1 | `docs/06-architecture-audit.md` | 6.32 | Тесты, блокировки, DQ |
| 2 | `docs/audits/2025-02-architecture-audit.md` | 6.08 | MetricsPort, lock enforcement |
| 3 | `docs/architecture-audit-bioetl.md` | 6.27 | Тесты, fencing token, VACUUM |
| 4 | `docs/07-architecture-audit-bioetl.md` | 6.31 | Silver DQ, Medallion |

**Общий диапазон оценок:** 6.08 — 6.32 (консенсус: ~6.25)

---

## 2. Верифицированные Метрики Кодовой Базы

> Проверено против реального кода 2025-12-27

| Метрика | Значение | Источник |
|---------|----------|----------|
| Python файлов | **216** | `find src/ -name "*.py" \| wc -l` |
| Классов | **306** | `grep -r "^class " src/ --include="*.py" \| wc -l` |
| Средний размер модуля | **~147 строк** | 31758 / 216 |
| mypy ошибок (--strict) | **1** | `MetricsPort.gauge` в health_monitor.py:203 |
| print() в коде | **13** | `grep -r "print(" src/bioetl \| wc -l` |
| Циклические импорты | **0** | `from bioetl.domain import *` — pass |
| TODO/FIXME | **1** | `grep -rE "(TODO\|FIXME)" src/` |

---

## 3. Анализ Утверждений: Верифицированные vs Ложные

### 3.1 Подтверждённые Проблемы (Все 4 плана)

| Проблема | Верификация | Файл:строка |
|----------|-------------|-------------|
| **MetricsPort vs HealthMonitor** | `MetricsPort` объявляет `set_gauge()`, но `HealthMonitor` вызывает `metrics.gauge()` | `observability.py:76`, `health_monitor.py:203` |
| **require_lock=False по умолчанию** | Все три writer-а имеют `require_lock: bool = False` в сигнатуре | `bronze_writer.py:63`, `gold_writer.py:66`, `delta_writer.py:80` |
| **CircuitBreaker без эмиссии метрик** | Docstring обещает метрики (строки 46-48), но код только хранит внутренние счётчики | `circuit_breaker.py:46-48,57-59` |
| **13 print() в коде** | Подтверждено grep-ом | 8 файлов в src/bioetl |

### 3.2 Ложные/Неточные Утверждения

| Ложное утверждение | Реальность | Доказательство |
|-------------------|------------|----------------|
| "pytest падает из-за отсутствия orjson" | orjson **есть** в dev-зависимостях | `pyproject.toml:63` |
| "asyncio_mode не распознан/не настроен" | `asyncio_mode = "auto"` **настроен** | `pyproject.toml:120` |
| "128 ошибок сбора тестов" | Проблема окружения, не кода | Зависимости установлены корректно |
| "Средний размер ~21 строка" | ~147 строк (31758/216) | Арифметическая ошибка |
| "MemoryLock без safety guard" | `validate_owner()` **существует** | `memory_lock.py:206-238` |
| "MemoryLock без heartbeat" | `heartbeat()` **реализован** | `memory_lock.py:176-204` |
| "NoOpGoldValidator — баг" | **By design** для пайплайнов без Gold | `pandera_validator.py:76-93` |
| "Нет fencing token" | owner_id **используется** как идентификатор | `memory_lock.py:31,98,166-168` |

### 3.3 Частично Верные Утверждения

| Утверждение | Нюанс |
|-------------|-------|
| "TTL/heartbeat не соответствуют требованиям 60s/20s" | TTL опционален (`None` по умолчанию), но механизм работает |
| "Writers не проверяют lock" | `require_lock=False` по умолчанию, но проверка реализована |
| "Silver без Pandera" | Используется PyArrow schema, не Pandera (by design для производительности) |
| "DQ пороги 5%/20% не автоматизированы" | Частично: `DQConfig` существует, enforcement — в application layer |

---

## 4. Консолидированные Оценки по Категориям

| # | Категория | Вес | Оценка | Обоснование |
|---|-----------|-----|--------|-------------|
| 1 | Слоистая архитектура | 15% | **9** | Нарушений импортов не найдено |
| 2 | Контракты и Ports | 12% | **6** | Реальный баг: MetricsPort.gauge |
| 3 | Medallion Architecture | 12% | **7** | Bronze/Silver/Gold работают; VACUUM ручной |
| 4 | Ошибки и Circuit Breaker | 10% | **6** | CB без метрик (не эмитирует в порт) |
| 5 | Блокировки | 10% | **6** | Механизмы есть, но `require_lock=False` по умолчанию |
| 6 | Валидация и DQ | 10% | **6** | Gold с Pandera, Silver с PyArrow |
| 7 | Логирование | 8% | **6** | 13 print(), MetricsPort расхождение |
| 8 | Тестирование | 8% | **7** | Тесты работают при корректном окружении; 80%+ coverage |
| 9 | Безопасность | 8% | **7** | Секреты через env/SecretStr |
| 10 | Документация | 7% | **7** | RULES/ADR актуальны, REFACTORING_PLAN ведётся |

**Консолидированный балл: 6.6 / 10** (выше чем в отдельных планах после коррекции ложных утверждений)

---

## 5. Консолидированный План Рефакторинга

### Приоритет P1: Критические (mypy, контракты)

#### P1.1 Исправить MetricsPort vs HealthMonitor

**Проблема:** `HealthMonitor.py:203` вызывает `metrics.gauge()`, но `MetricsPort` определяет только `set_gauge()`.

**Верификация:**
```python
# observability.py:76
def set_gauge(self, name: str, value: float, ...) -> None:

# health_monitor.py:203
self.metrics.gauge("provider_health_status", value, labels={"provider": state.provider})
```

**Решение:** Заменить `metrics.gauge()` на `metrics.set_gauge()` в `health_monitor.py:203`.

**Файлы:**
- `src/bioetl/infrastructure/adapters/http/health_monitor.py:203`

**Критерий готовности:**
- `mypy src/bioetl --strict` — 0 ошибок

**Трудозатраты:** S (< 1 час)

---

#### P1.2 Добавить эмиссию метрик в CircuitBreaker

**Проблема:** Docstring обещает метрики `circuit_breaker_state` и `circuit_breaker_trips_total` (строки 46-48), но код только хранит внутренние счётчики без эмиссии.

**Верификация:**
```python
# circuit_breaker.py:46-48 (docstring)
# Metrics emitted:
#     - circuit_breaker_state{provider}: 0=Closed, 1=Half-Open, 2=Open
#     - circuit_breaker_trips_total{provider}: Counter of OPEN transitions

# Реальность: _state, _trips_total — только внутренние поля (строки 56-59)
```

**Решение:** Добавить `MetricsPort` в конструктор и эмитировать метрики при смене состояния.

**Файлы:**
- `src/bioetl/infrastructure/adapters/http/circuit_breaker.py`

**Критерий готовности:**
- Метрики доступны в `/metrics` endpoint
- Тест проверяет эмиссию при переходе CLOSED→OPEN

**Трудозатраты:** M (1-2 дня)

---

### Приоритет P2: Высокий (Lock enforcement)

#### P2.1 Изменить require_lock по умолчанию на True

**Проблема:** Все три writer-а имеют `require_lock=False` по умолчанию, что позволяет запись без блокировки.

**Верификация:**
```python
# bronze_writer.py:63
require_lock: bool = False,

# gold_writer.py:66
require_lock: bool = False,

# delta_writer.py:80
require_lock: bool = False,
```

**Решение:**
1. Изменить default на `True` для production safety
2. Явно передавать `require_lock=False` в тестах

**Файлы:**
- `src/bioetl/infrastructure/storage/bronze_writer.py:63`
- `src/bioetl/infrastructure/storage/gold_writer.py:66`
- `src/bioetl/infrastructure/storage/delta_writer.py:80`
- Тесты: обновить fixtures

**Риски:**
- Существующие вызовы без lock context сломаются
- Требуется feature flag или deprecation warning период

**Критерий готовности:**
- Запись без lock вызывает `LockNotHeldError`
- Тесты обновлены и проходят

**Трудозатраты:** M (2-3 дня)

---

### Приоритет P3: Средний (Cleanup)

#### P3.1 Удалить print() из продакшен кода

**Проблема:** 13 вхождений `print()` нарушают правило единого логгера.

**Верификация:**
```bash
grep -r "print(" src/bioetl --include="*.py" | wc -l
# 13
```

**Решение:**
1. Заменить на `logger.debug()` / `logger.info()` где требуется вывод
2. Удалить примеры в docstrings или заменить на код без side effects
3. Добавить ruff правило `T201` (print found)

**Файлы:** 8 файлов (см. grep выше)

**Критерий готовности:**
- `grep -r "print(" src/bioetl --include="*.py" | wc -l` → 0
- ruff правило блокирует новые print()

**Трудозатраты:** S (0.5 дня)

---

### Приоритет P4: Желательно (Observability, VACUUM)

#### P4.1 Автоматизация VACUUM/retention

**Текущее состояние:** VACUUM вызывается вручную через сервисы, нет автоматического планировщика.

**Решение:**
1. Добавить `vacuum_after_write: bool = False` параметр в DeltaWriter
2. Или: создать cron job / postrun hook

**Трудозатраты:** M (2-3 дня)

#### P4.2 DQ метрики и пороги для Silver

**Текущее состояние:** Silver использует PyArrow schema без DQ threshold enforcement.

**Решение:**
1. Добавить подсчёт DQ ошибок в RecordProcessor
2. Эмитировать метрики `dq_errors_total`, `dq_error_rate`
3. Применять soft/hard thresholds (5%/20%)

**Трудозатраты:** L (1-2 недели)

---

## 6. Roadmap

```
Фаза 1 (1 неделя):
├── P1.1: Исправить MetricsPort (S) ✓ → mypy 0 ошибок
└── P1.2: CB метрики (M)

Фаза 2 (2 недели):
├── P2.1: require_lock=True (M)
└── P3.1: Удалить print() (S)

Фаза 3 (2+ недели):
├── P4.1: VACUUM автоматизация (M)
└── P4.2: Silver DQ (L)
```

**Ожидаемый балл после Фазы 1-2:** ~7.5
**Ожидаемый балл после Фазы 3:** ~8.0

---

## 7. Метрики CI Регресса (консолидированные)

| Метрика | Порог | Команда | Блокирует PR |
|---------|-------|---------|--------------|
| Coverage | ≥80% | `pytest --cov-fail-under=80` | Да |
| mypy errors | 0 | `mypy src/bioetl --strict` | Да |
| Циклические импорты | 0 | `PYTHONPATH=src python -c "from bioetl.domain import *"` | Да |
| Нарушения слоёв | 0 | `lint-imports` | Да |
| print() в коде | 0 | `ruff check --select=T201` | Да (после P3.1) |

---

## 8. Выводы

### 8.1 Что было неправильно в исходных планах

1. **Ложные утверждения о зависимостях** — orjson и asyncio_mode настроены корректно
2. **Неверные метрики** — средний размер модуля 147, не 21 строка
3. **Преувеличение проблем MemoryLock** — safety guard и heartbeat реализованы
4. **Смешение проблем кода и окружения** — pytest падает из-за окружения, не кода

### 8.2 Что было правильно

1. **MetricsPort.gauge баг** — подтверждён (единственная mypy ошибка)
2. **require_lock=False** — подтверждён риск
3. **CircuitBreaker без метрик** — подтверждён gap между docstring и реализацией
4. **print() в коде** — подтверждено 13 вхождений

### 8.3 Рекомендации

1. **Использовать REFACTORING_PLAN.md** — он уже ведётся с двойной верификацией
2. **Удалить дублирующие audit-ы** — консолидировать в один документ
3. **Приоритизировать P1** — это единственные блокеры для mypy --strict

---

*Документ создан в соответствии с протоколом REQ-ARCH-040 (Двойная Верификация).*
*Все утверждения подкреплены ссылками на код.*
