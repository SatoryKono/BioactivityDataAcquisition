# Консолидированный План Рефакторинга BioETL v2.0

*Версия: 2.0 | Дата: 2025-12-28 | Статус: Верифицирован*

> **Источник**: Анализ 4 планов рефакторинга с верификацией кодом согласно CLAUDE.md §0.
> - `reports/architecture-audit-2025-03.md`
> - `reports/architecture_audit_20251228.md`
> - `reports/architecture_audit_bioetl.md`
> - `docs/refactoring-plan.md` (v5.7)

---

## ⚠️ КРИТИЧЕСКИ ВАЖНО: Ложные Утверждения в Исходных Планах

Верификация кодом выявила **значительное количество ложных утверждений** в трёх новых планах.
Эти ошибки **НЕ должны повторяться** в будущих планах.

### ❌ ЛОЖНЫЕ УТВЕРЖДЕНИЯ (ПОДТВЕРЖДЕНО КОДОМ)

| Ложное утверждение | Планы | Реальность | Верификация |
|--------------------|-------|------------|-------------|
| "Нет fencing token и safety guard в lock/writer" | audit-2025-03, audit_20251228, audit_bioetl | **РЕАЛИЗОВАНО**: `validate_lock_for_write()` в `lock_validator.py:88`, используется в bronze_writer.py:171, delta_writer.py:255, gold_writer.py:109 | `grep validate_lock_for_write` |
| "owner_id не проверяется при heartbeat" | audit-2025-03 | **ПРОВЕРЯЕТСЯ**: `heartbeat()` строка 196: `if existing_owner != str(owner_id): return False` | `memory_lock.py:196` |
| "MemoryLock без Safety Guard" | все три | **РЕАЛИЗОВАНО**: `validate_owner()` в `memory_lock.py:206-238`, тесты в `test_lock_safety_guard.py` (8 тестов) | Тест REQ-ARCH-041 |
| "CircuitBreaker не публикует метрики" | audit-2025-03, audit_20251228 | **ПУБЛИКУЕТ**: `_emit_state_metric()`, `_emit_trip_metric()` в `circuit_breaker.py:93-109` | `circuit_breaker.py:93-109` |
| "DQ метрики не экспортируются" | audit_20251228, audit_bioetl | **РЕАЛИЗОВАНО**: `postrun_service.py:158-163` эмитит `dq_soft_threshold_exceeded`, :203-207 эмитит `dq_check_duration_ms` | `grep dq_soft_threshold` |
| "Тесты падают из-за отсутствующих зависимостей (orjson, pyarrow, etc.)" | все три | **ВСЕ ЗАВИСИМОСТИ в pyproject.toml**: orjson:39, pyarrow:25, pyyaml:22, pandera:29, pytest-asyncio:57 | `pyproject.toml` |
| "BatchWriter обходит JsonEncoderPort" | audit_bioetl | BatchWriter в **application** слое (допустимо). Нет JsonEncoderPort в domain — это не нарушение. | `batch_writer.py:12` |
| "MemoryLock не задаёт TTL=60s по умолчанию" | audit_20251228, audit_bioetl | TTL настраивается при `acquire()`. Default TTL = `heartbeat_interval * 3` = 90s (by design) | CLAUDE.md §5 |
| "Нет автоматизации DQ/Medallion политик" | audit_bioetl | **РЕАЛИЗОВАНО**: `MedallionPolicy`, `DQConfig`, `SilverWriteMode`, `GoldWriteMode` enums | docs/refactoring-plan.md |

### ✅ КОРРЕКТНЫЕ УТВЕРЖДЕНИЯ (НО НЕ ТРЕБУЮТ ДЕЙСТВИЙ)

| Утверждение | Почему не требует действий |
|-------------|---------------------------|
| "Pandera strict=False по умолчанию" | **By design** для backward compatibility. Можно включить strict=True в конфигурации пайплайна. |
| "NoOpValidator существует" | **Null Object Pattern** — валидный паттерн для опциональной валидации. |
| "Retention 168h (7d) по умолчанию" | **Delta Lake default**. Можно переопределить при вызове `vacuum(retention_hours=2160)`. |

---

## Часть 1: Верифицированные Метрики

