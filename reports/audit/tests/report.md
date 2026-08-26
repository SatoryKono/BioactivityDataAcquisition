# Audit: tests-system

| Field | Value |
| --- | --- |
| `domain_id` | `tests-system` |
| `prompt_id` | `prompt.audit.tests-system` |
| `version` | 1.2.0 |
| `MODE` | `audit` |
| `AUDIT_MODE` | `full` |
| `LANGUAGE` | `ru` |
| `SCOPE` | `tests/` `configs/quality/` |
| `REQUIRE_GH_TRACKING` | `false` |
| `surface_score` | **2** / 3 |
| `date` | 2026-08-26 |
| `blocked` | `false` |

## Executive summary

Тестовая система BioETL — зрелый pytest-контур regression-detection: именованные lanes (ADR-042 / `configs/quality/test_matrix.yaml`), раздельные unit/integration/contract/e2e/architecture/security/smoke/performance, coverage-verify 85% line+branch, VCR replay-only по умолчанию, skip-census для contract/integration, пустой curated flaky inventory. CI **запускает** эти гейты на PR, но **не блокирует merge в `main`** (ruleset enforcement=disabled). Отдельный системный дефект: глобальный `addopts -m "not benchmark and not slow"` делает `@pytest.mark.slow` недостижимым в канонических lanes и почти во всех workflow без `-o addopts=`.

**Score 2 (acceptable):** ядро механизма корректно и автоматизировано; есть локальные, но материальные gaps (deselection slow-тестов, e2e skip вне census, xdist vs serial policy, optional merge). Не 3: CI не является merge-truth и часть security/e2e/architecture тестов не коллекционируется. Не 1: unit/integration/architecture/coverage на PR реально исполняются и падают closed внутри workflow.

## Method / evidence

- Инспекция `pyproject.toml` `[tool.pytest.ini_options]`, `configs/quality/test_matrix.yaml`, skip/flaky/e2e SLO/coverage/mutation/VCR policies.
- Инспекция `.github/workflows/tests.yml`, `e2e-matrix-health.yml`, `import-linter.yml`, `contract-tests.yml`, `mutation-testing.yml`, `architecture.yml`, `security.yml`.
- Поиск `skip`/`xfail`/`flaky`/`rerun`/`.only`/`-n auto` по `tests/**` и workflows.
- Сверка RULES.md §4.2, ADR-042, `docs/03-guides/testing.md`, `docs/00-project/governance/05-github-policy.md`.
- Live GitHub ruleset API **не** перепроверялся в этой сессии (документированное состояние 2026-08-19).
- Повторные прогоны flaky **не** выполнялись (нет shell; бюджет full-suite запрещён карточкой).

## Inventory

### Stack (proven)

- Framework: pytest (`pyproject.toml` `[tool.pytest.ini_options]`).
- Coverage: pytest-cov; `fail_under` **не** в pyproject (намеренно); hard gate только `coverage-verify` (`coverage report --fail-under=85` + branch 85%).
- HTTP: VCR.py / pytest-recording; default `VCR_RECORD_MODE=none` (`tests/conftest.py`).
- Property: Hypothesis (`HYPOTHESIS_PROFILE=ci` в Tests workflow).
- Parallel: local default serial (`forbid_global_xdist_addopts: true`); CI opt-in xdist на части jobs.

### Levels present

| Level | Path | PR-blocking workflow job (если workflow запущен) |
| --- | --- | --- |
| unit (pure) | `tests/unit/**` minus scripts/repo_backed | `test-fast`, `test-matrix` |
| unit fs_contract | classified modules | `unit-filesystem-contracts` |
| unit repo_backed | `tests/unit/repo_backed/` | `repo-backed-unit` |
| unit scripts | `tests/unit/scripts/` | `unit-scripts-tooling` |
| integration | `tests/integration/` | `test-matrix` (group integration) |
| contract offline | `tests/contract/` + `tests/unit/contracts/` | `contract-confidence` (`no_api or not network`) |
| contract live | `tests/contract/` `--network` | monthly `contract-tests.yml` only |
| architecture | `tests/architecture/` | `import-linter.yml` job `arch-tests` (`not slow`) |
| e2e smoke | matrix + chembl activity | `e2e-matrix-health.yml` `matrix-smoke-blocking` |
| e2e control-plane | pubchem full cycle | `tests.yml` `control-plane-e2e` |
| e2e nightly | `tests/e2e/` minus e2e_smoke | schedule in `e2e-matrix-health.yml` |
| security | `tests/security/` | `test-matrix` group security |
| smoke | `tests/smoke/` | `smoke-check` (`not memory`) |
| memory | neo4j/mcp smoke | `memory-tests` |
| performance | `tests/performance/` | `performance-budgets` |
| mutation | domain + curated application | `mutation-testing.yml` (path-filtered PR) |
| migration | — | **absent as named suite** (не указано) |

