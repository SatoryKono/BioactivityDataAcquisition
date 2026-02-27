# Инвентаризация Объектов и Обнаружение Дублирования / Мёртвого Кода

*Version 1.0 | Aligned with RULES.md v5.22 (2026-02-03)*

## Цель

Провести полную инвентаризацию всех объектов (классов, функций, констант, type aliases)
в каждом архитектурном слое проекта BioETL с целью:

1. **Обнаружение дублирующейся логики** — семантически идентичные или перекрывающиеся реализации
2. **Обнаружение мёртвого кода** — объекты без вызовов, неиспользуемые импорты, orphan-модули
3. **Формирование карты зависимостей** — кто кого использует, выявление циклов и изолятов

**Субагент:** `py-audit-bot` (mode: `AUDIT`, phase: `targeted`, audit_type: `inventory`)

---

## Методология

### Принцип работы

Инвентаризация проводится **послойно** в порядке архитектурных зависимостей:

```
1. domain/        ← фундамент, ни от кого не зависит
2. application/   ← зависит от domain
3. infrastructure/ ← зависит от domain
4. composition/   ← зависит от domain + application + infrastructure
5. interfaces/    ← зависит от всех
```

Для каждого слоя выполняются 3 фазы:
- **Фаза A**: Сбор реестра объектов
- **Фаза B**: Анализ использования (reference count)
- **Фаза C**: Анализ дублирования (семантическое сравнение)

### Scope границы

- **В scope:** `src/bioetl/` — весь production-код
- **Вне scope:** `tests/`, `scripts/`, `docs/`, `configs/`
- **Cross-reference:** тесты проверяются только для определения "используется ли объект"

---

## Фаза A: Реестр Объектов (на каждый слой)

### A1. Извлечение всех классов

```bash
# Формат: файл:строка:имя_класса
grep -rn "^class [A-Z]" src/bioetl/{layer}/ --include="*.py" | \
  sed 's/class \([A-Za-z_]*\).*/\1/' | sort
```

Для каждого класса фиксировать:

| Поле | Описание |
|------|----------|
| `module` | Полный Python-путь модуля |
| `class_name` | Имя класса |
| `file` | Путь к файлу |
| `line` | Номер строки |
| `base_classes` | Родительские классы |
| `suffix` | Тип по NAME-001 (Factory/Client/Port/Service/Transformer/Error/Schema/Config) |
| `loc` | Количество строк в классе |
| `public_methods` | Список публичных методов (без `_` prefix) |
| `private_methods` | Список приватных методов (`_` prefix) |

### A2. Извлечение всех функций уровня модуля

```bash
# Функции не в классах
grep -rn "^def \|^async def " src/bioetl/{layer}/ --include="*.py" | sort
```

Для каждой функции:

| Поле | Описание |
|------|----------|
| `module` | Полный Python-путь |
| `function_name` | Имя функции |
| `signature` | Полная сигнатура (аргументы + return type) |
| `loc` | Количество строк |
| `is_public` | Начинается ли без `_` |

### A3. Извлечение констант и type aliases

```bash
# Константы (UPPER_SNAKE_CASE на уровне модуля)
grep -rn "^[A-Z][A-Z_]*\s*=" src/bioetl/{layer}/ --include="*.py"

# Type aliases
grep -rn "^[A-Z][a-zA-Z]*\s*=.*\(TypeAlias\|TypeVar\|ParamSpec\|Annotated\|Union\|dict\[" \
  src/bioetl/{layer}/ --include="*.py"
```

### A4. Извлечение `__all__` экспортов

```bash
grep -rn "__all__" src/bioetl/{layer}/ --include="*.py" -A 20
```

Сравнить `__all__` с фактическими определениями в модуле. Зафиксировать:
- Объекты в `__all__`, но не определённые в модуле (битые re-exports)
- Объекты определённые, но не в `__all__` (потенциально приватные)

---

## Фаза B: Анализ Использования (Reference Count)

### B1. Для каждого объекта из Фазы A подсчитать ссылки

```bash
# Поиск использования класса/функции во ВСЁМ проекте
grep -rn "ClassName\|function_name" src/bioetl/ tests/ --include="*.py" | \
  grep -v "^.*:.*class ClassName\|^.*:.*def function_name" | wc -l
```

### B2. Классификация по использованию

