# /verify-architecture

Проверка архитектурных правил проекта BioETL перед коммитом или PR.

## Использование

```
/verify-architecture [mode] [category]
```

**Режимы:**
- `quick` — быстрая проверка (критические правила, ~30 сек)
- `full` — полная проверка (все 43 теста, ~2-3 мин)
- `category` — только указанная категория

**Категории:**
- `imports` — матрица импортов, forbidden imports
- `di` — Dependency Injection violations
- `metrics` — размеры файлов/классов/функций, god objects
- `contracts` — Port contracts, adapter contracts, schemas
- `docs` — документация, версии, docstrings
- `style` — форматирование, naming, logging

**Примеры:**
```
/verify-architecture              # quick mode по умолчанию
/verify-architecture full         # полная проверка
/verify-architecture imports      # только проверка импортов
/verify-architecture full di      # полная проверка DI
```

---

## Инструкции для Claude

При вызове этого skill выполни проверки согласно выбранному режиму.

### Режим `quick` (по умолчанию)

Запусти критические проверки, блокирующие PR:

```bash
cd "E:\google_drive\05_AI\github\BioactivityDataAcquisition2"

# 1. Layer imports (БЛОКЕР)
uv run pytest tests/architecture/test_layer_dependencies.py tests/architecture/test_forbidden_imports.py -v --tb=short 2>&1 | tail -30

# 2. DI violations (БЛОКЕР)
uv run pytest tests/architecture/test_di_compliance.py tests/architecture/test_di_constructors.py -v --tb=short 2>&1 | tail -30

# 3. Code metrics (WARNING)
uv run pytest tests/architecture/test_code_metrics.py -v --tb=short 2>&1 | tail -40

# 4. Lint
uv run ruff check src/bioetl/ --select=E,F,I --statistics 2>&1 | tail -20
uv run mypy src/bioetl/ --no-error-summary 2>&1 | tail -20
```

### Режим `full`

Запусти все архитектурные тесты:

```bash
uv run pytest tests/architecture/ -v --tb=short -q 2>&1
```

### Категория `imports`

```bash
uv run pytest tests/architecture/test_layer_dependencies.py \
              tests/architecture/test_forbidden_imports.py \
              tests/architecture/test_domain_purity.py \
              tests/architecture/test_interfaces_no_infrastructure.py \
              tests/architecture/test_composite_layer_boundaries.py \
              tests/architecture/test_bootstrap_layer_boundaries.py \
              -v --tb=short 2>&1
```

### Категория `di`

```bash
uv run pytest tests/architecture/test_di_compliance.py \
              tests/architecture/test_di_constructors.py \
              tests/architecture/test_di_discipline.py \
              tests/architecture/test_no_side_effects_in_composition.py \
              -v --tb=short 2>&1
```

### Категория `metrics`

```bash
uv run pytest tests/architecture/test_code_metrics.py \
              tests/architecture/test_code_formatting.py \
              -v --tb=short 2>&1
```

### Категория `contracts`

```bash
uv run pytest tests/architecture/test_port_contracts.py \
              tests/architecture/test_adapter_contracts.py \
              tests/architecture/test_registry_contracts.py \
              tests/architecture/test_gold_schema_contracts.py \
              tests/architecture/test_transformer_signatures.py \
              tests/architecture/test_metadata_output_contract.py \
              -v --tb=short 2>&1
```

### Категория `docs`

```bash
uv run pytest tests/architecture/test_documentation.py \
              tests/architecture/test_docs_version_sync.py \
              tests/architecture/test_domain_public_api.py \
              -v --tb=short 2>&1
```

### Категория `style`

```bash
uv run pytest tests/architecture/test_code_formatting.py \
              tests/architecture/test_no_fstring_in_logs.py \
              tests/architecture/test_no_structlog_in_application_interfaces.py \
              tests/architecture/test_no_logging_getlogger_in_infrastructure.py \
              tests/architecture/test_no_print_in_docstrings.py \
              -v --tb=short 2>&1
```

---

## Формат вывода

После выполнения проверок, предоставь структурированный отчёт:

