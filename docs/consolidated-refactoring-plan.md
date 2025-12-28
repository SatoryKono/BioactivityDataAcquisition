# Консолидированный План Рефакторинга BioETL

*Версия: 1.3 | Дата: 2025-12-27 | Статус: В работе*

> **Источник**: Сравнительный анализ 4 планов рефакторинга с верификацией кодом.
> **Протокол**: Двойная верификация согласно `docs/RULES.md` §7 (REQ-ARCH-040).

---

## Содержание

1. [Резюме анализа](#резюме-анализа)
2. [Выявленные неточности](#выявленные-неточности-в-планах)
3. [Верифицированный статус](#верифицированный-статус-реализации)
4. [Актуальные задачи](#актуальные-задачи-рефакторинга)
5. [Roadmap](#roadmap)

---

## Резюме анализа

### Проанализированные документы

| # | Документ | Версия | Ключевой фокус |
|---|----------|--------|----------------|
| 1 | `docs/refactoring-plan.md` | v5.6 | Детерминизм, Medallion, единый источник времени |
| 2 | `docs/refactoring-plan-bronze-validation.md` | v1.0 | Bronze Validation, Safety Guards |
| 3 | `docs/consolidated-refactoring-analysis.md` | v1.0 | Сводный анализ 4 аудитов |
| 4 | `docs/06-architecture-audit.md` (diff) | v1 | Архитектурный аудит с балльной оценкой |

### Ключевые выводы

| Категория | Количество | Примечание |
|-----------|------------|------------|
| **Ложные утверждения** | ~12 | Задачи уже реализованы, но помечены как TODO |
| **Неточности в метриках** | ~8 | LOC, количество методов, баллы |
| **Устаревшие данные** | ~5 | Код изменился после написания планов |
| **Актуальные задачи** | 5 | Требуют реальной работы |

---

## Выявленные неточности в планах

### ❌ ЛОЖНЫЕ УТВЕРЖДЕНИЯ (уже реализовано!)

| Утверждение | Источник | Реальность | Верификация |
|-------------|----------|------------|-------------|
| **"Safety Guard для Storage Writers — НЕ РЕАЛИЗОВАНО"** | BRONZE_VALIDATION.md Задача 4 | ✅ РЕАЛИЗОВАНО | `delta_writer.py:230-269`, `gold_writer.py:114-150`, `bronze_writer.py:175-210` — `_validate_lock_held()` |
| **"LockContext нужно создать"** | BRONZE_VALIDATION.md Задача 4 | ✅ РЕАЛИЗОВАНО | `domain/locking.py:43-123` — полная реализация с `is_valid()`, `matches_table()`, `create()` |
| **"Parquet разрешён в sink config — нарушает RULES.md"** | CONSOLIDATED.md P1.2 | ✅ РЕАЛИЗОВАНО | `pipeline_config.py:261-271` — валидация с `ValueError` для Silver/Gold |
| **"Тесты падают из-за orjson"** | 06-audit.md | ✅ НЕАКТУАЛЬНО | `pyproject.toml:50` — `orjson>=3.9` в зависимостях |
| **"Нет архитектурных тестов"** | 06-audit.md | ✅ РЕАЛИЗОВАНО | 26 файлов в `tests/architecture/` |
| **"Bronze Validation Enhancement нужна"** | BRONZE_VALIDATION.md Задача 1 | ✅ РЕАЛИЗОВАНО | `bronze_writer.py:151-178` — `_validate_json_records()` |
| **"Gold Contracts Documentation нужна"** | BRONZE_VALIDATION.md Задача 3 | ✅ РЕАЛИЗОВАНО | `docs/contracts/gold/` — 3 JSON Schema файла |

### ⚠️ НЕТОЧНОСТИ В МЕТРИКАХ

| Файл | Утверждение | Реальность | Расхождение |
|------|-------------|------------|-------------|
| `runner.py` | 173 строки (refactoring-plan.md) | **166 строк** | -7 строк |
| `bootstrap.py` | ~100-140 строк (несколько планов) | **182 строки** | +42-82 строки |
| `gold_writer.py` | 593-674 строки (разные планы) | **740 строк** | +66-147 строк |
| Arch tests | "нет" или "20+" | **26 файлов** | — |

### 🔄 УСТАРЕВШИЕ ДАННЫЕ

| Утверждение | Источник | Текущий статус |
|-------------|----------|----------------|
| "M3: Bronze validation ⏳" | REFACTORING_PLAN.md:125 | ✅ Реализовано |
| "mypy 27-32 ошибки" | Все планы | Требует проверки |
| "require_lock=False — проблема" | 06-audit.md | Валидация существует, но отключена по умолчанию |

---

## Верифицированный статус реализации

### ✅ УЖЕ РЕАЛИЗОВАНО (не требует работы)

| Компонент | Файл:строки | Дата верификации |
|-----------|-------------|------------------|
| **LockContext value object** | `domain/locking.py:43-123` | 2025-12-27 |
| **LockNotHeldError exception** | `domain/locking.py:20-39` | 2025-12-27 |
| **_validate_lock_held() в DeltaWriter** | `delta_writer.py:230-269` | 2025-12-27 |
| **_validate_lock_held() в GoldWriter** | `gold_writer.py:114-150` | 2025-12-27 |
| **_validate_lock_held() в BronzeWriter** | `bronze_writer.py:175-210` | 2025-12-27 |
| **Parquet запрещён для Silver/Gold** | `pipeline_config.py:261-271` | 2025-12-27 |
| **Bronze JSON validation** | `bronze_writer.py:151-178` | 2025-12-27 |
| **Gold Contracts** | `docs/contracts/gold/*.json` | 2025-12-27 |
| **Детерминистичный jitter** | `domain/resilience.py:45-84` | 2025-12-26 |
| **SilverWriteMode/GoldWriteMode Enums** | `delta_writer.py:53-64`, `gold_writer.py:42-54` | 2025-12-26 |
| **Schema drift handling** | `delta_writer.py:303-393` | 2025-12-26 |
| **PipelineContext.started_at** | `context.py:109` | 2025-12-27 |

---

## Актуальные задачи рефакторинга

### Приоритет 1 (P1): КРИТИЧЕСКИЕ

#### P1.1: Включить require_lock=True по умолчанию ✅ ВЫПОЛНЕНО

**Статус**: ✅ ВЫПОЛНЕНО (2025-12-27)
**Коммит**: `ec13bba` — feat(storage): enable require_lock=True by default in writers

| Параметр | Значение |
|----------|----------|
| Изменения | `require_lock=True` в `bronze_writer.py:63`, `delta_writer.py:80`, `gold_writer.py:66` |
| Тесты | Все fixtures обновлены с `require_lock=False` |
| Файлы | 15 файлов изменено |

---

#### P1.2: Исправить mypy ошибки

**Статус**: ⚠️ ТРЕБУЕТ ПРОВЕРКИ
**Проблема**: Планы указывают 27-32 ошибки mypy --strict.

| Параметр | Значение |
|----------|----------|
| Команда проверки | `mypy --strict src/bioetl` |
| Целевое состояние | 0 ошибок |
| Трудозатраты | S-M (1-2 дня) |

**Критерий готовности**:
```bash
mypy --strict src/bioetl 2>&1 | grep -c "error:"
# Должен вернуть 0
```

---

### Приоритет 2 (P2): ВЫСОКИЙ

#### P2.1: Автоматизировать VACUUM

**Статус**: ⚠️ ТРЕБУЕТСЯ
**Проблема**: `MedallionLifecycleService.vacuum()` существует, но нет автоматического вызова.

| Параметр | Значение |
|----------|----------|
| Текущее состояние | Ручной вызов через CLI |
| Целевое состояние | Автоматический вызов после успешного run (настраивается в YAML) |
| Файлы | `medallion_lifecycle.py`, `runner.py`, config |
| Трудозатраты | M (2 дня) |

**Целевой конфиг**:
```yaml
maintenance:
  auto_vacuum: true
  vacuum_retention_days: 7
```

---

#### P2.2: Обновить документацию планов

**Статус**: ⚠️ ТРЕБУЕТСЯ
**Проблема**: Планы содержат устаревшую информацию и ложные утверждения.

| Параметр | Значение |
|----------|----------|
| Файлы | `docs/refactoring-plan.md`, `docs/refactoring-plan-bronze-validation.md`, `docs/consolidated-refactoring-analysis.md` |
| Действие | Пометить реализованные задачи как ✅, удалить дублирующие документы |
| Трудозатраты | S (0.5 дня) |

**Рекомендация**: Консолидировать все планы в один документ (этот файл).

---

### Приоритет 3 (P3): ЖЕЛАТЕЛЬНО

#### P3.1: Централизованный ProviderHealthMonitor

**Статус**: ⏳ ЧАСТИЧНО РЕАЛИЗОВАНО
**Проблема**: Логика health monitoring размазана по адаптерам.

| Параметр | Значение |
|----------|----------|
| Текущее состояние | Каждый адаптер управляет своим состоянием |
| Целевое состояние | Централизованный `ProviderHealthMonitor` с метриками |
| Файлы | `infrastructure/adapters/http/health_monitor.py` (новый) |
| Трудозатраты | M (2-3 дня) |

---

#### P3.2: Очистить print() из docstrings

**Статус**: ⏳ ЖЕЛАТЕЛЬНО
**Проблема**: 13 вхождений print() в docstring/примерах.

| Параметр | Значение |
|----------|----------|
| Трудозатраты | S (0.5 дня) |
| Команда проверки | `grep -r "print(" src/bioetl --include="*.py" \| wc -l` |

---

## НЕ требуют рефакторинга (закрытые вопросы)

| Предложение | Почему закрыто |
|-------------|----------------|
| "Создать LockContext value object" | УЖЕ РЕАЛИЗОВАНО: `domain/locking.py:43-123` |
| "Добавить _validate_lock_held() в writers" | УЖЕ РЕАЛИЗОВАНО: все 3 writers |
| "Запретить Parquet для Silver/Gold" | УЖЕ РЕАЛИЗОВАНО: `pipeline_config.py:261-271` |
| "Добавить Bronze JSON validation" | УЖЕ РЕАЛИЗОВАНО: `bronze_writer.py:151-178` |
| "Создать Gold Contracts" | УЖЕ РЕАЛИЗОВАНО: `docs/contracts/gold/` |
| "Убрать fallback NoOp из writers" | Null Object Pattern — валидный паттерн |
| "Разбить bootstrap_pipeline" | Уже делегирует, 182 строки приемлемо |

---

## Roadmap

```
Фаза 1 (1 неделя): P1 — Критические
├── ✅ P1.1: require_lock=True (ВЫПОЛНЕНО 2025-12-27)
└── ⏳ P1.2: mypy fix (требует проверки в CI)
    Ожидаемый результат: CI стабилен, блокировки обязательны

Фаза 2 (1 неделя): P2 — Высокий
├── P2.1: VACUUM автоматизация (2 дня)
└── ✅ P2.2: Обновить документацию (В ПРОЦЕССЕ)
    Ожидаемый результат: Автоматизация, актуальные docs

Фаза 3 (по необходимости): P3 — Желательно
├── P3.1: ProviderHealthMonitor (2-3 дня)
└── P3.2: Очистить print() (0.5 дня)
```

---

## Метрики контроля (CI)

| Метрика | Порог | Команда | Блокирует PR |
|---------|-------|---------|--------------|
| Coverage | ≥80% | `pytest --cov-fail-under=80` | Да |
| mypy errors | 0 | `mypy --strict src/bioetl` | Да |
| Arch tests | pass | `make arch-test` | Да |
| require_lock | True | grep в writers | Да (после Фазы 1) |

---

## Приложение: Команды верификации

```bash
# Проверить реализацию lock validation
grep -n "_validate_lock_held" src/bioetl/infrastructure/storage/*.py

# Проверить LockContext
grep -n "class LockContext" src/bioetl/domain/locking.py

# Проверить Parquet validation
grep -A5 "format.*parquet" src/bioetl/infrastructure/schemas/pipeline_config.py

# Проверить mypy
mypy --strict src/bioetl 2>&1 | grep -c "error:"

# Проверить require_lock default
grep "require_lock: bool = " src/bioetl/infrastructure/storage/*.py
```

---

*Верифицировано: 2025-12-27 | Протокол: REQ-ARCH-040 (двойная верификация)*