| Категория | Критерий | Действие |
|-----------|----------|----------|
| **ACTIVE** | ≥1 ссылка в production + ≥1 в тестах | Штатный объект |
| **PRODUCTION_ONLY** | ≥1 ссылка в production, 0 в тестах | Кандидат на добавление тестов |
| **TEST_ONLY** | 0 в production, ≥1 в тестах | Подозрение на мёртвый код |
| **DEAD** | 0 ссылок (кроме определения и `__all__`) | Мёртвый код |
| **SELF_ONLY** | Используется только внутри своего модуля | Кандидат на инлайнинг |
| **RE_EXPORT_ONLY** | Только в `__init__.py` / re-export | Проверить необходимость фасада |

### B3. Анализ импортов

```bash
# Неиспользуемые импорты в каждом файле
# (Объекты импортируются, но не используются в теле модуля)
python -m pyflakes src/bioetl/{layer}/
```

Альтернативно (если pyflakes недоступен):

```bash
# Для каждого файла: извлечь imported names, проверить usage
for f in $(find src/bioetl/{layer}/ -name "*.py"); do
  echo "=== $f ==="
  # Извлекаем импортированные имена
  grep "^from .* import \|^import " "$f" | \
    sed 's/.*import //; s/ as [a-zA-Z_]*//' | tr ',' '\n' | \
    xargs -I{} sh -c 'count=$(grep -c "{}" "$0" 2>/dev/null); echo "{}: $count refs"' "$f"
done
```

### B4. Orphan-модули

```bash
# Файлы, на которые нет ни одного import
for f in $(find src/bioetl/{layer}/ -name "*.py" ! -name "__init__.py"); do
  module=$(echo "$f" | sed 's|src/||; s|/|.|g; s|\.py$||')
  count=$(grep -rn "from $module\|import $module" src/bioetl/ --include="*.py" | wc -l)
  if [ "$count" -eq 0 ]; then
    echo "ORPHAN: $f (0 imports)"
  fi
done
```

---

## Фаза C: Анализ Дублирования

### C1. Структурное дублирование (одинаковые сигнатуры)

Найти методы/функции с **идентичными именами и похожими сигнатурами** в разных классах:

```bash
# Извлечь все method signatures
grep -rn "def [a-z_].*(" src/bioetl/{layer}/ --include="*.py" | \
  sed 's/.*def \([a-z_]*\)(\(.*\)).*:/\1|\2/' | sort | uniq -d
```

Для каждого дубля проверить:
- Это **реализация Protocol** (допустимо — не дубликат)?
- Это **override в наследнике** (допустимо)?
- Это **copy-paste** (нарушение DRY)?

### C2. Семантическое дублирование (одинаковая логика)

Анализировать попарно классы с похожими суффиксами по NAME-001:

| Группа для сравнения | Что искать |
|---------------------|------------|
| `*Transformer` в одном провайдере | Идентичные `_transform_*` методы |
| `*Transformer` между провайдерами | Copy-paste общей логики (normalization, validation) |
| `*Client` между провайдерами | Дублирование HTTP logic, pagination, error handling |
| `*Schema` в `domain/schemas/` | Одинаковые поля / validators между провайдерами |
| `*Factory` в `composition/` | Идентичные конструкции объектов |
| `*Service` в `application/` | Перекрывающаяся бизнес-логика |
| `*Port` в `domain/ports/` | Порты с идентичными method signatures |

### C3. Дублирование между слоями

Особое внимание:

| Паттерн | Где искать | Риск |
|---------|-----------|------|
| Валидация в domain И в infrastructure | `domain/schemas/` vs `infrastructure/validation/` | Двойная валидация |
| Config-объекты в domain И в infrastructure | `domain/configs/` vs `infrastructure/config/` | Рассинхронизация |
| Утилиты в разных слоях | `*/utils.py`, `*/helpers.py` | Нарушение DRY |
| Mapper/Converter logic | `application/pipelines/` vs `infrastructure/adapters/` | Размытие границ |
| Exception hierarchies | `domain/exceptions/` vs local exceptions в модулях | Фрагментация |
| Type definitions | `domain/types.py` vs локальные type aliases | Расхождение |

### C4. Near-duplicate Detection (AST-based)

Если доступны утилиты:

```bash
# Pylint duplicate detection
pylint --disable=all --enable=duplicate-code src/bioetl/ 2>&1 | grep "Similar lines"

# Или через jscpd (если установлен)
jscpd src/bioetl/ --format python --threshold 5
```

Альтернативно — ручной анализ:

```bash
# Файлы с подозрительно похожим размером в одном пакете
find src/bioetl/{layer}/ -name "*.py" -exec wc -l {} \; | sort -n | \
  awk '{size=$1; name=$2; if (prev_size == size) print "SUSPECT: " prev " vs " name " (" size " lines)"; prev_size=size; prev=name}'
```

---

## Специфические Проверки по Слоям

