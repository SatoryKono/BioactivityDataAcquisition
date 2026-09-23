# Technical debt audit — `src`

| Field | Value |
| --- | --- |
| Date | 2026-09-23 |
| Ref | `origin/main` `670633e6ec68` |
| SCOPE | `src` (`bioetl` + `memory`) |
| MODE | `propose-patches` |
| AUDIT_MODE | `full` |
| surface_score | **2** (ядро под контролем; god-module и drift gates) |

## Executive

Measured debt, не raw markers: **0** TODO/FIXME/HACK в `src/bioetl` (8 raw hits = TEMP/CVCL_XXXX/ADR-XXX/DEPRECATED enum).

Тренд лучше 2026-08-28: exemptions 48→0, integral 9.47→10.0, composition 291→280/295. Бюджеты не предлагаются к росту.

Два блокирующих факта на текущем `origin/main`:

1. **AUD-001 P1** — scorecard hash `ce0ac31` ≠ inventory `0db51a46` после #10630; gates `module_coverage_scorecard_coherence` + `generated_artifact_drift`.
2. **AUD-002 P1** — `src/memory/graph/sync_pkg/_core.py` = **17740** LOC; #10526 закрыт без acceptance.

## Trend vs registries

| Signal | Historical | Now | Direction |
| --- | --- | --- | --- |
| `debt_scorecard` exemptions | 48 (2025-Q4) | 0 | improved |
| Architecture integral | 9.47 | 10.0 (artifact) | improved / proxy |
| Composition modules | 291/295 | 280/295 util 0.9492 | improved, near cap |
| God-module `_core.py` | 18179 (#10526) | 17740 | unchanged material |
| Hotspot families `files_ge_250_loc` | 0 budget | 0 observed | held |
| Uncovered/unmeasured bioetl | 0/0 | 0/0 | held |
| Partially covered | — | 10 | residual test debt |
| Constructor waivers | 2 | 1 (`QuarantineEntry`, expiry 2026-12-31) | shrink-only |

## Marker / suppression triage

| Class | Raw | Measured debt |
| --- | --- | --- |
| TODO/FIXME/HACK | 0 in bioetl | none |
| XXX/TEMP/DEPRECATED grep | 8 | 0 (FP: TEMP type, CVCL_XXXX, ADR-XXX, enum) |
| `pragma: no cover` | ~25 | mostly `__getattr__` facades; do not remove |
| `type: ignore` | ~20 bioetl | AUD-005 P3 mixin/override seams |
| `# nosec` | pubmed XML / delta / tracing | keep; Bandit seams |

`coverage.xml` в этом checkout отсутствует — pragma не сверялся с EXCLUDED vs executed. Снимать exclusion без теста запрещено.

## Findings (risk order)

| ID | P | Status | Claim |
| --- | --- | --- | --- |
| AUD-001 | P1 | PROVEN | Scorecard/inventory SHA desync, gates fail on main |
| AUD-002 | P1 | PROVEN | God-module 17740 LOC; #10526 acceptance unmet |
| AUD-003 | P2 | PROVEN watch | composition 280/295, util 0.9492 ≤ 0.95 |
| AUD-004 | P2 | PROVEN | 10 partial modules; FK tail &lt;80% |
| AUD-005 | P3 | PROVEN | `type: ignore` vs `cast()` at mixins |

Не issue: domain/aggregates 8/8 hold-flat (#10552); config duplicate_cluster_count=6 — зеркала INV-CFG-009, не drift; `no_executable_lines` re-export `domain/exceptions/infrastructure`.

## Top-20 (probability × blast)

1. AUD-001 — CI/release gate на каждом PR после #10630.
2. AUD-002 — любой memory-graph change = конфликт на 17k файле.
3. FK reconciliation partial (AUD-004) — Gold FK write path.
4. composition headroom 15 (AUD-003) — feature-block если добавить модуль.
5–10. Остальные 7 partial modules (1–6 missing lines).
11–20. type: ignore mixin seams, constructor waiver, `__getattr__` pragmas, CLI 410 LOC files outside hotspot families (inventory, не exemption).

## Quick wins vs strategic vs dependency

| Bucket | Item | Effort |
| --- | --- | --- |
| Quick win | AUD-001 rebind scorecard + remote-main baseline | S |
| Quick win | Sync comment `live 279` → `280` in `package_cohesion_budget.yaml` | S |
| Test debt | Unit tests on FK reconciliation missing lines | M |
| Strategic | Split `_core.py` &lt;500 LOC packages | XL |
| Watch | composition shrink-before-add | — |
| Dependency | radon untyped import; no obsolete runtime dep found in this pass | — |

## Proposed patches (MODE=propose-patches)

См. `proposed-patches.md`. Применяется в этой ветке только AUD-001 rebind (budget-neutral). Split `_core.py` и coverage-тесты — отдельные PR, бюджеты не трогать.

## GH tracking

| Finding | Action |
| --- | --- |
| AUD-001 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10632 |
| AUD-002 | reopen https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10526 |
| AUD-003 | no issue (cap holds) |
| AUD-004 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10631 |
| AUD-005 | no issue (P3 local) |

## Checks

Run:

- `python -m scripts.engineering.qa report-debt-governance-gates --check --changed-from-ref origin/main` → exit 1 (AUD-001)
- marker scan `src/bioetl` TODO/FIXME/HACK → 0
- inventory summary: 2478 modules, 2467 full, 10 partial, 1 no_exec

Skipped: live `coverage.xml` pragma EXCLUDED map; `mypy --strict` full tree; xenon on `_core.py`; Sonar.

Mirror-sync: N/A (no `.codex`/`.junie` edits).
`.env` not touched. Debt budgets not raised.
