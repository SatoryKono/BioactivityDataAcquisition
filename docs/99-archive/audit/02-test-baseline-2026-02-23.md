# Test Baseline: full-audit-2026-02-23

**Дата**: 2026-02-23 (baseline)
**Фаза**: baseline
**RF scope**: (full audit — все модули)
**Python**: 3.11.14
**pytest**: 8.4.2
**Среда**: uv, local (без Docker/network)

---

## Результаты

### Итог по всем тестам (без e2e, benchmarks, performance)

| Категория | Total | Pass | Fail | Skip | Error |
|-----------|:-----:|:----:|:----:|:----:|:-----:|
| **ИТОГО** | **12352** | **12113** | **1** | **238** | **0** |

### Разбивка по директориям

| Категория | Total | Pass | Fail | Skip | Error |
|-----------|:-----:|:----:|:----:|:----:|:-----:|
| unit | 9556 | 9554 | 0 | 2 | 0 |
| architecture | 1372 | 1350 | 1 | 21 | 0 |
| integration | 435 | 430 | 0 | 5 | 0 |
| contract | 695 | 485 | 0 | 210 | 0 |
| security | 22 | 22 | 0 | 0 | 0 |
| smoke | 41 | 41 | 0 | 0 | 0 |
| root-level (test_architecture.py + test_data_storage.py) | 175 | 175 | 0 | 0 | 0 |

**Время выполнения**: ~96 сек (параллельно, -n auto)

### Пропущенные тесты (skip) — причины

| Количество | Причина |
|:----------:|---------|
| 210 | Live API tests disabled (`BIOETL_LIVE_API_TESTS` not set) — contract tests для ChEMBL, PubChem, UniProt, PubMed, publication schemas |
| 19 | Schema uses global coerce — field-level checks не применимы |
| 5 | VCR cassette not yet recorded (chembl filtered API request tests) |
| 2 | `requires full composition context` (deprecation warning tests) |
| 1 | Legacy `_bootstrap` package not found |
| 1 | Bootstrap not found (tracing enforcement) |
| 1 | No allowed files in composition layer (expected) |

---

## Coverage

### По слоям

| Слой | Statements | Missed | Coverage |
|------|:----------:|:------:|:--------:|
| **domain** | 10 575 | 689 | **93.48%** |
| **application** | 7 339 | 399 | **94.56%** |
| **infrastructure** | 9 137 | 856 | **90.63%** |
| **interfaces** | 1 221 | 25 | **97.95%** |
| **composition** | 2 385 | 517 | **78.32%** |
| **OVERALL** | **30 694** | **2 501** | **89.53%** |

### Пороги качества

| Метрика | Порог | Факт | Статус |
|---------|:-----:|:----:|:------:|
| Coverage (overall) | ≥85% | 89.53% | PASS |
| Coverage (domain) | ≥90% | 93.48% | PASS |
| Coverage (composition) | ≥85% | 78.32% | **WARN** |
| mypy errors | 0 | 0 | PASS |
| Architecture tests | 100% | 99.93% (1350/1371) | **FAIL** |
| ruff lint | 0 errors | 0 errors | PASS |
| ruff format | 0 issues | 1 file | **FAIL** |

### Модули с покрытием ниже 70% (требуют внимания)

| Модуль | Coverage |
|--------|:--------:|
| `src/bioetl/domain/schemas/generated/__init__.py` | 0.00% |
| `src/bioetl/domain/schemas/generated/registry.py` | 0.00% |
| `src/bioetl/domain/services/_date_helpers.py` | 0.00% |
| `src/bioetl/infrastructure/storage/delta_writer.py` | 0.00% |
| `src/bioetl/infrastructure/adapters/chembl/deduplication.py` | 13.16% |
| `src/bioetl/composition/bootstrap/runtime/composite.py` | 20.96% |
| `src/bioetl/infrastructure/adapters/cached_bronze_data_source.py` | 22.47% |
| `src/bioetl/domain/value_objects/inchi.py` | 31.25% |
| `src/bioetl/composition/_resource_management.py` | 33.33% |
| `src/bioetl/composition/_services.py` | 43.18% |
| `src/bioetl/domain/value_objects/molecular_descriptors.py` | 44.76% |
| `src/bioetl/__init__.py` | 49.06% |
| `src/bioetl/composition/factories/http_client_factory.py` | 52.11% |
| `src/bioetl/infrastructure/adapters/pubchem/client.py` | 53.60% |
| `src/bioetl/domain/ports/data_normalization.py` | 55.26% |
| `src/bioetl/composition/providers/registration.py` | 57.96% |
| `src/bioetl/infrastructure/adapters/uniprot/client.py` | 59.44% |
| `src/bioetl/domain/ports/storage.py` | 60.87% |
| `src/bioetl/application/pipelines/chembl/tissue_transformer.py` | 61.11% |
| `src/bioetl/infrastructure/adapters/filterable_mixin.py` | 61.11% |
| `src/bioetl/composition/factories/storage_adapter.py` | 61.41% |
| `src/bioetl/domain/ports/observability.py` | 61.90% |
| `src/bioetl/composition/services/versioning.py` | 63.64% |
| `src/bioetl/domain/ports/delta_reader.py` | 64.29% |
| `src/bioetl/composition/bootstrap/cli/metrics.py` | 66.67% |
| `src/bioetl/infrastructure/adapters/openalex/fallback.py` | 65.52% |

