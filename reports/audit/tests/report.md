# Tests system audit (read-only)

| Поле | Значение |
| --- | --- |
| `domain_id` | `tests-system` |
| `prompt_id` | `prompt.audit.tests-system` v1.2.0 |
| `mode` | `audit` / `AUDIT_MODE=full` |
| `scope` | `tests/`, `configs/quality/` |
| `read_root` | `.worktrees/nine-domain-audit-9f71c6444175` @ `e1c184857e46` |
| `language` | `ru` |
| `surface_score` | **2** |
| `audit_date` | 2026-09-26 |

## Executive summary

Тестовая система BioETL — **regression-detection платформа**, а не vanity coverage: pytest + lanes из `test_matrix.yaml`, ~2935 `test_*.py`, 530 architecture-guards, inventory skip/VCR/flaky, CI `test-matrix` + `coverage-verify` (85%). Детерминизм усилен (`strict-markers`, `filterwarnings=error`, timeout 60s, запрет pytest-rerun для лечения flake в e2e SLO).

**P1 (2):** GitHub ruleset `pr-gate-complete` **отключён** (каталог checks advisory, #11180); полный offline E2E (`e2e-nightly-full`) **не на PR** при MUST e2e для composition/interfaces — merge опирается на unit/integration/architecture + advisory e2e-smoke satellite.

**P2:** узкая flaky-телеметрия (N=3, два файла); Windows/WSL architecture skips (#10418); prompt-tests только nightly; большой объём `pytest.skip(` vs декораторы.

**Сильные стороны:** `unit_unconditional_skips: []`, markerless budget 0, guard `*.disabled`, integration VCR policy, live contract opt-in, memory lane изолирован от coverage.

Полный pytest suite **не запускался** (read-only / time budget). Выводы — inspection + rg/count по worktree.

## Метод

| Шаг | Действие |
| --- | --- |
| Config | `pyproject.toml`, `configs/quality/test_matrix.yaml`, `github_required_checks.yaml`, skip/flaky/VCR/e2e SLO YAML |
| Inventory | rg `@pytest.mark.skip`, `pytest.skip(`, `xfail`; подсчёт `test_*.py` |
| CI map | `.github/workflows/tests.yml` (test-matrix, coverage-verify, flaky-telemetry, memory-tests) |
| Lanes | ADR-042 matrix: unit-fast, integration-replay, contracts, architecture, e2e-* |

## Surface score

| Score | Обоснование |
| ---: | --- |
| **2** | Критичные product paths покрыты unit/integration/contract/architecture + CI shards; merge-truth на Linux CI. Cap 3 снят из‑за P1 (ruleset advisory, PR без full E2E replay) и ограниченной flaky observability. |

## Top remediations

1. После #11180 — восстановить enforcement ruleset 13643213 или явный операторский merge blocker.
2. Держать `e2e-matrix-health.yml` matrix-smoke-blocking; nightly `e2e-nightly-full-replay` как release confidence.
3. Не расширять flaky shard без owner/minutes; пустой `flaky_test_inventory` ≠ «нет flake».
4. Windows: `architecture-fast-boundary`, merge — CI Linux.
5. Slim-кампания для 4 allowlist VCR >10 MiB.

## Ограничения

- `full_suite_ran: false` — без unbounded pytest по AGENTS.md / prompt Stop.
- Flaky **не** помечены repeat-run в этой сессии (нет N-rerun evidence).

## Machine output

`findings.json` — 18 findings, max 20, PROVEN-preferred.