### Domain Layer

| Проверка | Команда | Что ищем |
|----------|---------|----------|
| Дубли Ports | Сравнить signatures всех `*Port` протоколов | Порты с одинаковыми методами |
| Дубли Schemas | Сравнить поля `*BronzeSchema`, `*SilverSchema`, `*GoldSchema` одного entity | Идентичные field definitions |
| Дубли между common/ и provider-specific schemas | Поля из `common/` дублирующиеся в `chembl/`, `pubmed/` etc. | Copy-paste вместо inheritance |
| Дубли Value Objects | Сравнить `value_objects/` — нет ли перекрытий | Два VO с одинаковой семантикой |
| Мёртвые entities | Entity без ссылок из application/infrastructure | Определены, но не используются |
| Мёртвые exceptions | Exception без raise/except | Определены, но не выбрасываются |

```bash
# Мёртвые exceptions
for exc in $(grep -rn "class.*Error\|class.*Exception" src/bioetl/domain/exceptions/ --include="*.py" | \
  sed 's/.*class \([A-Za-z]*\).*/\1/'); do
  count=$(grep -rn "$exc" src/bioetl/ tests/ --include="*.py" | grep -v "class $exc" | wc -l)
  echo "$exc: $count references"
done
```

### Application Layer

| Проверка | Что ищем |
|----------|----------|
| Дубли между Transformer'ами одного провайдера | Идентичные _transform_record, _normalize методы |
| Дубли между Transformer'ами разных провайдеров | Copy-paste publication normalization, date parsing etc. |
| Неиспользуемые pipeline-функции | Функции `create_*_pipeline` без вызовов |
| Дубли в composite/ vs core/ | Перекрывающаяся orchestration logic |
| Мёртвые Service-классы | Service без инъекции/вызова |

```bash
# Сравнить методы transformer'ов одного провайдера (пример: chembl)
for f in src/bioetl/application/pipelines/chembl/*_transformer.py; do
  echo "=== $(basename $f) ==="
  grep "def " "$f" | sed 's/.*def //' | cut -d'(' -f1
done

# Общие методы между transformer'ами разных провайдеров
for dir in src/bioetl/application/pipelines/*/; do
  provider=$(basename "$dir")
  for f in "$dir"*_transformer.py; do
    [ -f "$f" ] && grep "def " "$f" | sed "s/.*def /$provider:/"
  done
done | sort -t: -k2 | awk -F: '{if(prev==$2) print "DUP: "$0" vs "prev_line; prev=$2; prev_line=$0}'
```

### Infrastructure Layer

| Проверка | Что ищем |
|----------|----------|
| Дубли HTTP logic между adapter clients | Идентичные retry, pagination, error handling |
| Дубли моделей (Pydantic) между adapters | Одинаковые response models |
| Мёртвые adapters | Adapter без регистрации в composition |
| Дубли storage logic | Перекрывающаяся логика в bronze/silver/gold writers |
| Мёртвые observability components | Метрики, tracers без подключения |

```bash
# Проверить регистрацию адаптеров
for client in $(grep -rn "class.*Client" src/bioetl/infrastructure/adapters/ --include="*.py" | \
  sed 's/.*class \([A-Za-z]*\).*/\1/'); do
  count=$(grep -rn "$client" src/bioetl/composition/ --include="*.py" | wc -l)
  echo "$client: $count refs in composition/"
done
```

### Composition Layer

| Проверка | Что ищем |
|----------|----------|
| Дубли Factory-методов | Идентичная сборка объектов в разных factory |
| Мёртвые factory-функции | Factory-метод не вызывается из interfaces/bootstrap |
| Дублирование bootstrap logic | Повторяющийся wiring в разных assembly-модулях |

### Interfaces Layer

| Проверка | Что ищем |
|----------|----------|
| Дубли CLI-обработчиков | Повторяющийся boilerplate в Click-командах |
| Мёртвые команды | CLI-команда не зарегистрированная в группе |
| Дубли форматирования | Повторяющийся output formatting |

---

## Формат Выходного Отчёта

### Структура файла: `reports/inventory/<task_id>/inventory-report.md`