`pytest.ini` / `tox.ini` отсутствуют; SSOT — `pyproject.toml`.

### Canonical local commands

Windows: `.\.venv-win\Scripts\python.exe -m pytest …`  
Canonical unit-fast (TEST_LANE mental model):

```text
pytest tests/unit -m "not fs_contract and not repo_backed and not subprocess_backed and not slow and not benchmark and not memory" --ignore=tests/unit/scripts --ignore=tests/unit/repo_backed
```

Direct runner: `scripts/engineering/dev/run_pytest.sh`. Default addopts already exclude `slow` and `benchmark`.

## Checklist

- [x] Tests from clean checkout path documented (`docs/03-guides/testing.md`, `test_matrix.yaml` execution_defaults)
- [x] Unit tests not requiring external network by default (no `pytest.mark.network` under `tests/unit/`; contract network is opt-in)
- [x] Isolation of temp dirs/ports/time/random (FixedClock, uuid4 budget 0, VCR none, cwd pin)
- [ ] Quarantine has owner + expiry for **e2e** skips (contract/integration census есть; e2e — нет)
- [x] Focused tests (`.only`) — не найдены
- [ ] `@pytest.mark.slow` имеет исполняемый CI owner (почти нет; исключение: `security.yml` detect-secrets с `-o addopts=`)

## Surface score legend

| Score | Meaning |
| --- | --- |
| 3 | Critical paths covered; tests isolated/stable; CI actually blocks |
| 2 | Solid base; local gaps or limited observability |
| 1 | Material flaky/disabled zones, weak isolation, or optional CI |
| 0 | Tests broken/absent on critical path, or green CI is fiction |

Mapping used: domain card 0–3 (not 0–5).

## Findings (max 20, PROVEN preferred)

См. `findings.json`. Кратко:

1. **TEST-SYS-001 P1** — `addopts -m "not benchmark and not slow"` AND-комбинируется с любым CLI `-m`; `@pytest.mark.slow` недостижим в Tests/E2E/architecture lanes.
2. **TEST-SYS-002 P1** — required-check ruleset на `main` disabled; merge/push не требуют test jobs.
3. **TEST-SYS-003 P2** — CI `-n auto` на `test-fast` и `test-matrix` vs `serial_or_bounded_lanes` (unit-fast, integration-replay); VCR integration почти без `serial`.
4. **TEST-SYS-004 P2** — skip inventory не покрывает `tests/e2e/` (24 census rows только contract/integration).
5. **TEST-SYS-005 P2** — `e2e_skip_rate_slo.yaml` mode=`advisory`; blocking 15% только у matrix-smoke run3.
6. **TEST-SYS-006 P2** — 16 pipelines в `MATRIX_REPLAY_DEFERRED_PIPELINES` вне PR e2e-smoke; `chembl_publication_term` owner — dedicated e2e не в e2e-smoke.
7. **TEST-SYS-007 P2** — non-critical matrix VCR mismatch → `pytest.skip` (`INFRA_FLAKY_CASSETTE_MISMATCH`), не fail.
8. **TEST-SYS-008 P3** — `docs/03-guides/testing.md` ссылается на несуществующий `tests/infrastructure/**`.
9. **TEST-SYS-009 P3** — гайды рекомендуют `pytest -m slow` без `-o addopts=`, что даёт пустую выборку.
10. **TEST-SYS-010 NOT_PROVEN** — flaky: curated inventory пуст; повторный N-run в этой сессии не выполнялся.

## What works (do not rediscover as unknown)

