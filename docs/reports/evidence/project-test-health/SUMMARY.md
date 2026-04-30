---
status: active-non-canonical
last_verified: "2026-04-30"
freshness_window_days: 90
owner: quality
canonical_sources:
  - configs/quality/test_matrix.yaml
  - configs/quality/test_health_reporting.yaml
  - configs/quality/fixture_governance_ledger.yaml
  - .github/workflows/tests.yml
stale_action: refresh evidence pack or mark as historical non-normative before using for governance decisions
---

# Сбор evidence завершён: project-test-health

Дата: 2026-03-23
Статус: актуализировано под текущий verify baseline

Review note (2026-03-27): included in the repo-wide evidence-pack sweep; see `docs/reports/evidence/project-evidence-rebaseline/06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md` for wave status, retained-vs-reopened interpretation, and current review scope.

> Этот summary — repo-only evidence layer для test-health решений.
> Для canonical test policy и active runtime expectations приоритет остаётся у
> `configs/quality/test_matrix.yaml`, `configs/quality/test_health_reporting.yaml`
> и active guides under `docs/03-guides/`.

Freshness note (2026-04-29): this evidence summary is non-canonical and must not
override active policy in `configs/quality/test_matrix.yaml`,
`configs/quality/test_health_reporting.yaml`, `configs/quality/fixture_governance_ledger.yaml`,
or current CI workflow definitions. Treat the "Оставшиеся пробелы" section as a
backlog signal only until a fresh evidence-pack rebaseline or a machine-readable
policy update confirms the finding.
Machine-readable metadata for this non-canonical summary now lives in
`docs/reports/evidence/project-test-health/metadata.yaml`, and shard status is
tracked in `docs/reports/evidence/project-test-health/shard_registry.yaml`.

Примечание о rebaseline: после `RF-011` текущий confidence baseline подтверждён
полным verify bundle: `pytest tests -q`, секторные прогоны `tests/architecture`
и `tests/unit`, а также `ruff`, `mypy`, dependency-map `--check` и
compatibility-snapshot `--check` зелёные на актуальном дереве.

## Статус shard-ов

| Shard                              | Evidence Objects | Gate   |
| ---------------------------------- | ---------------: | ------ |
| `failure-stability`                |                8 | PASSED |
| `coverage-governance`              |                9 | PASSED |
| `semanticscholar-pilot-options`    |                6 | PASSED |
| `semanticscholar-enforced-options` |                6 | PASSED |
| `flaky-rate`                       |                1 | PASSED |
| `uncovered-module-risk-map`        |                1 | PASSED |
| `semanticscholar-environment-limited-frequency` |    1 | PASSED |
| `environment-limited-threshold`    |                1 | PASSED |

## Главные выводы

- BioETL already invests heavily in test survivability: default timeouts, local serial defaults, resilient CI fallback, and network gating are all explicit parts of the test system.
- The suite is structurally skip-heavy and condition-heavy rather than uniformly hard-failing; this is especially visible in architecture and live-contract paths.
- Coverage policy is explicit, but enforcement depth is uneven: overall thresholding is centralized in one CI job, mutation testing is only partially enforced, and VCR freshness governance is still staged.
- Provider live coverage is now baseline-enforced across all seven providers in the current matrix; `semanticscholar` no longer remains a baseline `pilot`, while the richer Semantic Scholar soak path stays opt-in outside the enforced core baseline.
- Semantic Scholar now has two explicit follow-on evidence layers: one records the historical pre-promotion pilot decision, and the newer one records the post-promotion choice to keep the enforced core baseline while monitoring residual `429` behavior.
- The project now encodes conditional confidence explicitly via machine-readable `fully_exercised_green`, `staged_green`, and `environment_limited_green` reporting classes.
- Skip-conditioned confidence is now also bucketed into canonical categories, which makes report refresh and evidence tracking more repeatable.
- The test tree is large (`994` test files) and dominated by unit plus architecture coverage, with topology itself enforced as a governance surface.
- Текущий baseline больше не держится только на секторных smoke-подтверждениях: после `RF-011` полный verify bundle снова подтверждён на актуальном дереве, так что главный residual risk смещается от broad correctness к future flakiness/order sensitivity monitoring.

## Закрытые follow-up gaps

- `flaky-rate` now defines the retained telemetry source and explicit
  unavailable-data behavior for missing historical CI artifacts.
- `uncovered-module-risk-map` maps weak confidence surfaces to structural
  risk/refactor priorities through `configs/quality/test_structural_watchlist_map.yaml`.
- `semanticscholar-environment-limited-frequency` now has a scheduled,
  non-blocking repeated-run tracking path through retained test-health summaries.
- `environment-limited-threshold` defines a numerical acceptance threshold in
  `configs/quality/environment_limited_green_policy.yaml`.
