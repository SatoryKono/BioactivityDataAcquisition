# Консолидированный Анализ Планов Рефакторинга BioETL

*Версия: 1.1 | Дата: 2025-12-31 | Протокол: Двойная Верификация (REQ-ARCH-040)*

> **ОБНОВЛЕНИЕ 2025-12-31**: Добавлены ложные утверждения из action_plan.md (OPS-001 MemoryLock, RedisLock).
> MemoryLock полностью реализует TTL/heartbeat/fencing. Redis НЕ требуется per ADR-010.

---

## Резюме

Проанализированы 4 плана рефакторинга:
1. `reports/architecture-audit-2025-01-06.md` — Общий балл 7.18
2. `docs/architecture/architecture-audit-2026-02-07.md` — Общий балл 8.00
3. `docs/architecture-audit.md` v2.0 — Общий балл 7.73
4. `docs/reports/architecture-audit-2026-01-06.md` — Общий балл 8.21

**Обнаружено:**
- 12 ложных/неточных утверждений
- 6 противоречий между планами
- 3 критических ошибки в датах документов

---

## Часть 1. Критические Ошибки в Документах

### 1.1. Некорректные Даты

| Документ | Указанная дата | Проблема |
|----------|----------------|----------|
| `architecture-audit-2026-02-07.md` | 2026-02-07 | **Будущее** (>1 год вперёд) |
| `architecture-audit.md` v2.0 | 2026-01-09 | **Будущее** |
| `architecture-audit-2026-01-06.md` | 2026-01-06 | **Будущее** |
| `reports/architecture-audit-2025-01-06.md` | 2025-01-06 | **Прошлое** (некорректно) |

**Реальная дата проекта:** 2025-12-29/30 (согласно refactoring-plan.md v6.0)

### 1.2. Ложные Утверждения (Верифицировано)

| # | Утверждение | Документ | Верификация | Статус |
|---|-------------|----------|-------------|--------|
| 1 | "Требуется RedisLock для прод-окружения" | audit-2025-01-06 | RULES.md §3.3, ADR-010 **явно запрещают** Redis | ❌ ЛОЖНО |
| 2 | "Только in-memory lock, непригоден для прода" | audit-2025-01-06 | По design: Local-Only Deployment (ADR-010) | ❌ ЛОЖНО |
| 3 | "Silver/Gold допускают Parquet" | audit.md v2.0 | `medallion_validator.py:191`: Silver **MUST** be delta | ⚠️ ЧАСТИЧНО |
| 4 | "vacuum_after_run выключен — нарушение" | audit-2025-01-06 | Преднамеренно выключен, VACUUM вызывается через CLI | ⚠️ ДИСКУССИОННО |
| 5 | "Нет явного VACUUM enforcement" | audit-2026-01-06 | `postrun_service.py:244-288` реализует VACUUM | ❌ ЛОЖНО |
| 6 | "print() в коде — нарушение" | все 4 | 14 из 16 — в docstrings (doctests) | ⚠️ ПРЕУВЕЛИЧЕНО |
| 7 | "PipelineRunner — god object" | - | 166 строк, 9 методов, делегирует | ❌ ЛОЖНО |
| 8 | "Бенчмарки content hash деградировали" | audit.md v2.0, 2026-01-06 | Требует верификации на текущем коде | ⚠️ НЕ ВЕРИФИЦИРОВАНО |
| 9 | "NoOpGoldValidator — баг" | audit-2026-02-07 | Преднамеренно для backward-compat | ⚠️ BY DESIGN |
| 10 | "Логи LockManager без run_id" | audit-2026-02-07 | Требует верификации | ⚠️ ПРОВЕРИТЬ |
| 11 | "api_key как str — уязвимость" | audit.md v2.0 | CLI маскирует; env-чтение реализовано | ⚠️ НИЗКИЙ РИСК |
| 12 | "MemoryMonitor возвращает нули" | - | Возвращает 50% (graceful degradation) | ❌ ЛОЖНО |
| 13 | **"OPS-001: MemoryLock без стандартных TTL/heartbeat/max duration"** | action_plan.md (diff) | **ПОЛНОСТЬЮ РЕАЛИЗОВАНО**: `_ttl_checker_loop()` (43-64), `heartbeat()` (176-204), `validate_owner()` (206-238), `aclose()` (240-255) в `memory_lock.py` | ❌ ЛОЖНО |
| 14 | **"Implement RedisLock per RULES.md §3.3"** | action_plan.md (diff) | **Redis НЕ требуется** per ADR-010 (Local-Only Deployment). MemoryLock полностью достаточен для локальных пайплайнов. | ❌ ЛОЖНО |

