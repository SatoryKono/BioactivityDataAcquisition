---
description: "Проверка архитектурных правил BioETL перед коммитом или PR. Режимы: quick, full, category."
---

# /verify-architecture

## Использование
```
/verify-architecture [mode] [category]
```

**Режимы:** `quick` (default, ~30s), `full` (all 43 tests), `category` (specific)
**Категории:** `imports`, `di`, `metrics`, `contracts`, `docs`, `style`

## Инструкции

### quick (default)
```bash
# 1. Layer imports (BLOCKER)
uv run pytest tests/architecture/test_layer_dependencies.py tests/architecture/test_forbidden_imports.py -v --tb=short
# 2. DI violations (BLOCKER)
uv run pytest tests/architecture/test_di_compliance.py tests/architecture/test_di_constructors.py -v --tb=short
# 3. Code metrics (WARNING)
uv run pytest tests/architecture/test_code_metrics.py -v --tb=short
# 4. Lint
uv run ruff check src/bioetl/ --select=E,F,I --statistics
uv run mypy src/bioetl/ --no-error-summary
```

### full
```bash
uv run pytest tests/architecture/ -v --tb=short -q
```

### Category-specific tests

| Category | Test files |
|----------|-----------|
| `imports` | `test_layer_dependencies`, `test_forbidden_imports`, `test_domain_purity`, `test_interfaces_no_infrastructure`, `test_composite_layer_boundaries`, `test_bootstrap_layer_boundaries` |
| `di` | `test_di_compliance`, `test_di_constructors`, `test_di_discipline`, `test_no_side_effects_in_composition` |
| `metrics` | `test_code_metrics`, `test_code_formatting` |
| `contracts` | `test_port_contracts`, `test_adapter_contracts`, `test_registry_contracts`, `test_gold_schema_contracts`, `test_transformer_signatures`, `test_metadata_output_contract` |
| `docs` | `test_documentation`, `test_docs_version_sync`, `test_domain_public_api` |
| `style` | `test_code_formatting`, `test_no_fstring_in_logs`, `test_no_structlog_in_application_interfaces`, `test_no_logging_getlogger_in_infrastructure`, `test_no_print_in_docstrings` |

## Severity

| Level | Tests | PR Impact |
|-------|-------|-----------|
| BLOCKER | imports, DI, domain purity | Blocks merge |
| WARNING | metrics, formatting, docs | Needs attention |
| INFO | fstring, PII, threading | Recommendations |

## Report Format
Table: Category | Status | Tests | Passed | Failed. Then Critical Failures (PR blockers) and Warnings.
