# Ревью архитектурного аудита BioETL 2026-01-27

**Дата ревью:** 2026-01-27
**Ревьюер:** Claude Code (сессия claude/review-audit-fixes-iAfXF)

## Резюме

Аудит содержит **несколько критических ложных утверждений**, которые могут привести к ненужной работе. После верификации кодом выявлены следующие расхождения:

## Часть 1. Верификация утверждений аудита

### 1.1. ❌ ЛОЖНОЕ: "145 прямых импортов domain из infrastructure — нарушение"

**Утверждение аудита:**
> "В инфраструктуре есть прямые импорты из `bioetl.domain` **вне** `domain.ports` (145 совпадений). Оценка слоистой архитектуры: 3/10"

**Верификация:**

```bash
# Проверка .importlinter контрактов
cat .importlinter
```

**Результат:** `.importlinter:29-36` определяет:
```ini
[importlinter:contract:infrastructure-independence]
name = Infrastructure layer must not import from application or interfaces
source_modules = bioetl.infrastructure
forbidden_modules =
    bioetl.application
    bioetl.interfaces
```

**Вывод:** Infrastructure **МОЖЕТ** импортировать Domain! Это **ожидаемое поведение** в Hexagonal Architecture:
- Infrastructure реализует Domain ports
- Infrastructure использует Domain types, exceptions, value objects
- Запрет только на импорт application и interfaces из infrastructure

**Матрица импортов (CLAUDE.md §2.1):**
```
domain ← application ← composition → infrastructure
                                  ↓
                              interfaces
```

Стрелка `←` означает "может импортировать из". Infrastructure → Domain — разрешено.

**Корректная оценка категории 1:** 8/10 (не 3/10)

---

### 1.2. ❌ ЛОЖНОЕ: "1 ошибка mypy в memory_monitor.py:141"

**Утверждение аудита:**
> "mypy errors: 1. Файл: src/bioetl/infrastructure/system/memory_monitor.py:141 - Unused type: ignore"

**Верификация:**

```bash
mypy src/bioetl --strict 2>&1 | grep -c "error:"
# Результат: 143

mypy src/bioetl --strict 2>&1 | grep "unused-ignore"
# src/bioetl/domain/serialization.py:38: error: Unused "type: ignore" comment  [unused-ignore]
```

**Реальность:**
1. **143 ошибки** mypy, не 1
2. `unused-ignore` в `serialization.py:38`, не в `memory_monitor.py:141`
3. 142 ошибки типа `Class cannot subclass "DataFrameModel"` — проблема типизации pandera

---

### 1.3. ❌ ЛОЖНОЕ: "domain/config.py и domain/result.py превышают лимиты LOC"

**Утверждение аудита:**
> "Архитектурные тесты падают из-за превышения лимитов LOC в domain/config.py и domain/result.py"

**Верификация:**

```bash
wc -l src/bioetl/domain/config.py
# 636 строк

ls src/bioetl/domain/result.py
# File not found — файл НЕ существует

wc -l src/bioetl/domain/composite/result.py
# 459 строк
```

**Проверка exemptions в test_code_metrics.py:**
```python
EXEMPTIONS = {
    "config.py": 640,  # exemption на 640 LOC
    "result.py": 335,  # exemption на 335 LOC (для composite/result.py)
}
```

**Реальность:**
- `domain/config.py` = 636 LOC < 640 (exemption) → **НЕ нарушение**
- `domain/result.py` не существует → **ложное утверждение**
- `domain/composite/result.py` = 459 LOC > 335 (exemption) → **Реальное нарушение!**

---

### 1.4. ⚠️ НЕТОЧНОЕ: "CompositePipelineState содержит дополнительные состояния"

Требуется дополнительная верификация через запуск тестов.

---

## Часть 2. Корректированная таблица метрик

| # | Категория | Оценка аудита | Корр. оценка | Комментарий |
|---|-----------|---------------|--------------|-------------|
| 1 | Слоистая архитектура | 3 | **8** | Domain→Infrastructure — разрешено |
| 2 | Контракты и Ports | 8 | 8 | Корректно |
| 3 | Medallion Architecture | 8 | 8 | Корректно |
| 4 | Ошибки и Circuit Breaker | 9 | 9 | Корректно |
| 5 | Блокировки | 9 | 9 | Корректно |
| 6 | Валидация и DQ | 7 | 7 | Корректно |
| 7 | Логирование/наблюдаемость | 8 | 8 | Корректно |
| 8 | Тестирование | 7 | **6** | 143 mypy ошибки, не 1 |
| 9 | Безопасность | 8 | 8 | Корректно |
| 10 | Документация | 7 | 7 | Корректно |

**Корректированный общий балл:** ~7.73 (не 7.28)

---

## Часть 3. Улучшенный план исправлений

### [P0-CRITICAL] Исправить 143 ошибки mypy --strict
**Приоритет:** Критический (блокирует CI)
**Трудозатраты:** M (дни)

