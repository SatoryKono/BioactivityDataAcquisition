---
id: prompt.audit.cycle.architecture
version: 1.1.0
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
  - Drive-by refactors outside SCOPE
  - Raising debt budgets to pass review
  - Findings without path-level evidence
  - Huge code-level diagram of the entire repo
  - C4 container assumed to mean Docker
  - Mass layer moves without a migration plan
  - Inventing category scores without evidence commands
  - Scoring categories not in the 10-category table
  - Empty form cycles
tags: [architecture, audit, cycle, scorecard, hexagonal, operator]
summary: Cyclic architecture audit — 10-category scorecard, plan, implement waves
max_body_lines: 280
---

# Cyclic project-architecture audit

N-итерационный аудит **общей архитектуры**: оценить по 10 категориям →
план улучшений → debt-safe waves → re-verify.

| Layer | Source |
| --- | --- |
| Domain method | `prompt.architecture.review` (hexagonal / C4 / arc42) |
| Scorecard SSOT | `reports/quality/architecture-quality-scorecard.json` |
| Loop shell | `prompt.audit.orchestrator` |

Default **`N=10`**, **`MODE=full`**, **`INCLUDE_PIPELINE=true`**,
**`LAYERS=all`**, **`SCORE_SOURCE=live+committed`**, все **`ALLOW_*=true`**.
Пустые циклы запрещены. Early-stop: 2 подряд итерации без новых PROVEN P0/P1
и без падения `integral_score`. **УВЕЛИЧИВАТЬ бюджеты техдолга ЗАПРЕЩЕНО.**

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
| `ALLOW_ISSUE_WRITE` | `true` |
| `ALLOW_PUSH` | `true` |
| `ALLOW_MERGE` | `true` |
| `ALLOW_CLOSE` | `true` |
| `MAX_ISSUES_PER_ITERATION` | `5` |
| `MAX_WAVES_PER_ITERATION` | `3` |
| `BASE_BRANCH` | `main` |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `WORK_BRANCH` | `fix/architecture-audit-cycle-<shortsha>` |

## BioETL anchors

- Requirements: `docs/01-requirements/REQUIREMENTS.md` + traceability CSV; PROVEN findings need `requirement_id`
- Hexagonal / layers: `RULES.md` §1; ADR-005, ADR-048
- Medallion: ADR-002; DQ ADR-027 / ADR-045
- Local-only default: ADR-010
- Determinism: ADR-014; observability ports ADR-006 / ADR-017 / ADR-019
- Index: `docs/00-project/architecture-index.md`
- Tests: `tests/architecture/`; import-linter: `.importlinter`
- Refresh when available: `python -m scripts.engineering.qa report-architecture-quality-scorecard`
- Windows: `.\.venv-win\Scripts\python.exe`

## 10 categories (canonical scorecard)

Оценивать **ровно эти 10** id. Score **0.0–10.0** (выше = лучше).

| # | `category_id` | Name | Primary evidence |
| --- | --- | --- | --- |
| 1 | `layer_compliance` | Слои | `.importlinter`, dep-map, forbidden imports |
| 2 | `hexagonal_ports_adapters` | Ports & adapters | `domain/ports`, adapters vs ports |
| 3 | `ddd_invariants` | DDD / aggregates | domain purity, identity |
| 4 | `composition_di` | Composition / DI | factories; no service locator outside composition |
| 5 | `module_boundaries_coupling` | Coupling | hotspots, fan-in, duplication |
| 6 | `naming_package_consistency` | Naming | `*Port` / `*Service` / `*Adapter` |
| 7 | `test_strategy_testability` | Testability | architecture tests, coverage inventory |
| 8 | `config_contracts_entrypoints` | Config / contracts | contracts, public entrypoints |
| 9 | `determinism_replay_observability` | Determinism / obs | ADR-014, metrics/traces ports |
| 10 | `debt_burden_evolution_friction` | Долг / friction | debt gates, residual non-growth |

`surface_score` 0–3 from integral: ≥9.0 → 3; ≥7.5 → 2; ≥5.0 → 1; else 0.
Cap at 1 if any P0 open; at 2 if any P1 open. Tag findings `category=<id>`.

## Preflight

1. `git status --porcelain`; SHA; branch; `gh auth status` (no tokens).
2. Dirty foreign work → worktree. Empty SCOPE → STOP.
3. `run_id = <UTC>-arch-cycle-<shortsha>`
4. Copy committed scorecard → `baseline-scorecard.json` under the run dir.
5. Artifacts: `reports/audit-runs/<run_id>/` + mirror `reports/audit/architecture/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Restore** | C4 context/container (container ≠ Docker). Dep graph for SCOPE. |
| **B Score** | Fill `scorecard.json`: per-category score, weight, evidence, delta vs baseline. Compute `integral_score` + `surface_score`. |
| **C Boundaries** | Import direction; cycles; injection; runtime min scenarios (startup, pipeline run, failure/retry). |
| **D ADR drift** | ADR/diagram claim → path. Differential vs `origin/BASE_BRANCH` if set. |
| **E Findings** | PROVEN-only `findings.json`; map to categories; P0–P3. |
| **F Plan** | `plan.json` waves ≤ MAX_WAVES. Each wave: goal, category_ids, files, risk, test plan, debt effect (↓ or flat), acceptance, rollback. |
| **G Issues** | Create if ALLOW_ISSUE_WRITE + PROVEN + `requirement_id`. Title `[architecture][<REQ-id>][P#]`. One issue per root-cause. |
| **H Implement** | WORK_BRANCH; minimal diffs; no drive-by; no mass layer moves without a migration plan. |
| **I Validate** | import-linter / architecture subset; re-score touched categories; PR if ALLOW_PUSH. |
| **J Post** | resolved \| unchanged \| regressed \| new. Score delta table. |

`MODE=audit` stops after E. `audit+plan` after F. `full` through J.

## Focus checklist (each cycle)

- [ ] All 10 categories scored with evidence
- [ ] `integral_score` + `surface_score` recorded
- [ ] No unlisted `interfaces→infrastructure` imports
- [ ] Plan waves debt-neutral or debt-reducing only
- [ ] ADR-010: no new mandatory Docker/Redis for local default
- [ ] Determinism / architecture gates not weakened
- [ ] Implementation only from plan waves
- [ ] No whole-repo code-level diagram dump

## Stop

Empty SCOPE; whole-repo code diagram; P0 “fixed” by raising budgets;
mass layer moves without an approved migration plan; invented scores;
orchestrator hard-stop.

## Success

- 10-category `scorecard.json` + findings + plan under the run dir
- Waves implemented under ALLOW_* or explicitly deferred
- No unexplained category regression
- `final-summary.md` after N or early-stop

## Related

- One-shot: `prompt.architecture.review`
- Adjacent residual: `prompt.audit.cycle.tech-debt`
- Dual-agent: `prompt.audit.dual-agent-cycle` +
  `AUDIT_PROMPT_SOURCE=prompt.architecture.cycle`
- Closeout: `prompt.closeout.grok`
- Previous: `prompt.audit.cycle.tech-debt` · Next: `prompt.audit.cycle.telemetry`