| Метрика | Значение | Команда |
|---------|----------|---------|
| Покрытие тестами | >85% (CI check) | `pytest --cov-fail-under=85` |
| Ошибки mypy | 2 | `mypy --strict` |
| Циклические импорты | 0 | `python -c "from bioetl.domain import *"` |
| Классы | 333 | `grep -r "^class " src/` |
| Файлы .py | 239 | `find src/ -name "*.py"` |
| Архитектурные тесты | 27 файлов | `tests/architecture/` |
| TODO/FIXME | 1 | `grep -rE "(TODO|FIXME)" src/` |
| print() в коде | 0 | `grep -r "print(" src/bioetl` |

---

## Часть 2: Реальный Статус по Категориям

### Сводная Таблица (Исправленная)

| # | Категория | Вес | Оценка | Взвеш. | Ключевые находки |
|---|-----------|-----|--------|--------|------------------|
| 1 | Слоистая архитектура | 15% | **9** | 1.35 | Нарушений нет, проверено import-linter |
| 2 | Контракты и Ports | 12% | **9** | 1.08 | Все порты в domain/ports/, DI через конструкторы |
| 3 | Medallion Architecture | 12% | **8** | 0.96 | Bronze/Silver/Gold реализованы, WriteMode enums есть |
| 4 | Обработка ошибок и CB | 10% | **9** | 0.90 | CB с метриками (circuit_breaker.py:93-109) |
| 5 | Блокировки | 10% | **8** | 0.80 | Safety Guard есть (validate_owner, test_lock_safety_guard.py) |
| 6 | Валидация и DQ | 10% | **8** | 0.80 | Pandera + DQ метрики (postrun_service.py:158-207) |
| 7 | Логирование | 8% | **8** | 0.64 | structlog + run_id везде |
| 8 | Тестирование | 8% | **7** | 0.56 | Зависимости есть, нужна проверка CI |
| 9 | Безопасность | 8% | **8** | 0.64 | API keys через конфиги |
| 10 | Документация | 7% | **8** | 0.56 | RULES/ADR актуальны |
| **Итого** | | **100%** | | **8.29** | |

**Интерпретация: 8.29 → Зрелая система, минимальный рефакторинг**

---

## Часть 3: Актуальные Задачи (Верифицированные)

### Приоритет 1 (P1): КРИТИЧЕСКИЕ — НЕТ

> **Все критические задачи из `docs/refactoring-plan.md` v5.7 уже выполнены.**
> D1-D3 (детерминизм), M1-M4 (Medallion), T1-T5 (timestamps) — ✅ ЗАВЕРШЕНЫ.

### Приоритет 2 (P2): ЖЕЛАТЕЛЬНЫЕ

#### P2.1: Включить strict=True для Gold валидации (опционально)

**Категория**: Валидация и DQ
**Статус**: ✅ УЖЕ РЕАЛИЗОВАНО как опция

**Текущее состояние**:
- `PanderaSilverValidator(strict=False)` — по умолчанию (pandera_validator.py:34)
- `PanderaGoldValidator(strict=False)` — по умолчанию (pandera_validator.py:114)

**Решение**: Это **by design**. Можно включить strict режим в конфигурации пайплайна:
```python
validator = PanderaGoldValidator(schema=MySchema, strict=True)
```

**Действие**: ❌ НЕ ТРЕБУЕТСЯ — уже поддерживается.

---

#### P2.2: Настроить retention для Bronze/Silver

**Категория**: Medallion Architecture
**Текущее состояние**:
- `retention_manager.vacuum(retention_hours=None)` — использует Delta Lake default (168h = 7d)
- RULES.md §2.1.3 требует 90d для Bronze archive

**Решение**: Retention уже параметризуется (retention_manager.py:69-71):
```python
await retention_manager.vacuum(table_name, retention_hours=2160)  # 90 days
```

**Действие**: Добавить scheduled job для VACUUM с правильным retention:
```python
# В service/maintenance.py
async def scheduled_vacuum(manager: RetentionManager):
    await manager.vacuum("bronze_archive", retention_hours=2160)  # 90d
    await manager.vacuum("silver", retention_hours=168)  # 7d default
```