**Проблема:** 143 ошибки mypy:
- 142 ошибки `Class cannot subclass "DataFrameModel"` в Gold-схемах pandera
- 1 ошибка `Unused "type: ignore"` в `serialization.py:38`

**Root cause:** Pandera DataFrameModel не имеет py.typed или stub-файлов для mypy.

**Решения (в порядке приоритета):**

1. **Добавить type: ignore для pandera schemas:**
   ```python
   # src/bioetl/domain/contracts/gold/chembl.py
   class ChemblActivityGold(DataFrameModel):  # type: ignore[misc]
       ...
   ```

2. **Или создать stub-файл для pandera:**
   ```
   stubs/pandera/__init__.pyi
   ```

3. **Удалить unused type: ignore:**
   ```python
   # src/bioetl/domain/serialization.py:38
   # Было:
   orjson = None  # type: ignore[assignment]
   # Стало:
   orjson = None
   ```

**Файлы:**
- `src/bioetl/domain/contracts/gold/*.py` (все Gold-схемы)
- `src/bioetl/domain/serialization.py:38`

**Критерий готовности:**
```bash
mypy src/bioetl --strict 2>&1 | grep -c "error:"
# Результат: 0
```

---

### [P1] Уменьшить размер domain/composite/result.py
**Приоритет:** Высокий
**Трудозатраты:** S (часы)

**Проблема:** `domain/composite/result.py` = 459 LOC > 335 (exemption)

**Решения:**

1. **Увеличить exemption** (если код когезивен):
   ```python
   # tests/architecture/test_code_metrics.py
   EXEMPTIONS = {
       "result.py": 460,  # Updated: CompositeResult with EnrichmentResult, MergeResult, SeedResult, DependencyResult
   }
   ```

2. **Или разбить на модули** (если логически возможно):
   - `seed_result.py`
   - `enrichment_result.py`
   - `merge_result.py`

**Файлы:**
- `src/bioetl/domain/composite/result.py`
- `tests/architecture/test_code_metrics.py`

**Критерий готовности:** Тест `test_domain_files_under_limit` проходит.

---

### [P2] Верифицировать CompositePipelineState FSM
**Приоритет:** Средний
**Трудозатраты:** S (часы)

**Проблема:** Аудит утверждает несоответствие набора состояний и metric values.

**Действие:** Запустить тесты после установки зависимостей:
```bash
pip install -e ".[dev]"
pytest tests/unit/domain/composite/test_state.py -v
```

**Критерий готовности:** Тест проходит или документировано причина.

---

### [P3-УДАЛИТЬ] ~~Устранить нарушения слоёв~~
**Статус:** ОТМЕНЕНО — ложное утверждение аудита

Infrastructure импортирует Domain — это **корректное поведение**, не нарушение.

---

## Часть 4. Обновлённые метрики контроля регресса (CI)

| Метрика | Порог | Команда | Блокирует PR |
|---------|-------|---------|--------------|
| Coverage | ≥85% | `pytest --cov-fail-under=85` | Да |
| mypy errors | 0 | `mypy src/bioetl --strict` | **Да** (исправить!) |
| Циклические импорты | 0 | `python -c "import bioetl.domain"` | Да |
| import-linter | 0 | `lint-imports --config .importlinter` | Да |
| print() в коде | 0 | `rg "print\(" src/bioetl -g "*.py"` | Да |

**УБРАТЬ из CI (ложная метрика):**
- ~~`rg "from bioetl\.domain(?!\.ports)" src/bioetl/infrastructure`~~ — не нарушение

---

## Часть 5. Итоговый roadmap

| Фаза | Задачи | Ожидаемый балл | Срок |
|------|--------|----------------|------|
| 1 | P0: mypy errors | 8.5 | 1-2 дня |
| 2 | P1: result.py LOC | 8.7 | 1 день |
| 3 | P2: FSM verification | 8.8 | 1 день |

---

## Verification Log

```bash
# Импорты domain из infrastructure
grep -r "from bioetl\.domain\." src/bioetl/infrastructure --include="*.py" | grep -v "from bioetl\.domain\.ports" | wc -l
# Результат: 145 (НЕ нарушение)

# .importlinter контракты
cat .importlinter | grep -A5 "infrastructure-independence"
# forbidden_modules: bioetl.application, bioetl.interfaces
# (НЕ включает bioetl.domain)

# mypy ошибки
mypy src/bioetl --strict 2>&1 | grep -c "error:"
# Результат: 143

# LOC файлов
wc -l src/bioetl/domain/config.py
# 636 (< 640 exemption)

wc -l src/bioetl/domain/composite/result.py
# 459 (> 335 exemption) — РЕАЛЬНОЕ НАРУШЕНИЕ
```

---

*Ревью выполнено согласно CLAUDE.md §0 "Протокол Обязательной Двойной Верификации"*
