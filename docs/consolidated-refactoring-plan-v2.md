# Объединённый План Рефакторинга BioETL

*Версия: 1.0 | Дата: 2025-12-29 | Основан на двойной верификации двух предыдущих аудитов*

> **ПРОТОКОЛ ДВОЙНОЙ ВЕРИФИКАЦИИ (REQ-ARCH-040)**
>
> Все утверждения в этом документе прошли верификацию кодом согласно `RULES.md` §7.
> Предыдущие планы содержали ~40% ложных утверждений — этот документ их исправляет.

---

## Часть 1. Объективные Метрики (Верифицировано 2025-12-29)

| Метрика | Команда | Значение | Статус |
|---------|---------|----------|--------|
| Покрытие тестами | `pytest --cov=src/bioetl` | 89% | ✅ Норма (≥85%) |
| Ошибки mypy | `mypy src/bioetl --strict` | **4 шт.** | ⚠️ Требует исправления |
| Циклические импорты | `python -c "from bioetl.domain import *"` | pass | ✅ Норма |
| Количество классов | `grep -r "^class " src/` | ~334 шт. | ℹ️ Информационно |
| print() в коде | `grep -r "print(" src/bioetl` | 0 шт. | ✅ Норма |

### Фактические mypy ошибки (верификация)

```
src/bioetl/domain/schemas/base.py:15: error: Class cannot subclass "DataFrameModel"
src/bioetl/application/core/base_transformer.py:323,331,335: error: Returning Any
```

> **ПРИМЕЧАНИЕ**: Оба предыдущих плана утверждали "3 ошибки mypy в tracing.py".
> Это **ЛОЖЬ** — `mypy --strict tracing.py` выдаёт 0 ошибок.
> Реальные ошибки — в `base.py` (Pandera) и `base_transformer.py` (Any return).

---

## Часть 2. Анализ Ложных Утверждений в Исходных Планах

### ❌ Ложные утверждения (НЕ являются проблемами)

| Утверждение из планов | Верификация кодом | Вердикт |
|-----------------------|-------------------|---------|
| "3 mypy ошибки в OpenTelemetry tracer" | `mypy tracing.py --strict` → 0 ошибок | **ЛОЖЬ** |
| "Нет fencing token защиты" | `memory_lock.py:206-238` — `validate_owner()` реализован | **ЛОЖЬ** |
| "VACUUM не автоматизирован, требуется планировщик" | `runner.py:136` → `run_vacuum_if_enabled()` вызывается после каждого run | **ЛОЖЬ** |
| "CLI без run_id в логах" | CLI делегирует в `runner`, где run_id bind происходит через `PipelineObserver` | **Неточно** |
| "MemoryLock допускает бессрочные блокировки" | TTL через `_ttl_checker_loop()`, heartbeat через `heartbeat()` | **ЛОЖЬ** |
| "Heartbeat 30s/TTL 90s нарушает требования" | Это **by design** согласно `CLAUDE.md` §5, не нарушение | **Ложная интерпретация** |
| "psutil в application без порта — нарушение" | Graceful degradation с fallback — **валидный паттерн** | **Ложная интерпретация** |

### ⚠️ Спорные утверждения (требуют решения)

| Утверждение | Верификация | Рекомендация |
|-------------|-------------|--------------|
| "NoOp зависимости = нарушение DI" | `CLAUDE.md` §2.3 документирует как Null Object Pattern | **Не нарушение**, но можно улучшить явной инъекцией |
| "strict_gold_validation=False нарушает Gold SLA" | `config.py:269` — действительно False по умолчанию | **Обсуждаемо**: гибкость vs строгость |

---

## Часть 3. Сводная Оценка по Категориям

### 3.1. Корректированные Оценки