- Coverage 85% line + 85% branch — project-defined, enforced in `coverage-verify`.
- Unconditional `@pytest.mark.skip` запрещён в unit/architecture (`test_test_skip_inventory.py` #9130).
- `*.disabled` test modules запрещены.
- xfail в продуктовых тестах не используется (только в census-тестах).
- pytest-rerunfailures отсутствует; retries не используются как flaky-fix в pyproject.
- VCR LFS fail-closed в `vcr-preflight` / control-plane-e2e.
- Network contract tests opt-in (`--network` / `BIOETL_NETWORK_TESTS`).
- Mutation: domain 70% + curated application 60% enforced; broad application staged (ADR-042).
- Flaky telemetry job: 3 seeds на узком determinism slice (не healer).
- E2E matrix smoke: 3x rerun + skip-rate 15% + fail on non-zero pytest (diagnostic, not retry-to-green).

## Critical path → tests

| Product path | Tests | PR gate | Residual risk |
| --- | --- | --- | --- |
| ChEMBL activity pipeline | unit/integration + e2e_smoke + matrix | yes | low |
| PubChem compound control-plane | `test_pubchem_compound_full_cycle` | `control-plane-e2e` | LFS-dependent |
| Other CRITICAL_SMOKE providers | matrix smoke (cassette) | e2e-matrix-health | skip on non-critical mismatch |
| Deferred chembl entities / composites | unit/integration owners; e2e deferred | partial | see TEST-SYS-006 |
| Gold DQ / schema | `tests/contract/test_gold_*` | contract-confidence | live API monthly only |
| Layer boundaries | `tests/architecture/` + lint-imports | `arch-tests` | `@pytest.mark.slow` skipped |
| Secret in VCR cassettes | `TestVCRCassetteSanitization` | **no** (slow) | TEST-SYS-001 |
| CLI / composition bootstrap | unit interfaces/composition + e2e | partial | slow full-chain e2e skipped |

## CI gates vs merge

Workflows on PR (path-filtered `tests.yml` ignores `docs/**`): smoke, unit lanes, integration, security, contract-confidence, coverage-verify, memory, performance, e2e matrix smoke, architecture (`import-linter.yml`).

GitHub merge truth (`docs/00-project/governance/05-github-policy.md`, 2026-08-19): **no live required-check ruleset**. Recommended always-on contexts `checks-complete` + `root-hygiene` defined but enforcement=disabled. Live API this session: NOT_PROVEN.

## Flaky / disabled

- Curated `configs/quality/flaky_test_inventory.yaml`: `reviewed_flaky_tests: []` (reviewed_on 2026-08-03).
- Empirical CI: `flaky-telemetry` job writes `flaky-test-empirical.json` (3 seeds, 2 files) — не полный suite.
- Disabled zone: весь класс `@pytest.mark.slow` (~32 маркера) + e2e runtime skips.
- Quarantine owner+expiry: только contract/integration census; e2e — reason codes без inventory.

## Skipped checks

| Check | Reason |
| --- | --- |
| `python -m memory.tooling.workflow pre-task/post-task` | no shell tool in this runtime |
| Full/lane pytest execution | card forbids unbounded suite; no shell |
| Repeat N flaky runs | no shell; would need scoped N |
| Live GitHub ruleset GET | not called; cite dated governance doc |
| GitHub issue write | `REQUIRE_GH_TRACKING=false` |
| `.env` read for tokens | not required; env guardrail |

## Debt outcome

`unchanged` — audit-only, budgets not modified. **ЗАПРЕЩЕНО УВЕЛИЧИВАТЬ** skip/xfail/debt budgets.

## Top remediations

1. Добавить канонический slow-lane с `-o addopts=` (или убрать `-m` из global addopts и держать exclusion только в named lanes). Подключить `TestVCRCassetteSanitization` и architecture/e2e slow owners.
2. Не повышать budgets. Для merge-integrity — отдельное maintainer-решение по ruleset (вне этого audit MODE); до включения required checks считать coverage-verify/checks-complete **рекомендательными**.
3. Выровнять CI xdist: либо пометить VCR integration `serial`, либо доказать xdist-safety и перенести integration-replay в `explicit_parallel_lanes`.
4. Расширить `test_skip_inventory.yaml` на `tests/e2e/` **или** отдельный e2e skip census с owner/expiry; не поднимать skip-rate budget.
5. Вернуть deferred pipelines в e2e-smoke или сменить `entity_test_ownership` на PR-blocking unit/integration owners.
6. Non-critical cassette mismatch: fail-closed или quarantine с expiry, не skip.
7. После 3 nightly samples — promote e2e skip SLO `advisory` → `blocking` без повышения 15%.
8. Исправить testing.md (`tests/infrastructure/**`) и команды `pytest -m slow`.

## Artifacts

- `reports/audit/tests/report.md`
- `reports/audit/tests/findings.json`
- `reports/audit/tests/test-matrix.csv`
- `reports/audit/tests/coverage-evidence.json`
- `reports/audit/tests/flaky-tests.csv`
- `reports/audit/tests/disabled-tests.csv`
- `reports/audit/tests/critical-gap-map.md`
