---
id: prompt.audit.project.new.architecture
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, codex, any]
params:
  - N
  - SCOPE
  - MODE
  - LANGUAGE
  - AUDIT_MODE
  - INCLUDE_PIPELINE
  - LAYERS
  - SCORE_SOURCE
  - ALLOW_ISSUE_WRITE
  - ALLOW_PUSH
  - ALLOW_MERGE
  - ALLOW_CLOSE
  - MAX_ISSUES_PER_ITERATION
  - MAX_WAVES_PER_ITERATION
  - BASE_BRANCH
  - REPO
  - WORK_BRANCH
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
  - fragments/audit-scale.md
  - fragments/finding-schema.md
  - fragments/project-requirements-audit.md
  - fragments/unknown-params.md
  - fragments/reports-output.md
  - fragments/shell-portability.md
  - fragments/orchestrator-guards.md
related_ssot:
  - AGENTS.md
  - docs/00-project/RULES.md
  - docs/00-project/NORMATIVE_SOURCES.md
  - docs/01-requirements/REQUIREMENTS.md
  - docs/01-requirements/traceability/requirements-traceability-crosswalk.csv
  - docs/00-project/architecture-index.md
  - docs/02-architecture/decisions
  - reports/quality/architecture-quality-scorecard.json
  - configs/quality/debt_scorecard.yaml
  - docs/00-project/ai/prompts/library/architecture/review-assessment.md
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
  - docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md
anti_patterns:
  - Inventing REQ-* IDs not in REQUIREMENTS.md / the traceability CSV
  - Scoring categories not in the 10-category table
  - Inventing category scores without evidence commands
  - Raising debt budgets to pass review
  - Drive-by refactors outside SCOPE
  - Mass layer moves without a migration plan
  - C4 container assumed to mean Docker
  - Empty form cycles
  - ALLOW_* true by library default
tags: [architecture, audit, cycle, scorecard, hexagonal, operator]
summary: Improved cyclic architecture audit — 10-category scorecard, plan waves, fail-closed ALLOW, early-stop
max_body_lines: 260
---

# Improved cyclic architecture audit

Улучшает `prompt.architecture.cycle` + `prompt.audit.cycle.architecture`.
Domain method: `prompt.architecture.review`. Scorecard SSOT:
`reports/quality/architecture-quality-scorecard.json`. Loop:
`prompt.audit.orchestrator`.

Library defaults: **`ALLOW_*=false`**. Пустые циклы запрещены.
**УВЕЛИЧИВАТЬ бюджеты техдолга ЗАПРЕЩЕНО.**

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `src/bioetl/ tests/architecture/` |
| `MODE` | `full` (`audit` \| `audit+plan` \| `audit+issues` \| `full`) |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` \| `differential` |
| `INCLUDE_PIPELINE` | `true` |
| `LAYERS` | `all` |
| `SCORE_SOURCE` | `live+committed` |
| `ALLOW_ISSUE_WRITE` | `false` |
| `ALLOW_PUSH` | `false` |
| `ALLOW_MERGE` | `false` |
| `ALLOW_CLOSE` | `false` |
| `MAX_ISSUES_PER_ITERATION` | `5` |
| `MAX_WAVES_PER_ITERATION` | `3` |
| `BASE_BRANCH` | `main` |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `WORK_BRANCH` | `fix/architecture-cycle-new-<shortsha>` |

## 10 categories (canonical ids)

`layer_compliance` · `hexagonal_ports_adapters` · `ddd_invariants` ·
`composition_di` · `module_boundaries_coupling` · `naming_package_consistency` ·
`test_strategy_testability` · `config_contracts_entrypoints` ·
`determinism_replay_observability` · `debt_burden_evolution_friction`

Score 0.0–10.0 with evidence commands. Do not add an 11th id without ADR.
Tag findings `category=<category_id>`. PROVEN MUST have `requirement_id`.

## Preflight

1. `git status --porcelain`; SHA. Чужой dirty → worktree.
2. Copy committed scorecard → `baseline-scorecard.json`.
3. `run_id = <UTC>-arch-new-<shortsha>`. Marker: `Cycle-run: <run_id>`.
4. Artifacts: `reports/audit-runs/<run_id>/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Map** | C4 context/container (container ≠ Docker). Dep graph for SCOPE. |
| **B Score** | Fill `scorecard.json` for all 10 ids; `integral_score`; `surface_score` (0–3). |
| **C Plan** | `plan.json` waves ≤ MAX_WAVES. Debt effect ↓ or flat. Acceptance + rollback. |
| **D Issues** | ALLOW_ISSUE_WRITE + PROVEN + `requirement_id`. Title `[arch][<REQ-id>][P#]`. |
| **E Implement** | Only plan waves on WORK_BRANCH. No mass layer moves without migration plan. |
| **F Validate** | `lint-imports` / architecture subset; re-score touched categories. Close only on `origin/main` if ALLOW_CLOSE. |

`MODE=audit` after B. `audit+plan` after C. `audit+issues` after D. `full` through F.

If `INCLUDE_PIPELINE=true`: audit arch CI + import-linter wiring; tag `pipeline`.

## Early-stop

`new_issues_i == 0` **и** `open_cycle_issues == 0` → STOP.
Два подряд цикла без новых PROVEN P0/P1 и без падения `integral_score` → STOP.

## Success

- 10-row score table every iteration
- No unexplained category regression
- ADR-010: no new mandatory Docker/Redis for local default