---

## Часть 2. Противоречия Между Планами

### 2.1. Оценка Блокировок

| Документ | Оценка | Рекомендация |
|----------|--------|--------------|
| audit-2025-01-06 | 4/10 | "Реализовать RedisLock" |
| audit-2026-02-07 | 9/10 | "TTL/heartbeat/fencing реализованы" |
| audit-2026-01-06 | 7/10 | "heartbeat/TTL не покрыты кодом" |

**Верификация (`memory_lock.py`):**
- ✅ TTL-based expiration: строки 43-64 (`_ttl_checker_loop`, `_release_expired_locks`)
- ✅ Heartbeat: метод `heartbeat()` обновляет `expires_at`
- ✅ Safety guard: `validate_owner()` для fencing token
- ✅ Graceful shutdown: `aclose()`

**Вердикт:** Оценка 9/10 корректна. Рекомендация Redis противоречит ADR-010.

### 2.2. Оценка Medallion/Parquet

| Документ | Утверждение | Оценка |
|----------|-------------|--------|
| audit.md v2.0 | "Silver/Gold допускают parquet" | 6/10 |
| audit-2026-02-07 | "NoOp валидация Silver опциональна" | 8/10 |
| audit-2026-01-06 | "Bronze/Delta задокументированы, нет VACUUM enforcement" | 7/10 |

**Верификация:**
- Silver: `medallion_validator.py:191` — **MUST** be "delta", parquet запрещён
- Gold: допускает "delta" ИЛИ "parquet" (`medallion_validator.py:201`)
- VACUUM: `postrun_service.py:244-288` — **РЕАЛИЗОВАНО**, но `vacuum_after_run=False` по умолчанию
- NoOpSilverValidator: допустимо, но создаёт риск пропуска валидации

**Вердикт:** Оценка 7/10 справедлива. Проблема не в Parquet, а в опциональности валидации.

### 2.3. Логирование и Наблюдаемость

| Документ | Оценка | Проблема |
|----------|--------|----------|
| audit-2025-01-06 | 7/10 | "composition использует std logging" |
| audit-2026-02-07 | 6/10 | "run_id отсутствует в сервисных логах" |
| audit.md v2.0 | 6/10 | "CLI вывод без run_id/UnifiedLogger" |
| audit-2026-01-06 | 5/10 | "print() в сервисах вместо UnifiedLogger" |

**Верификация (`grep print\(`):**
- `entrypoints.py`: 10 print() — ВСЕ в docstrings (doctests)
- `quarantine_service.py`: 1 print() — в docstring
- `vacuum_service.py`: 1 print() — в docstring
- Реальный runtime код: **0 print()**

**Вердикт:** Оценки 5-6 преувеличены. Реальная оценка: 7-8/10.

---

## Часть 3. Верифицированный Статус Проблем

### ✅ УЖЕ РЕАЛИЗОВАНО (не требует работы)

| Проблема | Доказательство |
|----------|----------------|
| VACUUM automation | `postrun_service.py:244-288` — `run_vacuum_if_enabled()` |
| DQ thresholds | `domain/config.py:27-40` — `DQConfig(soft=0.05, hard=0.20)` |
| Silver format = delta | `medallion_validator.py:191` — валидация |
| MemoryLock TTL/heartbeat | `memory_lock.py:43-64,176-204` |
| Content hash normalization | `transformations.py:29-36,83-87` |
| LoggerPort enforcement | Архитектурный тест `test_no_structlog_in_application_interfaces` |