```markdown
# Code Inventory Report — BioETL
Date: YYYY-MM-DD
Scope: src/bioetl/ (all layers)

## Executive Summary

| Метрика | Значение |
|---------|----------|
| Всего классов | ___ |
| Всего функций (module-level) | ___ |
| Всего констант | ___ |
| Мёртвых объектов (DEAD) | ___ |
| Дублей (confirmed) | ___ |
| Дублей (suspected) | ___ |

## 1. Реестр Объектов

### 1.1 Domain Layer
(таблица A1-A4)

### 1.2 Application Layer
(таблица A1-A4)

### 1.3 Infrastructure Layer
(таблица A1-A4)

### 1.4 Composition Layer
(таблица A1-A4)

### 1.5 Interfaces Layer
(таблица A1-A4)

## 2. Dead Code

### 2.1 DEAD объекты (0 ссылок)
| # | Object | Type | Layer | File:Line | Last Modified |
|---|--------|------|-------|-----------|---------------|

### 2.2 TEST_ONLY объекты (ссылки только в тестах)
| # | Object | Type | Layer | File:Line | Test File |
|---|--------|------|-------|-----------|-----------|

### 2.3 SELF_ONLY объекты (используются только в своём модуле)
| # | Object | Type | Layer | File:Line | Recommendation |
|---|--------|------|-------|-----------|----------------|

### 2.4 Orphan-модули (файлы без imports)
| # | File | LOC | Objects Defined | Recommendation |
|---|------|-----|----------------|----------------|

### 2.5 Неиспользуемые импорты
| # | File:Line | Import | Recommendation |
|---|-----------|--------|----------------|

## 3. Duplicate Logic

### 3.1 Confirmed Duplicates (идентичная логика)
| # | Object A | Object B | Similarity | Type | Recommendation |
|---|----------|----------|-----------|------|----------------|

### 3.2 Suspected Duplicates (похожая логика, требует ручной верификации)
| # | Object A | Object B | Similarity Basis | Risk |
|---|----------|----------|-----------------|------|

### 3.3 Cross-layer Duplicates
| # | Domain Object | Other Layer Object | Nature | Recommendation |
|---|---------------|-------------------|--------|----------------|

### 3.4 Cross-provider Duplicates (Transformer/Client/Schema)
| # | Provider A | Provider B | Shared Logic | LOC Savings |
|---|-----------|-----------|-------------|-------------|

## 4. Dependency Map

### 4.1 Объекты с наибольшим fan-out (зависят от многих)
| # | Object | Layer | Dependencies Count | Risk |
|---|--------|-------|--------------------|------|

### 4.2 Объекты с наибольшим fan-in (от них зависят многие)
| # | Object | Layer | Dependents Count | Criticality |
|---|--------|-------|-----------------|-------------|

### 4.3 Циклические зависимости внутри слоя
| # | Cycle | Layer | Files Involved |
|---|-------|-------|---------------|

## 5. Рекомендации

### 5.1 Немедленные действия (Quick Wins)
| # | Action | Objects | Impact | Effort |
|---|--------|---------|--------|--------|

### 5.2 Рефакторинги (требуют планирования)
| # | RF-ID | Description | Objects | Impact | Risk |
|---|-------|-------------|---------|--------|------|

### 5.3 По слоям — сводка

| Layer | Dead Objects | Duplicates | Health |
|-------|-------------|------------|--------|
| domain | ___ | ___ | ✅/⚠️/❌ |
| application | ___ | ___ | ✅/⚠️/❌ |
| infrastructure | ___ | ___ | ✅/⚠️/❌ |
| composition | ___ | ___ | ✅/⚠️/❌ |
| interfaces | ___ | ___ | ✅/⚠️/❌ |
```

---

## Правила Классификации

### Что НЕ считать мёртвым кодом

> **КРИТИЧЕСКИ ВАЖНО:** Проверить перед пометкой как DEAD.

| Паттерн | Причина |
|---------|---------|
| `Protocol` / `*Port` без прямых вызовов | Контракт — реализуется в infrastructure |
| `__all__` re-exports | Фасадный паттерн |
| `TYPE_CHECKING` imports | Type hints only |
| Pydantic/Pandera Schema validators (`@validator`, `@check`) | Вызываются фреймворком |
| Click decorators (`@click.command`, `@click.option`) | Вызываются CLI framework |
| `__init__.py` с re-exports | Package facade |
| Abstract methods в базовых классах | Реализуются в наследниках |
| Enum members | Могут использоваться через `.value` comparison |
| `@property` / `@cached_property` | Attribute access, не function call |
| NoOp implementations (Null Object) | Intentional — EXC-003 |
| Graceful degradation fallbacks | Intentional — EXC-006 |
| Backward-compatibility re-exports | Intentional — EXC-004 |

### Что НЕ считать дублированием

