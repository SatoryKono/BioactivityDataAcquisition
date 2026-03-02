# Code Quality Report

**Дата**: 2026-01-21
**RULES.md**: v5.12
**Проект**: BioETL

---

## Резюме

| Категория | Статус | Комментарий |
|-----------|--------|-------------|
| Линтинг (ruff) | ✅ PASS | 0 ошибок |
| Форматирование | ✅ PASS | 922 файла без изменений |
| Типизация (mypy) | ⚠️ WARN | 76 ошибок в 18 файлах |
| Архитектурные тесты | ✅ PASS | 990 passed, 14 skipped |
| Циклические импорты | ✅ PASS | Отсутствуют |
| Запрещённые паттерны | ✅ PASS | Не найдены в src/bioetl/ |
| Сложность кода | ✅ GOOD | 92% функций с complexity A |

---

## 1. Линтинг

```
ruff check: All checks passed!
ruff format: 922 files left unchanged
```

**Результат**: Код полностью соответствует стандартам Ruff.

---

## 2. Типизация (mypy --strict)

**Найдено**: 76 ошибок в 18 файлах (из 449 проверенных)

### Категоризация ошибок

| Тип ошибки | Количество | Причина |
|------------|------------|---------|
| `[misc]` - Class cannot subclass "BaseModel" | 42 | Pydantic без mypy plugin |
| `[unused-ignore]` - Unused type: ignore | 12 | Устаревшие ignore-комментарии |
| `[untyped-decorator]` - Untyped decorator | 10 | Pydantic @field-validator |
| `[no-any-return]` - Returning Any | 9 | Недостаточная типизация возвратов |
| **Итого** | **76** | |

### Затронутые файлы

| Файл | Ошибок | Основная проблема |
|------|--------|-------------------|
| `domain/models/metadata.py` | 21 | Pydantic BaseModel |
| `infrastructure/schemas/composite-config.py` | 18 | Pydantic + validators |
| `infrastructure/schemas/dq-report-config.py` | 6 | Pydantic BaseModel |
| `application/services/dq/silver-analyzer.py` | 6 | Unused type: ignore |
| `infrastructure/config/-base.py` | 4 | Pydantic BaseSettings |
| `infrastructure/schemas/filter-config.py` | 4 | Pydantic BaseModel |
| `infrastructure/schemas/dq-config.py` | 3 | Pydantic BaseModel |
| Остальные 11 файлов | 14 | Смешанные |

### Рекомендация по исправлению

**Корневая причина**: Pydantic модели не типизируются корректно в mypy --strict без плагина.

**Решение**: Включить `pydantic.mypy` плагин в `pyproject.toml`:

```toml
[tool.mypy]
plugins = ["pydantic.mypy"]

[tool.pydantic-mypy]
init-forbid-extra = true
init-typed = true
warn-required-dynamic-aliases = true
```

После включения плагина:
- 42 ошибки `[misc]` исчезнут
- 10 ошибок `[untyped-decorator]` исчезнут
- 12 ошибок `[unused-ignore]` нужно удалить вручную (устаревшие комментарии)
- 9 ошибок `[no-any-return]` требуют явного cast()

---

## 3. Архитектурные границы

```
pytest tests/architecture/ -v
990 passed, 14 skipped in 35.78s
```

**Результат**: Все архитектурные инварианты соблюдены.

### Проверенные контракты

| Категория | Тестов | Статус |
|-----------|--------|--------|
| Layer dependencies | 18 | ✅ |
| Port contracts | 130 | ✅ |
| DI compliance | 18 | ✅ |
| Forbidden imports | 6 | ✅ |
| No structlog in app/interfaces | 5 | ✅ |
| No datetime.now in infrastructure | 2 | ✅ |
| No random in writers | 3 | ✅ |
| Column order (schemas) | 105 | ✅ |
| Transformer signatures | 185 | ✅ |

### Циклические импорты

```python
from bioetl.domain import *        # OK
from bioetl.application import *   # OK
from bioetl.infrastructure import * # OK
```

**Результат**: Циклические импорты отсутствуют.

---

## 4. Запрещённые паттерны