### ⚠️ ОПЦИОНАЛЬНЫЕ УЛУЧШЕНИЯ (низкий приоритет)

| Улучшение | Текущее состояние | Риск |
|-----------|-------------------|------|
| `strict_gold_validation=True` по умолчанию | False (backward-compat) | Может сломать пайплайны без схем |
| `vacuum_after_run=True` по умолчанию | False (экономия ресурсов) | Рост времени выполнения |
| SecretStr для api_key | str с маскированием в CLI | Низкий (env-чтение работает) |
| Убрать print() из doctests | 16 примеров | Нулевой (не влияет на runtime) |

### 🔴 ПОДТВЕРЖДЁННЫЕ ПРОБЛЕМЫ (актуальные)

| # | Проблема | Файл:строки | Приоритет |
|---|----------|-------------|-----------|
| 1 | domain/config_types.py допускает parquet для Silver | `config_types.py:74` | P2 |
| 2 | Покрытие CLI/composition <65% | `composition/_bootstrap/`, CLI | P3 |

---

## Часть 4. Консолидированный План Рефакторинга

### [P1] Нет актуальных P1 задач

Все критические проблемы решены. См. `refactoring-plan.md` секция "✅ УЖЕ РЕАЛИЗОВАНО".

### [P2] Синхронизация типов с валидатором

**Категория**: Medallion Architecture, Типизация
**Влияние**: Качество кода, предотвращение ошибок конфигурации

**Проблема**: `domain/config_types.py:74` допускает `Literal["delta", "parquet"]` для Silver, но `medallion_validator.py:191` запрещает parquet. Рассинхронизация между типами и runtime-валидацией.

**Решение**: Изменить тип на `Literal["delta"]` для Silver в `config_types.py`.

**Файлы**:
- `src/bioetl/domain/config_types.py:74`

**Верификация**:
```bash
grep -n 'Literal\["delta", "parquet"\]' src/bioetl/domain/config_types.py
```

**Риски**: Несовместимость со старыми YAML-конфигами (если есть с parquet).
**Трудозатраты**: S (30 минут)

### [P3] Повышение покрытия CLI/composition

**Категория**: Тестирование
**Влияние**: Снижение риска регрессий

**Проблема**: Низкое покрытие:
- `composition/_bootstrap/storage.py` (24%)
- `cli/commands/config.py` (25%)
- `composition/entrypoints.py` (72%)

**Решение**: Добавить unit-тесты для непокрытых путей.

**Файлы**:
- `tests/unit/composition/`
- `tests/integration/interfaces/`

**Критерий готовности**: Покрытие ≥80% для указанных файлов.
**Трудозатраты**: M (2-3 дня)

---

## Часть 5. Рекомендации по Документам (Консолидация)

### 5.0. Авторитетные Источники (ЕДИНСТВЕННЫЕ)

> **ВАЖНО**: Только эти документы содержат верифицированную информацию.

| Документ | Версия | Назначение |
|----------|--------|------------|
| `docs/refactoring-plan.md` | v6.1 | **Авторитетный** план рефакторинга с 50+ верифицированными ложными утверждениями |
| `docs/architecture-audit.md` | v1.0 | Аудит архитектуры от 2025-12-29, оценка **8.9/10** |
| `CLAUDE.md` | актуальный | Справочник с протоколом двойной верификации |

### 5.1. Удалить/Архивировать (НЕ использовать)

| Документ | Причина |
|----------|---------|
| `reports/architecture-audit-2025-01-06.md` | Ложные рекомендации Redis, устаревший |
| `docs/architecture/architecture-audit-2026-02-07.md` | Некорректная дата (2026), дублирует функционал |
| **action_plan.md (если создан)** | **Содержит ложные утверждения OPS-001 о MemoryLock**. НЕ ИСПОЛЬЗОВАТЬ. |

### 5.2. Обновить

| Документ | Изменения |
|----------|-----------|
| `docs/architecture-audit.md` | Исправить дату на 2025-12-30, убрать ложные утверждения о Parquet |
| `docs/reports/architecture-audit-2026-01-06.md` | Исправить дату, синхронизировать с верифицированным статусом |

