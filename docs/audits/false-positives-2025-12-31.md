# False Positives Log

*Date: 2025-12-31*
*Commit: ef113536793feab13f14fbaa9fe055920cee374d*

---

## Обзор

Этот документ фиксирует утверждения, которые были **отклонены** в ходе аудита как ложные или неприменимые. Цель — предотвратить повторение ложных выводов в будущих аудитах.

**Общее количество отклонённых утверждений: 0** (в текущем аудите)

> **Примечание:** Предыдущие аудиты выявили ~130 ложных утверждений, которые задокументированы в `docs/refactoring-plan.md` секция "ЛОЖНЫЕ УТВЕРЖДЕНИЯ".

---

## Валидные Паттерны (НЕ проблемы)

Эти паттерны часто ошибочно идентифицируются как проблемы, но являются **валидными архитектурными решениями**.

### VP-001: Optional DI Parameters

**Паттерн:** `param: T | None = None`

**Пример:**
```python
class SomeService:
    def __init__(self, policy: WritePolicy | None = None):
        self._policy = policy or DefaultPolicy()
```

**Почему валидно:**
- Flexibility для тестов (можно передать mock)
- Convenience для production (default работает)
- Соответствует Python best practices

**Проверка:** Используется корректно в `delta_writer.py:98`

---

### VP-002: NoOp Implementations

**Паттерн:** Null Object Pattern для observability

**Примеры:**
- `NoOpMetrics` — metrics без side effects
- `NoOpTracing` — tracing без external calls
- `NoOpLogger` — logging без output

**Почему валидно:**
- Null Object Pattern из GoF
- Соответствует ADR-022
- Позволяет domain слою не зависеть от конкретных реализаций
- Упрощает тестирование

**Проверка:** `noop_*.py` в `infrastructure/observability/`

---

### VP-003: Large Files with Delegation

**Паттерн:** Файлы 500+ LOC с активным делегированием

**Примеры:**
| Файл | LOC | Делегирований | Вердикт |
|------|-----|---------------|---------|
| GoldWriter | 687 | 15 | OK |
| BronzeWriter | 603 | 12 | OK |
| ChEMBL client | 592 | 17 | OK |

**Почему валидно:**
- Размер ≠ god object
- Наличие делегирования (>10 `self._*` вызовов) указывает на Composition
- Высокая когезия (все методы связаны с write operations)

**Проверка:**
```bash
grep -o "self\._[a-z_]*" src/bioetl/infrastructure/storage/gold_writer.py | sort -u | wc -l
# Result: 15
```

---

### VP-004: Backward Compatibility Shims

**Паттерн:** Re-export в `__init__.py` для совместимости

**Пример:**
```python
# application/core/medallion_policy.py (19 строк)
from bioetl.domain.medallion import MedallionPolicy
__all__ = ["MedallionPolicy"]
```

**Почему валидно:**
- Migration path для старого кода
- Не дублирование — просто re-export
- Позволяет постепенный переход

**Проверка:** Файл содержит только import и re-export

---

### VP-005: Graceful Degradation

**Паттерн:** Консервативные fallback значения при недоступности ресурса

**Пример:** `MemoryMonitor._get_stats_estimate()`
```python
def _get_stats_estimate(self) -> MemoryStats:
    # При недоступности psutil возвращаем консервативные оценки
    return MemoryStats(
        percent_used=50.0,  # Консервативная оценка
        available_mb=1024,
        # ...
    )
```

**Почему валидно:**
- Documented behavior
- Лучше переоценить нагрузку, чем недооценить
- Кросс-платформенность (psutil может быть недоступен)

**Проверка:** `memory_monitor.py:170-180`

---

### VP-006: Email in Config

**Утверждение:** "Email в config требует хэширования как PII"

**Почему ЛОЖНО:**
- `default_email` — технический идентификатор для NCBI API
- NCBI требует email для идентификации инструмента
- Это NOT PII (персональные данные пользователей)

**Проверка:**
- `config.py:454-460` — контекст использования
- `pubmed_client.py:38-42` — как используется с NCBI API

---

### VP-007: Print in Docstrings

**Паттерн:** `>>> print(...)` в doctest примерах

**Статистика:** 40 вхождений `print()` в src/bioetl/

**Почему НЕ проблема:**
```bash
grep -rn "print(" src/bioetl/ | grep -v ">>> \|\.\.\.     print" | wc -l
# Result: 0
```

Все 40 вхождений — doctest примеры, не runtime код.

---

## Ложные Срабатывания из Предыдущих Аудитов

> Полный список см. в `docs/refactoring-plan.md` секция "ЛОЖНЫЕ УТВЕРЖДЕНИЯ" (130+ записей)

### Категории ложных утверждений:

| Категория | Примеров | Причина |
|-----------|----------|---------|
| "God object" без проверки делегирования | 8 | Размер ≠ сложность |
| "Не реализовано" (но реализовано) | 25+ | Устаревшие знания |
| "Нарушает DI" (но валидный паттерн) | 10+ | Неверная интерпретация |
| "Баг" (но design decision) | 15+ | Отсутствие контекста |
| "Требуется Redis" (но ADR-010) | 5+ | Игнорирование ADR |

### Топ-5 самых частых ложных утверждений:

1. **"PipelineRunner — god object"**
   - Реальность: 186 LOC, 13 делегирований

2. **"MemoryLock требует Redis"**
   - Реальность: ADR-010 явно supersedes Redis (Local-Only)

3. **"DQ метрики не реализованы"**
   - Реальность: `postrun_service.py:158-163` эмитит метрики

4. **"Content hash не исключает meta-поля"**
   - Реальность: `META_FIELDS` в `transformations.py:29-36`

5. **"Нет валидации write mode"**
   - Реальность: `SilverWriteMode`, `GoldWriteMode` enums

---

## Рекомендации для Будущих Аудитов

1. **ВСЕГДА проверять код перед утверждением**
   ```bash
   grep -rn "class X" src/bioetl/
   wc -l src/bioetl/path/to/file.py
   ```

2. **Проверять делегирование перед "god object"**
   ```bash
   grep -o "self\._[a-z_]*" file.py | sort -u | wc -l
   ```

3. **Сверять с ADRs**
   - ADR-010 supersedes ADR-003 (Redis → MemoryLock)
   - ADR-022 объясняет NoOp pattern

4. **Читать refactoring-plan.md секцию "ЛОЖНЫЕ УТВЕРЖДЕНИЯ"**
   - 130+ задокументированных ложных выводов

5. **Использовать триангуляцию**
   - Код (40%) + Документация (30%) + Тесты (30%)
   - Утверждение валидно только при ≥60% подтверждения

---

*Generated: 2025-12-31*
