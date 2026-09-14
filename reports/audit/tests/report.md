# Аудит тестовой системы (tests-system)

- **prompt_id:** `prompt.audit.tests-system`
- **AUDIT_MODE:** full
- **SCOPE:** `tests/` + `configs/quality/`
- **Дата (UTC):** 2026-09-14T06:23:37Z
- **surface_score:** 2 (ядро merge-gate работает; заявленный e2e-smoke не в required context)
- **REQUIRE_GH_TRACKING:** false (live GitHub ruleset не опрашивался; использован docs SSOT)

## Резюме

Тестовая система BioETL — pytest + именованные lane из `configs/quality/test_matrix.yaml` (ADR-042). Merge-истина — агрегатор `pr-gate-complete` (ruleset 13643213). Coverage line/branch 85% задан проектом (`coverage report --fail-under=85` + `check-branch-coverage`), не выдуман аудитом. Полный pytest не запускался.

Главный разрыв: lane `e2e-smoke` в матрице назван PR-blocking, но не входит в каталог/координатор required checks. `tests.yml` всё же блокирует PubChem `control-plane-e2e` и coverage 85%.

## Инвентарь

| Поверхность | Наблюдение |
| --- | --- |
| Конфиг pytest | Единственный SSOT: `pyproject.toml` `[tool.pytest.ini_options]`. `pytest.ini`/`tox.ini` отсутствуют. `--strict-markers`, `--strict-config`, timeout=60, `timeout_method=thread`, `filterwarnings=error`, addopts без xdist. |
| Модули `test_*.py` | 2437: unit 1595, architecture 515, integration 220, contract 43, e2e 27, security 13, smoke 7, prompts 8, benchmarks 5, performance 4 |
| Lane | 24 канонических lane в test_matrix.yaml |
| Уровни | unit, integration (VCR), contract, e2e, smoke, architecture, security, performance/benchmark, memory, prompts. Отдельной migration-lane нет. `docker_integration` — opt-in. |
| Маркеры | strict list в pyproject; `contract`/`contracts` — совместимый alias. |
| Skip | `test_skip_inventory.yaml`: 31 entry, suites contract/integration/e2e, все `permanent_policy`, без `temporary_debt`/`expires_on`. 10 grafana/dashboard. 16 pipeline в `e2e_matrix_replay_deferred`. |
| xfail / `*.disabled` | 0 product xfail; 0 `*.disabled` |
| Flaky | `flaky_test_inventory.yaml` `reviewed_flaky_tests: []`. `pytest-rerunfailures` не в pyproject. Retries: e2e-matrix 3× diagnostic + flaky-telemetry 3 seed на 2 файла. |
| Isolation | Local serial default; VCR default `none`; `BIOETL_RANDOM_ORDER_SEED` opt-in shuffle; Windows xdist cap 1 в conftest; uuid4/date.today budgets 0 в test-governance. |
| Coverage | CI `coverage-verify` `--fail-under=85`; pyproject `fail_under` намеренно не задан (partial shards). `LOCAL_COV_FAIL_UNDER?=80` только для `make test-cov-fast-stable`. |
| CI tests.yml | `on: workflow_call` + push (не pull_request). PR вызывает reusable через `pr-required.yml`. |
| Required checks | Каталог: lint-arch, tests, type-checking, security, codeql, docker (path), duplication, root-hygiene, generated-artifacts (path), compiled-artifacts, commit-governance, docs-governance. |

## Канонические команды (Windows)

```powershell
.\scripts\engineering\dev\run_pytest.ps1 tests\unit --narrow --timeout=120 --lf
.\.venv-win\Scripts\python.exe -m pytest tests/unit -m "not fs_contract and not repo_backed and not subprocess_backed and not slow and not benchmark and not memory" --ignore=tests/unit/scripts --ignore=tests/unit/repo_backed
```

Unit-fast / architecture-fast-boundary — как в `TEST_LANE_MENTAL_MODEL.md`. Clean checkout: `setup_env_windows.ps1` затем wrapper.

## CI: что реально блокирует merge

- **Ruleset:** только `pr-gate-complete` (docs SSOT, 2026-09-10).
- **Через tests.yml (вызывается координатором):** smoke, governance-preflight, test-fast, repo-backed, scripts-tooling, fs-contracts, subprocess-backed, test-matrix (unit shards + integration serial + security), memory-tests, coverage-verify 85%, coverage-inventory-currentness, control-plane-e2e (PubChem), contract-confidence, flaky-telemetry, tests-complete fail-closed.
- **Не в агрегаторе:** `.github/workflows/e2e-matrix-health.yml` `matrix-smoke-blocking` (заявленный e2e-smoke). Workflow всё ещё триггерится на `pull_request`, но не required.
- **Architecture PR:** `import-linter.yml` `arch-tests` с `-m not slow/benchmark/memory` (fast-boundary). Slow-governance — не обязательный PR default.
- **Live contracts:** scheduled `contract-tests.yml` (REQ-TEST-006), не PR.

## Checklist

- [x] Путь с clean checkout задокументирован (dev README + mental model)
- [x] Unit по умолчанию без сети (`mark.network` в tests/unit не найден; VCR default none)
- [x] Isolation temp/time/random в целом есть; Windows architecture skip — gap (TEST-SYS-002)
- [x] Quarantine: curated flaky inventory пуст; skip census без temporary_debt (expiry N/A)
- [x] `.only` не применим (нет pytest-only plugin; `--strict-markers`)

## Working-tree noise (не finding)

Checkout на `main` с незакоммиченным Grafana/HTTP WIP: dashboard JSON, prometheus-rules, grafana tests (`tests/architecture/test_grafana_*`, `tests/unit/scripts/ops/observability/*`, HTTP recent_pipeline_runs). Не трактовать как дефект тестовой системы, пока это не ломает collect/config. Аудит читал tracked configs, не WIP-дифф как SSOT.

## Findings

См. `findings.json`. 5 PROVEN, P0=0, P1=1.

## Residual / critical gaps (не отдельные дефекты системы)

- 16 pipeline вне PR e2e-smoke через `MATRIX_REPLAY_DEFERRED_PIPELINES` (#9729) — reviewed policy, не silent skip.
- Empirical flaky telemetry — 3 seed × 2 файла, не suite-wide; не маркировать flaky без N-rerun.
- `test_governance_audit.yaml` `audit_date: 2026-05-26` / shards `refreshed_at_utc: 2026-07-13` — метаданные старше текущего дерева; budgets всё ещё enforced architecture-тестами.

## Проверки

| Проверка | Результат |
| --- | --- |
| `pytest tests/architecture/test_pytest_config_single_source.py --collect-only` | 3 collected, exit 0 |
| `pytest tests/architecture/test_pytest_config_single_source.py -q --no-cov -p no:xdist` | passed, exit 0 @ 2026-09-14T06:23:37Z |
| Full pytest | **не запускался** (запрет unbounded) |
| Live GitHub ruleset API | **пропущен** (`REQUIRE_GH_TRACKING=false`); сверка по `05-github-policy.md` |
| N-rerun flaky | не выполнялся (нет кандидатов с repeat counts) |
| `.env` | не трогался |
| Debt budgets | не менялись |

## Top remediations

1. Включить e2e-smoke owner в pr-gate-complete **или** убрать формулировку PR-blocking из test_matrix.
2. Зафиксировать Windows/WSL architecture skip в census и/или дать Windows-safe subset.
3. Расширить skip forbid до AST Call walker.
4. Синхронизировать `gates.tests.owner_jobs` с `tests-complete.needs`.
