# Консолидированный план рефакторинга: унификация полей ChEMBL-пайплайнов

*Версия: 3.0.0 | Дата: 2026-02-15*
*Источники: ветки gFEGo (анализ), sRnnM (промты + код), 7Zhjk (filtering config), GBJxb (config plan)*
*Синхронизировано с main на 2026-02-15 (commit 0524ef4)*

---

## Статус: ✅ ПЛАН ЗАВЕРШЁН

Все задачи рефакторинга из оригинального плана (v1.0) и обновлений (v2.0) **выполнены**
и смержены в main. Этот документ фиксирует финальное состояние.

---

## 1. Итоги

Три независимых аудита (gFEGo, sRnnM, 7Zhjk) выявили 12 проблем в ChEMBL-пайплайнах.
Все проблемы исправлены через 7 PRs.

### 1.1 Полный статус исправлений

| # | Проблема | Статус | PR / Коммит |
|---|----------|--------|-------------|
| 1 | DTO `*-json` суффикс ≠ Entity/Gold | ✅ DONE | Уже в main (до аудита) |
| 2 | `action-type-parent` ≠ `action-type-parent-type` | ✅ DONE | Уже в main (до аудита) |
| 3 | `taxonomy-id` перегружен (Activity/Assay) | ✅ DONE | Уже в main (до аудита) |
| 4 | Taxonomy тип `string` ≠ `float64` | ✅ DONE | Уже в main (до аудита) |
| 5 | DTO taxonomy поля с API-именами | ✅ DONE | Уже в main (до аудита) |
| 6 | Filtering config рефакторинг | ✅ DONE | PR #2122 |
| 7 | DQ-конфиг molecule: entity + pipeline inline | ✅ DONE | PR #2135 (`5c83044`) |
| 8 | Assay filter `column-name` | ✅ DONE | Уже в main (`360e357`) |
| 9 | Molecule property alias дублирование | ✅ DONE | PR #2138 (`0c2b69b`) |
| 10 | DTO-only поля Target | ✅ DONE | PR #2136 (`1ff8a2e`) |
| 11 | `-normalize-source-config` complexity | ✅ DONE | PR #2137 (`14eea38`) |
| 12 | Deprecated bootstrap alias миграция | ✅ DONE | PR #2134 (`401ccbe`) |

### 1.2 Что НЕ менялось (by design)

| Тема | Обоснование |
|------|-------------|
| `assay-pref-name` → `pref-name` | Entity/Gold уже синхронны, не критично |
| `organism` bare vs prefixed | Корректно: bare в своём пайплайне, prefix при денормализации |
| `parent-molecule-id` vs `hierarchy-parent-chembl-id` | Разные уровни абстракции (FK vs hierarchy) |
| Target/TargetComponent `taxonomy-id` (bare) | Нет семантической перегрузки — в Target контексте однозначно |
| `variant-sequence-json` / `features-json` | Forensic-поля, намеренно хранят исходный JSON |

---

## 2. Выполненные рефакторинги (v1.0 → v2.0 → v3.0)

### Фаза 1: DTO ↔ Entity/Gold синхронизация (v1.0)

| ID (v1) | Задача | Коммит |
|---------|--------|--------|
| RF-01..04 | Убрать `-json` суффикс в DTO Activity/Assay/Target/Molecule | Уже в main |
| RF-05 | DQ entity-level конфиг molecule → Silver-имена | Уже в main |
| RF-06 | Assay filter `column-name` → unified name | `360e357` |
| RF-07 | Silver Target: `component-id` → `primary-component-id` | Уже в main |

### Фаза 2: Taxonomy семантическая унификация (v1.0)

| ID (v1) | Задача | Коммит |
|---------|--------|--------|
| RF-08 | Activity: `taxonomy-id` → `target-taxonomy-id` + float64 | Уже в main |
| RF-09 | Assay: `taxonomy-id` → `assay-taxonomy-id` | Уже в main |
| RF-10 | Документация taxonomy переименований | Уже в main |

