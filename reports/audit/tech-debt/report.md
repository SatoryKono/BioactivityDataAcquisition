# Аудит технического долга — BioactivityDataAcquisition

- Промпт: prompt.audit.tech-debt v1.3.0, MODE=audit, LANGUAGE=ru, SCOPE=repo-wide
- Прогоны: full (9 находок) + differential 2026-09-21 (маркеры стабильны: src 0 реальных, tests/scripts 43; type-ignore 74→64; nosec 32; pragma 23; циклы 30; god-module 17739)
- Измерения: новые, 2026-09-21 (grep-сводки + реестры + `git diff 09ab9ac..HEAD`)
- Находок: 9 (TD-001…TD-009); повышение бюджетов — НЕ предлагается
- surface_score (0–3): code 3, tests 3, config 3, dependencies 2, architecture 2, **общий 2**

## Сводка измерений

| Метрика | Значение | Источник |
| --- | --- | --- |
| TODO/FIXME/HACK/XXX/WORKAROUND в `src/bioetl` | 0 реальных (4 ложных: `CVCL_XXXX`, enum, ADR-шаблон) | grep |
| Маркеры в `tests/`,`scripts/` | 43 (тест-локальные) | grep |
| `nosec` в `src/` | 32, реестр + лок-тест | grep + `security_suppression_registry.yaml` |
| `type: ignore` в `src/` | 74, макс. 5/файл, рассредоточены | grep |
| `noqa` / `pragma: no cover` в `src/` | 12 / 23, с построчной rationale | grep |
| allowlist циклов импорта | 30 записей с owner + review_by | `basedpyright_import_cycle_allowlist.json` |
| God-module `sync_pkg/_core.py` | 17739 строк / 567 КБ (было 18179) | wc |
| Топ-модуль `src/bioetl` | 441 строка (size-долга в продукте нет) | find+wc |
| Дрейф `debt_scorecard.yaml` с 2026-08-20 | только вниз (6→5, 3→2, 2→0/1) | git diff |
| Гейт `debt-governance-gates.json` | все pass, рост запрещен | коммитованный отчет |

## Реестр по риску

### P1

| ID | Находка | Путь |
| --- | --- | --- |
| TD-001 | God-module `sync_pkg/_core.py` сохраняется (17.7k строк, было 18.1k); проектный tooling (Neo4j sync), под ruff/mypy-gates, декомпозиция идет (slice 1) | `src/memory/graph/sync_pkg/_core.py:1` |
| TD-002 | Мажорные холдбэки `pandas<2.3`, `deltalake<1.0` с rationale; пин arro3 снят (улучшение с AUD-006) | `pyproject.toml:26` |

### P2

| ID | Находка | Путь |
| --- | --- | --- |
| TD-003 | 30 allowlist-циклов импорта, все с owner/review_by; структурный остаток под замком | `configs/quality/basedpyright_import_cycle_allowlist.json:1` |
| TD-004 | Кластер `checkpoint_compatibility_*` (8+ модулей); transition-debt по скорингу = 0, но поверхность политики сохраняется — watch | `src/bioetl/application/services/checkpoint/:1` |

### P3

| ID | Находка | Путь |
| --- | --- | --- |
| TD-005 | 74 `type: ignore`, кластеры ≤5/файл (CLI, bronze_writer, context_run) — диффузный остаток | `src/bioetl/interfaces/cli/commands/domains/shared/click_options.py:1` |
| TD-006 | 32 `nosec`: lock-тест зелен 2026-09-21 (4 passed), реестр синхронен — закрыто | `configs/quality/security_suppression_registry.yaml:1` |
| TD-007 | 23 `pragma` проверены 2026-09-21: все EXCLUDED by design, снятие без тестов снизило бы покрытие; dated-review 2026-12-31 в будущем — снятий не due, закрыто как controlled | `src/bioetl/application/core/record_processor_config.py:63` |
| TD-008 | 11 `noqa: I001` удалены, applied twice (внешний откат между прогонами); gate чист, 86 тестов зеленые — закрыто | `src/bioetl/application/core/base_transformer/__init__.py:4` |
| TD-009 | 43 маркера разобраны 2026-09-21: 40 ложных (XXXXX-данные, guard-инфра, docstrings), 3 реальных уже удалены; локи зеленые — закрыто | `tests/:1` |

## Quick wins vs стратегический

- Quick wins: TD-008 (заменить noqa на isort-профиль для barrels), TD-009 (разобрать 43 маркера тестов).
- Стратегический: TD-001 (декомпозиция sync-ядра), TD-003 (вывод циклов из allowlist по review-датам).
- Зависимостный: TD-002 (валидация pandas 3.x / deltalake 1.x).

## Stop-подтверждение

Ни одна remediation не требует роста бюджетов/exemptions/порогов. Все правки — debt-reducing или budget-neutral.
