# Cyclic test-layer audit — 20260826T092749Z-tests-cycle-1e64aaac80

**Gate:** WARN
**surface_score:** 2 (acceptable) — core regression-detection mechanism present; snapshot drift was real and is regenerated; residual LOC growth is correctly fail-closed and out of SCOPE.
**SHA:** `1e64aaac80adca6b304fe2912d6cd18c8a37d027`
**Work branch:** `fix/audit-cycle-tests-seq-20260826` (requested `fix/audit-cycle-tests` locked in another worktree)
**Params:** N=10 MODE=full LANE=unit ALLOW_ISSUE_WRITE=true ALLOW_PUSH=true ALLOW_MERGE=false LANGUAGE=ru
**Debt outcome:** unchanged (no budget/skip/xfail increase)

## Executive summary

Тестовый слой BioETL на `1e64aaac80` — зрелая система: named lanes в `configs/quality/test_matrix.yaml`, skip-census 24/24, пустой flaky inventory, VCR before_record hooks, monthly contract workflow, CI unit-fast + coverage-verify 85%.

**PROVEN finding TEST-GOV-001 (P2, REQ-GOV-012):** committed `reports/quality/test-governance-current.json` расходился с live collector (`total_test_functions` 25006->25010, `source_tree_sha256` 899962f4...->b77152e5...). Бюджеты skip/xfail/debt не затронуты. Снимок перегенерирован канонической командой; `--check` x3 = 0; focused architecture test зелёный.

**PROVEN related TEST-RES-001 (P2, REQ-GOV-012):** `report_live_residual_snapshot --check` падает на росте `composition_factories_pipeline.total_loc` 3970->3983. Это корректный fail-closed residual-гейта, не дефект тестового слоя. Чинить `src/bioetl` / поднимать freeze запрещено в этом SCOPE. Связь: open epic #9639. Issue на bump snapshot не открывался.

GitHub issue_write заблокирован хостом (auto-mode). Payload: `issues.jsonl`. Номера issues не созданы.

`.venv-win` отсутствует в этом worktree (локальный env). Канонический runner `run_pytest.ps1` предпочитает `.venv-win`. Проверки выполнены через PYTHONPATH=src + системный Python 3.13.7 / pytest 8.4.2 (проект требует pytest>=9.0.3 — focused test всё же прошёл). Это NOT_PROVEN как дефект репозитория: `scripts/engineering/dev/setup_env_windows.ps1` существует.

## Focus checklist

- [x] Clean-checkout entry: `run_pytest.ps1` / `.venv-win` documented; local `.venv-win` missing (env)
- [x] Unit default has no mandatory external network (no pytest.mark.network under tests/unit)
- [x] Isolation: tmp/cache via runner; clock/ID seams governed
- [x] Quarantine/skip has owner + linked issue (24 entries, all @bioetl-* + #NNNN)
- [x] Flaky claims: none suspected; `--check` N=3 all pass (not a flake)
- [x] CI required checks mapped: tests.yml unit-fast, coverage-verify
- [x] test-governance-current.json regenerated (was drifted)
- [x] Skip/xfail/debt budgets unchanged

## REQ-TEST / REQ-GOV mapping

| ID | Result |
| --- | --- |
| REQ-TEST-001 / 002 | Architecture/unit mock policy present; no patch(httpx/requests/aiohttp) in tests/unit |
| REQ-TEST-003 | tests/fixtures/vcr/ present (356 yaml) |
| REQ-TEST-004 | tests/helpers/vcr_config.py before_record_request / before_record_response |
| REQ-TEST-005 | .github/workflows/tests.yml pytest lanes |
| REQ-TEST-006 | .github/workflows/contract-tests.yml schedule cron 0 2 1 * * |
| REQ-GOV-012 | Snapshot --check was red, now green after regen; residual --check still red on product LOC (out of SCOPE) |

## Issues

| Finding | GitHub | Status |
| --- | --- | --- |
| TEST-GOV-001 | not created (host blocked issue_write) | payload in issues.jsonl |
| TEST-RES-001 | do not open (gate working; #9639) | documented only |

## Validation

```text
python -m scripts.engineering.qa.report_test_governance_audit --check   # exit 0 x3
python -m pytest tests/architecture/test_test_governance_audit.py::test_test_governance_artifacts_match_live_collector
# passed
python -m scripts.engineering.qa.report_live_residual_snapshot --check
# exit 1 residual growth composition_factories_pipeline.total_loc 3970->3983
```

## Skipped checks

- Full unit-fast / architecture-full suite (LANE=unit budget; architecture-full already tracked #9639)
- `.venv-win` bootstrap / uv sync (heavy; not required to prove snapshot drift)
- MONITORING docker-compose.monitoring.yml not started (not dashboard work)
- GitHub issue create / close (host blocked)
- Merge to main (ALLOW_MERGE=false)

## Debt

unchanged — no skip/xfail/debt budget edits.