```
## Architecture Verification Report

### Summary
| Category | Status | Tests | Passed | Failed |
|----------|--------|-------|--------|--------|
| Imports  | ✅/❌  | N     | N      | N      |
| DI       | ✅/❌  | N     | N      | N      |
| Metrics  | ✅/❌  | N     | N      | N      |
| ...      | ...    | ...   | ...    | ...    |

### Critical Failures (PR Blockers)
- ❌ test_forbidden_imports: infrastructure imported in domain
  - `src/bioetl/domain/foo.py:15` imports `infrastructure.bar`
- ❌ test_di_compliance: dependency created inside class
  - `src/bioetl/application/service.py:42` creates `HttpClient()`

### Warnings (Non-blocking)
- ⚠️ test_code_metrics: file exceeds LOC limit
  - `transformer.py: 520 LOC (limit: 500)`

### Recommendations
1. Fix forbidden import in `domain/foo.py`
2. Inject `HttpClient` via constructor
3. Consider splitting `transformer.py`
```

---

## Категории тестов

### 🔴 BLOCKERS (PR не пройдёт)

| Тест | Что проверяет | RULES.md |
|------|---------------|----------|
| `test_layer_dependencies` | Матрица импортов между слоями | §1.1 |
| `test_forbidden_imports` | Запрещённые импорты (infra→domain) | §1.1 |
| `test_di_compliance` | DI через конструктор | §1.2 |
| `test_di_constructors` | Нет создания зависимостей внутри | §1.2 |
| `test_domain_purity` | Domain без I/O и side effects | §1.1 |

### 🟡 WARNINGS (требуют внимания)

| Тест | Что проверяет | RULES.md |
|------|---------------|----------|
| `test_code_metrics` | LOC, CC, god objects | §6.3 |
| `test_code_formatting` | Ruff formatting | §4.3 |
| `test_docs_version_sync` | Версии документов | §7 |
| `test_port_contracts` | Protocol compliance | §1.3 |

### 🟢 INFO (рекомендации)

| Тест | Что проверяет |
|------|---------------|
| `test_no_fstring_in_logs` | Lazy logging |
| `test_pii_hashing` | PII в трансформерах |
| `test_registry_threading` | Thread-safety |

---

## Быстрые команды

```bash
# Только критические проверки (30 сек)
make arch-test-critical

# Полная проверка (2-3 мин)
make arch-test

# Конкретная категория
pytest tests/architecture/test_*import*.py -v

# С verbose output
pytest tests/architecture/ -v --tb=long -x
```

---

## Интеграция с CI

Тесты автоматически запускаются в GitHub Actions:
- `.github/workflows/tests.yml` — на каждый PR
- Блокеры останавливают merge
- Warnings отображаются как annotations

---

## Пример вызова

```
User: /verify-architecture

Claude: Запускаю быструю проверку архитектуры...

$ uv run pytest tests/architecture/test_layer_dependencies.py test_forbidden_imports.py ...

## Architecture Verification Report

### Summary
| Category | Status | Tests | Passed | Failed |
|----------|--------|-------|--------|
| Imports  | ✅     | 6     | 6      | 0      |
| DI       | ✅     | 4     | 4      | 0      |
| Metrics  | ⚠️     | 12    | 11     | 1      |
| Lint     | ✅     | -     | -      | -      |

### Warnings
- ⚠️ test_code_metrics::TestFileSizeLimits
  - `transformer.py: 520 LOC (limit: 500)`
  - Action: Add to EXEMPTIONS or refactor

### Result: ✅ Ready for commit (1 warning)
```

---

## Mapping тестов к RULES.md

| Тест файл | RULES.md секция |
|-----------|-----------------|
| `test_layer_dependencies.py` | §1.1 Матрица Импортов |
| `test_forbidden_imports.py` | §1.1 Запрещённые Импорты |
| `test_di_*.py` | §1.2 DI через Конструктор |
| `test_domain_purity.py` | §1.1 Domain Layer |
| `test_port_contracts.py` | §1.3 Ports & Adapters |
| `test_code_metrics.py` | §6.3 Метрики Кода |
| `test_code_formatting.py` | §4.3 Стиль Кода |
| `test_medallion_invariants.py` | §2 Medallion Architecture |
| `test_lock_safety_guard.py` | §4.6 Safety Guard |
| `test_docs_version_sync.py` | §7 Документация |