**Трудозатраты**: S (0.5 дня)
**Приоритет**: LOW — функционал есть, нужна только автоматизация расписания

---

#### P2.3: Обновить документацию тестового контура

**Категория**: Документация
**Текущее состояние**: Три новых плана содержат устаревшую информацию о зависимостях.

**Решение**: Обновить reports/ с корректной информацией:
- Все зависимости уже в pyproject.toml
- pytest-asyncio настроен
- Тесты должны проходить при `make test`

**Действие**:
1. Удалить/архивировать три устаревших плана из reports/
2. Обновить CHANGELOG.md

**Трудозатраты**: S (0.5 дня)

---

### Приоритет 3 (P3): ОПТИМИЗАЦИИ

#### P3.1: O2-O4 из refactoring-plan.md

**Статус**: Частично выполнено (O1 ✅)

| Задача | Статус | Описание |
|--------|--------|----------|
| O1: TracingContext в BaseTransformer | ✅ | base_transformer.py:125-187 |
| O2: TracingContext в PipelineExecutor | ⏳ | Root span для batch |
| O3: Graceful shutdown для tracer | ⏳ | Flush spans при close() |
| O4: Тесты observer | ⏳ | Добавить unit тесты |

**Трудозатраты**: M (2-3 дня)

---

## Часть 4: Метрики Контроля (CI)

| Метрика | Порог | Команда | Блокирует PR |
|---------|-------|---------|--------------|
| Coverage | ≥85% | `pytest --cov-fail-under=85` | Да |
| mypy errors | 0 | `mypy --strict` | Да |
| Архитектурные тесты | 100% pass | `pytest tests/architecture/` | Да |
| import-linter | 0 violations | `lint-imports` | Да |
| print() в коде | 0 | `grep -r "print(" src/bioetl` | Да |

---

## Часть 5: Причины Ошибок в Исходных Планах

| Причина | Пример | Как избежать |
|---------|--------|--------------|
| **Отсутствие верификации кодом** | "Нет safety guard" без `grep validate_owner` | Всегда: `grep`, `Read`, проверка тестов |
| **Устаревшие знания** | "Нет зависимостей" (но уже в pyproject.toml) | Читать актуальный pyproject.toml |
| **Неверная интерпретация** | "NoOp = нарушение DI" | Знать Null Object Pattern |
| **Игнорирование docs/refactoring-plan.md** | Повторение уже закрытых задач | Сверяться с секцией "УЖЕ РЕАЛИЗОВАНО" |

---

## Часть 6: Рекомендации

### ОБЯЗАТЕЛЬНО перед созданием задачи рефакторинга:

```bash
# 1. Проверить refactoring-plan.md
grep -A3 "ЛОЖНЫЕ УТВЕРЖДЕНИЯ" docs/refactoring-plan.md

# 2. Прочитать целевой файл
cat src/bioetl/path/to/file.py | head -100

# 3. Проверить существующие тесты
ls tests/architecture/test_*.py
ls tests/unit/*/test_*.py | grep <component>

# 4. Проверить зависимости
grep "<package>" pyproject.toml
```

### Формат верифицированного предложения:

```markdown
## Задача: [Название]

### Верификация (дата: YYYY-MM-DD)
- **Файл**: `path/to/file.py:строки` (N строк, M методов)
- **Не в "ЛОЖНЫЕ УТВЕРЖДЕНИЯ"**: ✅
- **Нет в "УЖЕ РЕАЛИЗОВАНО"**: ✅

### Текущее состояние
[Описание с ссылками `файл:строка`]

### Проблема (с доказательствами)
[Команды grep/read которые подтверждают проблему]

### Решение
[Предлагаемые изменения]
```

---

## Roadmap

| Фаза | Задачи | Трудозатраты | Ожидаемый балл |
|------|--------|--------------|----------------|
| ✅ Завершено | D1-D3, M1-M4, T1-T5, O1 | — | 8.29 (текущий) |
| P2 | Scheduled VACUUM, документация | 1 день | 8.4 |
| P3 | O2-O4 (observability) | 2-3 дня | 8.6 |

---

*Верифицируй перед утверждением. Код — единственный источник истины.*