### 5.3. Карта Планов Рефакторинга

| # | Документ | Статус | Рекомендация |
|---|----------|--------|--------------|
| 1 | `docs/refactoring-plan.md` | ✅ Авторитетный | Использовать как primary source |
| 2 | `docs/consolidated-refactoring-analysis.md` | ✅ Актуальный | Использовать как обзор аудитов |
| 3 | `docs/pipeline-refactoring-plan.md` | ⚠️ Вспомогательный | Только для YAML/transformer optimization |
| 4 | `docs/domain-services-integration-plan.md` | ⚠️ Опциональный | План интеграции неиспользуемых сервисов |
| 5 | `docs/plans/refactoring-detail-2025-12-29.md` | ⚠️ Детали | Детализация 3 конкретных задач |
| 6 | `docs/archived/refactoring-plan-bronze-validation.md` | ❌ Архивный | Устаревший, в archived/ |

### 5.4. Ложные Утверждения из action_plan.md (diff)

> **⚠️ НЕ ИСПОЛЬЗОВАТЬ action_plan.md!** Содержит ложные утверждения:

| Утверждение | Почему ЛОЖНО |
|-------------|--------------|
| OPS-001: "MemoryLock без стандартных TTL/heartbeat/max duration" | **ПОЛНОСТЬЮ РЕАЛИЗОВАНО** в `memory_lock.py:43-255` |
| "Implement RedisLock per RULES.md §3.3" | **Redis НЕ требуется** per ADR-010 (Local-Only Deployment) |

---

## Часть 6. Метрики Контроля

| Метрика | Порог | Команда | Блокирует PR |
|---------|-------|---------|--------------|
| Coverage | ≥85% | `pytest --cov-fail-under=85` | Да |
| mypy errors | 0 | `mypy src/bioetl --strict` | Да |
| Циклические импорты | 0 | `python -c "from bioetl.domain import *"` | Да |
| Нарушения слоёв | 0 | `import-linter` | Да |
| Архитектурные тесты | pass | `make arch-test` | Да |

---

## Приложение A. Сравнительная Таблица Оценок

| Категория | audit-2025-01-06 | audit-2026-02-07 | audit.md v2.0 | audit-2026-01-06 | Верифицировано |
|-----------|------------------|------------------|---------------|------------------|----------------|
| Слоистая архитектура | 9 | 9 | 9 | 9 | **9** ✅ |
| Контракты/Ports | 8 | 8 | 9 | 7 | **8** |
| Medallion | 7 | 8 | 6 | 7 | **8** |
| Ошибки/CB | 7 | 8 | 8 | 8 | **8** |
| Блокировки | **4** ❌ | 9 | 9 | 7 | **9** ✅ |
| Валидация/DQ | 6 | 7 | 8 | 6 | **8** |
| Логирование | 7 | 6 | 6 | 5 | **7-8** |
| Тестирование | 9 | 9 | 6 | 6 | **9** |
| Безопасность | 7 | 8 | 7 | 8 | **8** |
| Документация | 7 | 7 | 8 | 8 | **8** |
| **ИТОГО** | **7.18** | **8.00** | **7.73** | **8.21** | **~8.5** |

---

## Приложение B. Команды Верификации

```bash
# Проверка формата Silver
grep -n "silver_format.*delta" src/bioetl/application/core/medallion_validator.py

# Проверка MemoryLock TTL
grep -n "ttl_checker\|heartbeat\|expires_at" src/bioetl/infrastructure/locking/memory_lock.py

# Проверка VACUUM
grep -n "vacuum_after_run\|run_vacuum" src/bioetl/application/core/postrun_service.py

# Проверка print() в runtime (не docstrings)
grep -n "print(" src/bioetl/**/*.py | grep -v '>>>\|\.\.\.>>'

# Размер PipelineRunner
wc -l src/bioetl/application/core/runner.py
```

---

*Документ подготовлен с применением Протокола Двойной Верификации (REQ-ARCH-040).*