| Паттерн | Причина |
|---------|---------|
| Реализации одного Protocol разными адаптерами | По дизайну — каждый адаптер своя реализация |
| Template Method overrides в наследниках | По дизайну — hook points |
| Bronze/Silver/Gold variants одного entity | Разные medallion layers, разная семантика |
| `__init__` с DI-параметрами в разных классах | Boilerplate DI, не дублирование логики |
| Одинаковые field names в разных Pydantic/Pandera моделях | Может быть justified (разные constraints) |
| Одинаковые error handling в разных adapters | Каждый adapter обрабатывает свои специфичные ошибки |

### Что СЧИТАТЬ дублированием

| Паттерн | Severity |
|---------|----------|
| Copy-paste `_normalize_*` между Transformer'ами | HIGH |
| Идентичная pagination logic в разных Client'ах | HIGH |
| Одинаковый date/string parsing в нескольких модулях | MEDIUM |
| Дублирование validation rules (domain + infrastructure) | HIGH |
| Идентичные helper-функции в разных модулях | MEDIUM |
| Copy-paste error mapping между adapters | MEDIUM |
| Дублирующиеся Config dataclass'ы | HIGH |

---

## Приоритизация Результатов

### Scoring

| Категория | Вес | Описание |
|-----------|-----|----------|
| Dead Code | 30% | Объём мёртвого кода в LOC |
| Cross-provider Duplicates | 25% | Дублирование между провайдерами |
| Cross-layer Duplicates | 20% | Дублирование между слоями |
| Intra-layer Duplicates | 15% | Дублирование внутри одного слоя |
| Orphan Modules | 10% | Модули без входящих зависимостей |

### Severity дублей

| LOC дубля | Severity |
|-----------|----------|
| ≥50 LOC | CRITICAL — обязательный рефакторинг |
| 20-49 LOC | HIGH — рекомендуется рефакторинг |
| 10-19 LOC | MEDIUM — по усмотрению |
| <10 LOC | LOW — возможно приемлемо |

---

## Команды Быстрого Старта

```bash
# 1. Общие метрики
echo "=== General Metrics ==="
find src/bioetl/ -name "*.py" | wc -l
grep -rn "^class " src/bioetl/ --include="*.py" | wc -l
grep -rn "^def \|^async def " src/bioetl/ --include="*.py" | wc -l

# 2. Метрики по слоям
for layer in domain application infrastructure composition interfaces; do
  echo "=== $layer ==="
  echo "  Files: $(find src/bioetl/$layer/ -name '*.py' | wc -l)"
  echo "  Classes: $(grep -rn '^class ' src/bioetl/$layer/ --include='*.py' | wc -l)"
  echo "  Functions: $(grep -rn '^def \|^async def ' src/bioetl/$layer/ --include='*.py' | wc -l)"
  echo "  LOC: $(find src/bioetl/$layer/ -name '*.py' -exec cat {} + | wc -l)"
done

# 3. Быстрая проверка дублей (pylint)
pylint --disable=all --enable=duplicate-code src/bioetl/ 2>&1 | head -50

# 4. Неиспользуемые импорты
python -m pyflakes src/bioetl/ 2>&1 | grep "imported but unused" | head -30

# 5. Vulture (dead code detector)
vulture src/bioetl/ --min-confidence 80 2>&1 | head -50
```

---

## Интеграция с Workflow

### Входные данные от других субагентов

| Источник | Что используем |
|----------|---------------|
| `py-audit-bot` (baseline) | Findings по naming, imports — дополняют картину |
| `py-test-bot` (baseline) | Coverage report — подсвечивает непокрытый код |

### Выходные данные для других субагентов

| Потребитель | Что передаём |
|-------------|-------------|
| `py-plan-bot` | Список RF-* рефакторингов на основе дублей |
| `py-code-bot` | Конкретные файлы и объекты для удаления/объединения |
| `py-doc-bot` | Обновление документации после удаления мёртвого кода |
| `py-test-bot` | Объекты PRODUCTION_ONLY для написания тестов |

---

## Checklist Завершённости

- [ ] Реестр объектов собран для всех 5 слоёв
- [ ] Reference count подсчитан для каждого объекта
- [ ] Dead code помечен и проверен против исключений
- [ ] Дублирование между провайдерами проанализировано
- [ ] Дублирование между слоями проанализировано
- [ ] Orphan-модули идентифицированы
- [ ] Рекомендации приоритизированы
- [ ] Отчёт сформирован в заданном формате

---

## References

- **RULES.md** — `docs/00-project/RULES.md`
- **Self-review rules** — `.claude/rules/ai-selfreview-rules.md`
- **Architecture docs** — `docs/02-architecture/`
- **ADR decisions** — `docs/02-architecture/decisions/`
- **Naming Policy** — `docs/00-project/governance/02-naming-policy.md`
- **File Policy** — `docs/00-project/governance/03-file-policy.md`