### Фаза 1 (v2.0): Config-уровень

| ID (v2) | Задача | PR | Коммит |
|---------|--------|-----|--------|
| RF-01 | Pipeline inline DQ molecule → Silver-имена | #2135 | `5c83044` |
| RF-02 | Assay filter `column-name` | — | `360e357` |

### Фаза 2 (v2.0): Molecule property alias

| ID (v2) | Задача | PR | Коммит |
|---------|--------|-----|--------|
| RF-03 | Molecule Gold: `property-*` → canonical alias (Вариант A) | #2138 | `0c2b69b` |

### Фаза 3 (v2.0): DTO-only поля Target

| ID (v2) | Задача | PR | Коммит |
|---------|--------|-----|--------|
| RF-04 | Удалены `dap-id`, `target-constraints`, `component-tax-ids` из config/docs | #2136 | `1ff8a2e` |

### Фаза 4 (v2.0): Техдолг

| ID (v2) | Задача | PR | Коммит |
|---------|--------|-----|--------|
| RF-05 | Декомпозиция `-normalize-source-config` → 4 функции (40 LOC) | #2137 | `14eea38` |

### Дополнительно

| Задача | PR | Коммит |
|--------|-----|--------|
| SilverFilterConfig nominal type separation | #2122 | — |
| BaseConfigLoader abstraction | #2122 | — |
| `dq-overrides` → `dq-overrides` rename | #2122 | — |
| Directory fallback (filters/filter, quality/dq) | #2122 | — |
| Deprecated bootstrap alias → canonical names | #2134 | `401ccbe` |
| Monitor deprecated aliases (runtime warnings) | #2134 | — |

---

## 3. Верификация

### Команды проверки

```bash
# Linting
ruff check src/ tests/
ruff format --check src/ tests/

# Type checking
mypy --config-file pyproject.toml src/bioetl/

# Architecture tests
pytest tests/architecture/ -v

# Full test suite
pytest tests/ -m "not e2e and not benchmark" --ignore=tests/e2e --ignore=tests/contract -q

# Coverage
pytest --cov=src/bioetl --cov-fail-under=85
```

### Остаточные grep-проверки (все должны давать 0 совпадений)

```bash
# -json в DTO (кроме forensic-полей)
grep -rn "-json" src/bioetl/domain/entities/chembl.py | \
  grep -v "variant-sequence-json\|features-json\|#\|serialize-to-json"

# bare taxonomy-id в Activity/Assay
grep -rn '"taxonomy-id"' src/bioetl/domain/entities/bioactivity.py \
  src/bioetl/domain/contracts/gold/chembl.py

# action-type-parent без -type
grep -rn "action-type-parent[^-]" src/ --include="*.py"

# property-* в Molecule Gold (должно быть 0 — только canonical aliases)
grep "property-" src/bioetl/domain/contracts/gold/chembl.py | grep -i molecule

# Deprecated bootstrap aliases (должны быть только в compatibility shim)
grep -rn "from bioetl.*-bootstrap\|from bioetl.*bootstrap" src/bioetl/ --include="*.py" | \
  grep -v "composition/bootstrap\|--init--"
```

---

## 4. Архитектурные решения

| Решение | Выбор | Обоснование |
|---------|-------|-------------|
| Molecule Gold alias strategy | **Вариант A**: только canonical | Чистый API для downstream, property-* остаются в Silver |
| Target DTO-only fields | Удалены из config/docs | `dap-id`, `target-constraints`, `component-tax-ids` не используются downstream |
| `-normalize-source-config` | Декомпозиция на 4 функции | 147 LOC → 40 LOC, CC>15 → CC<10 |
| Filter config types | SilverFilterConfig nominal type | Structurally identical to Gold but type-distinct |
| DQ config naming | `dq-overrides` (backward-compat alias `dq-overrides`) | AliasChoices обеспечивает обратную совместимость |