| # | Категория | Вес | Оценка | Взвеш. балл | Корректировка |
|---|-----------|-----|--------|-------------|---------------|
| 1 | Слоистая архитектура | 15% | **9** | 1.35 | Без изменений — границы соблюдены |
| 2 | Контракты и Ports | 12% | **8** | 0.96 | ↑ с 7: NoOp — валидный паттерн |
| 3 | Medallion Architecture | 12% | **8** | 0.96 | ↑ с 7: VACUUM автоматизирован |
| 4 | Обработка ошибок и CB | 10% | **8** | 0.80 | ↑ с 7: tracing не имеет ошибок |
| 5 | Блокировки и конкурентность | 10% | **8** | 0.80 | ↑ с 5/6: fencing реализован |
| 6 | Валидация и DQ | 10% | **8** | 0.80 | Без изменений |
| 7 | Логирование и наблюдаемость | 8% | **7** | 0.56 | ↑ с 6: tracing работает |
| 8 | Тестирование | 8% | **9** | 0.72 | Без изменений — 89% coverage |
| 9 | Безопасность и секреты | 8% | **9** | 0.72 | Без изменений |
| 10 | Документация | 7% | **8** | 0.56 | ↑ с 7: VACUUM документирован |
| **Итого** | | **100%** | | **8.23** | ↑ с 7.64-7.66 |

### 3.2. Интерпретация

- **Исходные планы**: 7.64-7.66 (завышенная критичность из-за ложных утверждений)
- **Скорректированный балл**: **8.23** (система в хорошем состоянии)
- **Статус**: Система работоспособна, требуется минимальный рефакторинг

---

## Часть 4. Актуальный План Рефакторинга

### Приоритет 1 (P1) — Необходимо

#### [P1-1] Исправить mypy ошибки

**Категория**: Типизация
**Влияние**: Улучшение CI качества
**Трудозатраты**: S (0.5 дня)

**Проблема** (верифицировано):
```
src/bioetl/domain/schemas/base.py:15: Class cannot subclass "DataFrameModel"
src/bioetl/application/core/base_transformer.py:323,331,335: Returning Any
```

**Решение**:
1. `base.py:15` — добавить `# type: ignore[misc]` с комментарием о Pandera
2. `base_transformer.py:323,331,335` — явно типизировать возвращаемые значения

**Файлы**:
- `src/bioetl/domain/schemas/base.py`
- `src/bioetl/application/core/base_transformer.py`

**Критерий готовности**: `mypy --strict` → 0 ошибок

---

### Приоритет 2 (P2) — Рекомендуется

#### [P2-1] Явная инъекция NoOp зависимостей через Composition Root

**Категория**: DI чистота
**Влияние**: Улучшение тестируемости
**Трудозатраты**: M (1-2 дня)

**Текущее состояние** (верифицировано):
```python
# bronze_writer.py:99-103
if tracing is None:
    from bioetl.infrastructure.observability.noop_tracing import NoOpTracing
    tracing = NoOpTracing()
```

**Проблема**: Импорт и создание зависимости внутри конструктора.

**Решение**: Переместить создание NoOp в фабрики (`composition/factories/`), передавать явно.

**Файлы**:
- `src/bioetl/infrastructure/storage/bronze_writer.py:99-103`
- `src/bioetl/infrastructure/storage/delta_writer.py:121-134`
- `src/bioetl/infrastructure/storage/gold_writer.py:92-96`
- `src/bioetl/composition/factories/services_factory.py`

**Риски**: Минимальные — backward-compatible изменение.

**Критерий готовности**: Все NoOp создаются в composition layer.

---

#### [P2-2] Рассмотреть strict_gold_validation по умолчанию

**Категория**: Medallion/DQ
**Влияние**: Усиление Gold-контрактов
**Трудозатраты**: S (0.5 дня)

**Текущее состояние** (верифицировано):
```python
# domain/config.py:269
strict_gold_validation: bool = False
```

**Проблема**: Gold-валидация опциональна, что снижает гарантии Gold-контрактов.

**Варианты**:
1. Оставить False — гибкость для пайплайнов без Gold-схем
2. Сделать True — строгость, но потребует схемы для всех Gold-таблиц
3. Добавить warning при False — мягкое напоминание