---

## Failures (1 failure)

### FAIL-001
- **Тест**: `tests/architecture/test_code_formatting.py::TestCodeFormatting::test_ruff_formatting_src`
- **Категория**: architecture
- **RF**: N/A (baseline — не связано с конкретным RF)
- **Тип ошибки**: AssertionError — ruff format check
- **Файл нарушителя**: `src/bioetl/infrastructure/storage/gold_writer.py`
- **Stack trace**:
  ```
  AssertionError: Code formatting issues found in src/:
    Would reformat: src/bioetl/infrastructure/storage/gold_writer.py
    1 file would be reformatted, 569 files already formatted

  Run `ruff format src` to fix formatting issues.
  assert 1 == 0
   +  where 1 = CompletedProcess(args=[..., 'ruff', 'format', '--check', 'src'], ...).returncode
  ```
- **Фикс**: `uv run ruff format src/bioetl/infrastructure/storage/gold_writer.py`
- **Статус**: Pre-existing baseline failure. Не блокирует рефакторинг, но MUST fix (ARCH).

---

## mypy — Type Check

```
Success: no issues found in 542 source files
```

Статус: **PASS** (0 ошибок, strict mode)

---

## ruff lint

```
All checks passed!
```

Статус: **PASS** (0 нарушений в src/ и tests/)

---

## ruff format

```
Would reformat: src/bioetl/infrastructure/storage/gold_writer.py
1 file would be reformatted, 569 files already formatted
```

Статус: **FAIL** — 1 файл требует форматирования.

---

## Skipped Tests — Детали

### Architecture tests skipped (21)

| Причина | Количество |
|---------|:----------:|
| `CHEMBL_ACTIVITY_SCHEMA uses custom column order` | 9 (test_column_order.py) |
| `CHEMBL_*/PUBCHEM_* use custom column order` | 9 (test_column_order.py) |
| `Legacy _bootstrap package not found` | 1 |
| `No allowed files in composition layer (expected)` | 1 |
| `Bootstrap not found` (tracing enforcement) | 1 |

### Integration tests skipped (5)

| Причина | Количество |
|---------|:----------:|
| VCR cassette not yet recorded (filtered API request tests) | 5 |

Затронутые файлы:
- `tests/integration/chembl/test_activity_extraction_params.py` — `test_filtered_api_request`
- `tests/integration/chembl/test_assay_extraction_params.py` — `test_assay_filtered_api_request`
- `tests/integration/chembl/test_publication_extraction_params.py` — `test_publication_filtered_api_request`
- `tests/integration/chembl/test_target_extraction_params.py` — `test_target_filtered_api_request`
- `tests/integration/chembl/test_molecule_extraction_params.py` — `test_molecule_filtered_api_request`

Для записи кассет: `VCR_RECORD_MODE=new_episodes pytest -k test_filtered_api_request`

---

## Общая оценка состояния

| Компонент | Статус | Комментарий |
|-----------|:------:|-------------|
| Unit tests | **GREEN** | 9554/9556, 0 failures |
| Integration tests | **GREEN** | 430/435, 0 failures (5 skipped — нет кассет) |
| Architecture tests | **YELLOW** | 1350/1372 — 1 fail (ruff format), 21 skipped |
| Contract tests | **GREEN** | 485/695 — 0 failures (210 skipped — live API disabled) |
| Security tests | **GREEN** | 22/22 |
| Smoke tests | **GREEN** | 41/41 |
| Coverage (overall) | **GREEN** | 89.53% > 85% threshold |
| Coverage (domain) | **GREEN** | 93.48% > 90% threshold |
| Coverage (composition) | **YELLOW** | 78.32% < 85% threshold |
| mypy (strict) | **GREEN** | 0 errors in 542 files |
| ruff lint | **GREEN** | 0 errors |
| ruff format | **RED** | 1 file: `gold_writer.py` |

---

## Рекомендации для py-debug-bot

### DBG-001 (HIGH): Исправить форматирование gold_writer.py

Это единственный failing test. Фикс тривиальный:

```bash
uv run ruff format src/bioetl/infrastructure/storage/gold_writer.py
```

### Внимание: Composition layer coverage (78.32%)

Composition layer ниже порога 85%. Наиболее критичные модули:
- `bootstrap/runtime/composite.py` (20.96%) — composite pipeline bootstrap
- `_resource_management.py` (33.33%)
- `_services.py` (43.18%)
- `factories/http_client_factory.py` (52.11%)
- `providers/registration.py` (57.96%)

Рекомендуется добавить тесты для composition layer в рамках следующего sprint.

### VCR cassettes missing (5 skipped)

5 тестов интеграции пропущены из-за отсутствия VCR кассет. Требуется запись с реальным API:

```bash
VCR_RECORD_MODE=new_episodes uv run pytest tests/integration/chembl/ -k "filtered_api_request" -v
```

---

*Сформировано: py-test-bot | 2026-02-23 | task_id=full-audit-2026-02-23*
