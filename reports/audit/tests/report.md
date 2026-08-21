<<<<<<< HEAD
# Tests-system cyclic audit — 20260821T114953Z-tests-cycle-27105f85

**Gate: WARN** · **surface_score: 2** · **debt_outcome: unchanged**

Независимый прогон `prompt.audit.tests-cycle` на clean `origin/main` @ `27105f8536`.
Чужой dirty tree (`fix/architecture-audit-cycle`) не трогался — работа в worktree.

## PROVEN findings

| ID | REQ | P | Issue | PR | Post-audit |
| --- | --- | ---: | ---: | ---: | --- |
| TEST-GOV-002 | REQ-GOV-012 | P2 | #9325 | #9327 (канон.) + branch `fix/audit-tests-cycle` `88de1a6c82` | resolved_on_branch (не на origin/main; ALLOW_MERGE=false) |
| TEST-SYS-012 | REQ-TEST-005 | P1 | #9040 | — | unchanged |

Других **PROVEN** находок после чтения checkout нет.

Новый issue не создавался (dedupe). Второй PR не открывался: #9327 уже содержит идентичный 2-file refresh. Ветка `fix/audit-tests-cycle` запушена как независимый re-verify.

## Почему не 10 пустых итераций

N=10 запрошен. Empty form cycles запрещены. После iteration 2 нет новых P0/P1; единственный исправимый PROVEN дефект тестового слоя обновлён на feature-branch. Итерации 3–10 остановлены.

## Checklist