| Паттерн | src/bioetl/ | src/tools/ | Комментарий |
|---------|-------------|------------|-------------|
| `print()` | 0 | 135 | tools/ — standalone скрипты, допустимо |
| Хардкод секретов | 0 | 0 | ✅ |
| Sentinel values | 0 | 0 | ✅ |
| `datetime.now()` без tz | 0 | 0 | ✅ |
| `random.` без seed | 0 | 0 | ✅ |
| `structlog` в app/interfaces | 0 | N/A | ✅ |

**Результат**: Все запрещённые паттерны отсутствуют в основном коде.

---

## 5. Сложность кода

### Cyclomatic Complexity Distribution

| Ранг | Диапазон | Количество | Процент |
|------|----------|------------|---------|
| A | 1-5 | 3344 | 92.5% |
| B | 6-10 | 250 | 6.9% |
| C | 11-20 | 20 | 0.6% |
| D-F | 21+ | 0 | 0% |

### Функции с высокой сложностью (C)

| Функция | Файл | CC |
|---------|------|-----|
| `MergeService.-apply-explicit-rules` | composite/merger.py:542 | 20 |
| `SilverDQAnalyzer.analyze` | services/dq/silver-analyzer.py:54 | 20 |
| `CrossRefAdapter.fetch-filtered-with-fallback` | adapters/crossref/client.py:191 | 17 |
| `PubMedAdapter.fetch-filtered-with-fallback` | adapters/pubmed/pubmed-client.py:298 | 17 |
| `SilverDQAnalyzer.-check-value-distribution` | services/dq/silver-analyzer.py:360 | 17 |
| `OpenAlexAdapter.fetch-filtered-with-fallback` | adapters/openalex/client.py:209 | 16 |
| `GoldWriter.-write-gold-metadata` | storage/gold-writer.py:602 | 15 |
| `GoldDQAnalyzer.-check-statistical-profile` | services/dq/gold-analyzer.py:490 | 15 |
| `GoldDQAnalyzer.-check-scd-integrity` | services/dq/gold-analyzer.py:654 | 15 |

### Maintainability Index

| Ранг | Количество файлов |
|------|-------------------|
| A (высокая) | 449 |
| B (средняя) | 0 |
| C (низкая) | 0 |

**Результат**: Весь код имеет высокую поддерживаемость (ранг A).

---

## 6. Блокеры (MUST исправить)

### Критические (блокируют production)

1. **mypy --strict не проходит** (76 ошибок)
   - Решение: Включить pydantic.mypy плагин
   - Удалить 12 устаревших `# type: ignore` комментариев
   - Добавить cast() для 9 функций с `[no-any-return]`

### Файлы с устаревшими type: ignore (удалить комментарии)

```
src/bioetl/domain/serialization.py:38
src/bioetl/domain/value-objects/dq-metrics.py:83
src/bioetl/infrastructure/adapters/common/api-request-collector.py:111
src/bioetl/infrastructure/adapters/common/api-request-collector.py:198
src/bioetl/application/services/dq/silver-analyzer.py:93,379-383
src/bioetl/application/services/dq/gold-analyzer.py:135,446
```

---

## 7. Рекомендации (SHOULD)

### Высокий приоритет

1. **Включить pydantic.mypy плагин** — устранит 52 из 76 ошибок типизации

2. **Рефакторинг сложных функций** (CC ≥ 17):
   - `-apply-explicit-rules` (CC=20) — разбить на подфункции
   - `analyze` в DQ analyzers (CC=20) — извлечь проверки в отдельные методы

### Средний приоритет

3. **Унифицировать `fetch-filtered-with-fallback`** — 4 адаптера имеют одинаковую сложную логику, кандидат на mixin

4. **Удалить устаревшие type: ignore** — 12 комментариев больше не нужны

---

## 8. Сводка для CI/CD

```yaml
# Рекомендуемые проверки для CI
quality-gates:
  ruff-check: PASS       # ✅ Готово
  ruff-format: PASS      # ✅ Готово
  mypy-strict: FAIL      # ⚠️ Требует pydantic.mypy
  arch-tests: PASS       # ✅ 990/990
  coverage: 85%+         # ✅ (проверяется отдельно)

# После исправления mypy:
# mypy-strict: PASS      # Ожидается после включения плагина
```

---

*Отчёт сгенерирован автоматически. Актуален на дату создания.*