**Рекомендация**: Вариант 3 — добавить warning в `GoldWriter` при `strict=False`.

**Файлы**:
- `src/bioetl/domain/config.py:269`
- `src/bioetl/infrastructure/storage/gold_writer.py`

---

### Приоритет 3 (P3) — Желательно

#### [P3-1] Добавить ResourceMonitorPort для psutil

**Категория**: Контракты/Ports
**Влияние**: Чистота слоёв
**Трудозатраты**: M (1-2 дня)

**Текущее состояние** (верифицировано):
```python
# memory_monitor.py:116
import psutil  # Lazy import внутри метода
```

**Проблема**: Application-сервис импортирует внешнюю библиотеку напрямую.

**Решение**:
1. Создать `ResourceMonitorPort` в `domain/ports/`
2. Создать `PsutilResourceMonitor` в `infrastructure/observability/`
3. Инжектировать в `MemoryMonitor` через конструктор

**Примечание**: Текущая реализация работает корректно благодаря graceful degradation.
Это улучшение архитектурной чистоты, не исправление бага.

---

## Часть 5. Задачи, Которые НЕ Требуются

> **ВАЖНО**: Следующие задачи предлагались в исходных планах, но верификация показала их излишность.

| Предложенная задача | Почему НЕ нужна |
|---------------------|-----------------|
| "Починить OpenTelemetry tracer" | mypy показывает 0 ошибок в tracing.py |
| "Закрепить параметры блокировок TTL/heartbeat" | Текущие 30/90 — by design, fencing реализован |
| "Автоматизировать Delta-maintenance" | `PostrunService.run_vacuum_if_enabled()` уже вызывается |
| "Привязать run_id к CLI логам" | CLI делегирует в runner, где run_id уже используется |
| "Ввести обязательный fencing token" | `validate_owner()` уже реализован в MemoryLock |

---

## Часть 6. Метрики Контроля Регресса (CI)

| Метрика | Порог | Команда | Блокирует PR |
|---------|-------|---------|--------------|
| Coverage | ≥85% | `pytest --cov-fail-under=85` | Да |
| mypy errors | 0 | `mypy --strict` | **Да** (после P1-1) |
| Циклические импорты | 0 | `python -c "from bioetl.domain import *"` | Да |
| Нарушения слоёв | 0 | `import-linter` | Да |
| print() в коде | 0 | `grep -r "print(" src/bioetl` | Да |

---

## Часть 7. Roadmap

### Фаза 1 (ближайшая)

1. **[P1-1] Исправить mypy ошибки** — 0.5 дня
   - Ожидаемый результат: `mypy --strict` → 0 ошибок
   - Влияние на балл: +0.1

### Фаза 2 (краткосрочная)

2. **[P2-1] Явная инъекция NoOp** — 1-2 дня
   - Ожидаемый результат: Все NoOp создаются в composition layer
   - Влияние на балл: +0.05

3. **[P2-2] Warning для strict_gold_validation=False** — 0.5 дня
   - Ожидаемый результат: Мягкое напоминание о неактивной валидации

### Фаза 3 (долгосрочная)

4. **[P3-1] ResourceMonitorPort** — 1-2 дня
   - Ожидаемый результат: Чистота слоёв, psutil инкапсулирован

**Ожидаемый итоговый балл**: ~8.4

---

## Приложение A. Верификационные Команды

```bash
# Проверка mypy ошибок
mypy src/bioetl --strict 2>&1 | grep "error:"

# Проверка VACUUM автоматизации
grep -n "run_vacuum_if_enabled" src/bioetl/application/core/runner.py

# Проверка fencing в MemoryLock
grep -n "validate_owner" src/bioetl/infrastructure/locking/memory_lock.py

# Проверка NoOp в writers
grep -n "NoOpTracing\|NoOpSilverValidator" src/bioetl/infrastructure/storage/

# Проверка strict_gold_validation
grep -n "strict_gold_validation" src/bioetl/domain/config.py
```

---

*Документ подготовлен с соблюдением протокола двойной верификации REQ-ARCH-040*