- [x] Clean-checkout / documented entry command
- [x] Unit default без обязательной внешней сети
- [x] Skip/quarantine с owner/issue
- [x] Flaky: 0; без ложных N-repeat
- [x] CI required checks: ruleset disabled (документировано, #8619 closed)
- [x] test-governance snapshot drift найден и refresh-нут каноническим генератором
- [x] Skip/xfail/debt budgets не увеличены

## Skipped checks

- Полный `pytest tests/unit` / unit-fast (~21k) — вне бюджета LANE evidence
- Полный `tests/architecture` — heavy; взяты skip/governance/residual guards
- Live Grafana/monitoring stack — не требовался для tests-cycle
- Junie mirror — runtime trees не менялись
- `.env` — не изменялся

## Artifacts

- Этот run: `reports/audit-runs/20260821T114953Z-tests-cycle-27105f85/`
- Domain notes: `reports/audit/tests-cycle/20260821T114953Z-tests-cycle-27105f85/` (не перезаписывал чужой dirty `reports/audit/tests/`)
||||||| b48ac65c98
# Tests audit
=======
# Аудит тестовой системы BioETL
>>>>>>> master20260821-3

<<<<<<< HEAD
||||||| b48ac65c98
surface_score=2. Source `20260820T081148Z-tests-cycle-16c9a2b6e6`.
=======
- **domain_id:** `tests-system`
- **prompt_id:** `prompt.audit.tests-system`
- **AUDIT_MODE:** `full`
- **MODE:** `audit` (propose-patches listed, not applied)
- **LANGUAGE:** `ru`
- **BASE:** `main`
- **SCOPE:** `tests/` + `pyproject.toml` + `.github/workflows` (test gates only)
- **Дата:** 2026-08-21
- **surface_score:** `2` (acceptable: core regression machinery exists and CI blocks; e2e skip/retry and mutation-threshold drift remain)

## Executive summary

Тестовая система BioETL — зрелый pytest-контур регрессии, а не «coverage vanity». Канонические lane живут в `configs/quality/test_matrix.yaml` (ADR-042). PR реально блокирует: unit-fast / test-matrix / serial coverage-verify (`--fail-under=85` line + 85% branch), offline contract-confidence, e2e-smoke, architecture-fast (`import-linter.yml`), security, VCR preflight, mutation (partial). Live network по умолчанию выключен; VCR record mode по умолчанию `none`.

Материальные разрывы — не отсутствие suite, а **ослабление e2e-гейта** (3× rerun = pass-in-any, skip VCR mismatch, nightly fail-open) и **дрейф mutation threshold 44% vs SSOT 60%**. Эмпирический N-rerun локально не запускался (нет shell в этом агенте; anti-pattern «full-suite outside SCOPE»).

## Surface score

| Score | Meaning (domain card) | Выбор |
| --- | --- | --- |
| 3 | Critical paths covered; tests isolated/stable; CI actually blocks | нет: e2e skip/retry ослабляет merge-сигнал |
| **2** | Solid base; local gaps or limited observability | **да** |
| 1 | Material flaky/disabled zones, weak isolation, or optional CI | нет: unit/coverage/architecture-fast блокируют |
| 0 | Tests broken/absent on critical path, or green CI is fiction | нет |

Mapping: kit 0–3 control maturity. Не ставился на отдельные findings.

## Inventory (SCOPE)

### Уровни тестов

| Level | Path | PR gate | Notes |
| --- | --- | --- | --- |
| smoke | `tests/smoke/` | `tests.yml` `smoke-check` | `-m "not memory"` |
| unit-fast | `tests/unit/` minus scripts/repo_backed | `tests.yml` `test-fast` | xdist; excludes fs_contract/slow/memory |
| repo-backed / fs_contract / subprocess / scripts | dedicated jobs | `tests.yml` serial | coverage shards |
| unit matrix | domain/application/infrastructure/other | `tests.yml` `test-matrix` | Python **3.13 only** |
| integration | `tests/integration/` | test-matrix + consolidation-gates | VCR replay |
| security | `tests/security/` | test-matrix | |
| contract offline | `tests/contract/` + `tests/unit/contracts/` | `contract-confidence` | `-m "no_api or not network"` |
| contract live | `tests/contract/` | monthly `contract-tests.yml` | skip on HTTP errors |
| architecture-fast | `tests/architecture/` `-m "not slow"` | `import-linter.yml` `arch-tests` | |
| architecture-slow | full architecture | nightly `architecture.yml` only | not on PR |
| e2e-smoke | matrix smoke + chembl_activity | `e2e-matrix-health.yml` | 3× rerun |
| e2e control-plane | PubChem full cycle | `tests.yml` `control-plane-e2e` | LFS cassette |
| e2e-nightly-full | matrix live | schedule; **fail-open** | |
| memory | neo4j smoke | `memory-tests` | outside coverage |
| performance | `tests/performance/test_hotspot_budgets.py` | `performance-budgets` | own timers |
| benchmarks plugin | `tests/benchmarks/` | nightly without `-p benchmark` | skipped |
| mutation | domain + 3 application slices | `mutation-testing.yml` | domain 70%; app **44%** vs SSOT 60% |

Нет отдельного `pytest.ini` / `tox.ini`: конфиг в `pyproject.toml` `[tool.pytest.ini_options]`.

### Канонические команды (SSOT)

Локально (Windows): `.\.venv-win\Scripts\python.exe -m pytest …`  
Lane: `docs/00-project/ai/agents/guides/TEST_LANE_MENTAL_MODEL.md` и `docs/03-guides/testing.md`.

Default addopts: `-m "not benchmark and not slow"`, `-p no:benchmark`, serial (без xdist). CI явно включает xdist на parallel lanes.

Coverage SSOT: RULES §4.2 ≥85% line; `coverage-verify` также branch 85%. `fail_under` **не** в `[tool.coverage.report]` (чтобы шарды не падали).

## Checklist

- [x] Clean-checkout path documented (`docs/03-guides/testing.md`, test_matrix lanes)
- [x] Unit tests do not require network by default (no `pytest.mark.network` under `tests/unit/`)
- [x] Isolation: VCR `none`, frozen e2e time, `tmp_path`, session cwd pin; local serial default
- [x] Quarantine/skip owner+expiry: contract/integration inventoried; **e2e not in census**
- [x] No pytest `.only`; `--strict-markers`; no product `@pytest.mark.xfail`; no `*.disabled` modules
- [x] CI coverage fail-under only where project defines it (85%)
- [x] Retries not used as pytest-rerunfailures; **e2e 3× rerun still heals pass-in-any**
- [ ] Empirical flake N-rerun in this agent — **skipped** (no shell; not a full-suite run)

## Findings

См. `findings.json`. Кратко:

| ID | P | Status | Claim |
| --- | --- | --- | --- |
| TEST-001 | P2 | PROVEN | E2E 3× stability: pass in **any** rerun ⇒ not recurrent |
| TEST-002 | P2 | PROVEN | Skip-rate CI 23% + `--ignore-failures` vs SLO 15% advisory |
| TEST-003 | P2 | PROVEN | VCR mismatch in matrix smoke → `pytest.skip`, not fail |
| TEST-004 | P2 | PROVEN | Nightly live e2e fail-open (`exit 0`, skip-rate 100%) |
| TEST-005 | P2 | PROVEN | Mutation app gates 44% vs matrix/ADR-042 60% |
| TEST-006 | P2 | PROVEN | Composite + many ChEMBL entities deferred from PR e2e-smoke |
| TEST-007 | P3 | PROVEN | Skip inventory не сканирует `tests/e2e/` |
| TEST-008 | P3 | PROVEN | `tests/benchmarks/` в CI без `-p benchmark` → skip |
| TEST-009 | P3 | PROVEN | Local addopts hide `slow`; test-matrix Python 3.13 vs jobs 3.12; PR Linux-only |
| TEST-010 | P3 | PROVEN | Live contract skip on transport/5xx (inventoried; monthly can be green without API) |

P0/P1: **0**. Unsafe release через отсутствие unit/coverage/architecture-fast **не** доказан.

## Critical path → tests

| Product path | Tests | PR blocking? |
| --- | --- | --- |
| ChEMBL activity fetch→Gold | unit + integration + `test_chembl_activity_e2e` (`e2e_smoke`) | yes |
| Other CRITICAL_SMOKE_PIPELINES | matrix smoke | yes, but skip-on-mismatch |
| PubChem control-plane completeness | `test_pubchem_compound_full_cycle` | yes (LFS) |
| Composite pipelines | unit/integration; **deferred** from matrix smoke | no e2e-smoke |
| Determinism/idempotency | integration gates, skip-forbidden | yes (consolidation + test-matrix) |
| Schema/contracts | `tests/contract/` offline | yes |
| Live API drift | monthly live contracts | skip-tolerant |
| Secrets/VCR hygiene | security + vcr-preflight | yes |
| Layer boundaries | architecture-fast on PR | yes |

## Flaky / disabled

- Curated `configs/quality/flaky_test_inventory.yaml`: `reviewed_flaky_tests: []` (2026-08-03).
- No `pytest-rerunfailures` in `pyproject.toml`.
- No product `xfail`.
- `tests/architecture/test_no_disabled_test_modules.py` forbids `*.disabled`.
- E2E skip SLO `configs/quality/e2e_skip_rate_slo.yaml`: `mode: advisory`, `forbid_retries_to_heal_flakes: true` — **противоречит** 3× pass-any gate.

Empirical N-rerun this session: **not run**. CI `flaky-telemetry` repeats 3 seeds on a tiny subset (not proof of suite-wide stability).

## CI gates (test-related workflows)

Blocking on PR (workflow-level, if required):

- `.github/workflows/tests.yml` — smoke, VCR, unit lanes, coverage-verify, contract-confidence, control-plane-e2e, memory, performance-budgets, governance
- `.github/workflows/e2e-matrix-health.yml` — matrix-smoke-blocking
- `.github/workflows/import-linter.yml` — architecture-fast
- `.github/workflows/mutation-testing.yml` — path-filtered
- `.github/workflows/contract-tests.yml` — monthly live (fail-closed after `continue-on-error` diagnostics)
- `.github/workflows/consolidation-gates.yml` — subset architecture + contract + determinism

`architecture.yml` — schedule/dispatch only (not PR).

GitHub branch-protection required-check names: **не запрашивались** (`REQUIRE_GH_TRACKING=false`).

## Isolation / reproducibility

- VCR default `none` (`tests/conftest.py` session autouse).
- `before_record` sanitizes `authorization` / `x-api-key` / `cookie` (`tests/helpers/vcr_config.py`, `tests/conftest.py`).
- Cassette LFS fail-closed in vcr-preflight / control-plane-e2e.
- Hypothesis `HYPOTHESIS_PROFILE=ci` in Tests workflow.
- pytest `timeout = 60` default; e2e collection hook raises timeout.
- Local xdist forbidden globally; CI enables on named parallel lanes.

## Skipped checks

1. `python -m pytest` / N-rerun — нет shell tool; anti-pattern unbounded suite.
2. Memory `pre-task`/`post-task` — нет shell.
3. GitHub required checks / issues — `REQUIRE_GH_TRACKING=false`, `ALLOW_ISSUE_WRITE=false`.
4. `.env` не читался на предмет секретов в отчёте (guardrail: no .env edits).

## top_remediations (not applied)

1. Считать e2e-case нестабильным, если он не **passed во всех** N rerun (или оставить 3× только telemetry).
2. Выровнять CI skip-rate с SLO ≤15% и убрать `--ignore-failures` у blocking job.
3. В playback `INFRA_FLAKY_CASSETTE_MISMATCH` → fail для smoke matrix.
4. Nightly live: убрать `exit 0` / `max-skip-rate 1.0`; fail-closed.
5. `mutation-testing.yml` threshold = `test_matrix.yaml` `min_score` (60) **или** явно staged 44 без претензии «enforced 60».
6. Вынести composite/deferred entity e2e в blocking lane либо skip с owner+expiry.
7. Расширить `test_skip_inventory` на `tests/e2e/`.
8. Performance nightly: `-p benchmark -p no:xdist` как в комментарии `pyproject.toml`.

## Kit extras

- `test-matrix.csv`
- `coverage-evidence.json`
- `flaky-tests.csv`
- `disabled-tests.csv`
- `critical-gap-map.md`

## Debt / secrets

- Долговые бюджеты не менялись.
- Секреты в отчёт не включались.
- Код не патчился.
>>>>>>> master20260821-3
