---
id: prompt.architecture.cycle
version: 1.1.0
status: active
class: operator-paste
owner: BioETL Team
runtimes:
- grok
- codex
- any
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
- fragments/git-safety.md
- fragments/debt-budget-ban.md
- fragments/env-guardrail.md
- fragments/evidence-contract-v3.md
- fragments/language-ru.md
- fragments/audit-scale.md
- fragments/finding-schema.md
- fragments/orchestrator-guards.md
- fragments/cyclic-kernel-v3.md
related_ssot:
- AGENTS.md
- docs/00-project/RULES.md
- docs/00-project/NORMATIVE_SOURCES.md
- docs/00-project/architecture-index.md
- docs/02-architecture/decisions/
- reports/quality/architecture-quality-scorecard.json
- configs/quality/debt_scorecard.yaml
- docs/00-project/ai/prompts/library/audit/orchestrator.md
- docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md
anti_patterns:
- Drive-by refactors outside SCOPE
- Raising debt budgets to pass review
- Findings without path-level evidence
- Huge code-level diagram of entire repo
- C4 container assumed to mean Docker
- Empty form cycles
- Mass layer moves without migration plan
- Inventing category scores without evidence commands
- Scoring categories not in the 10-category table
tags:
- architecture
- audit
- cycle
- scorecard
- hexagonal
- plan
- implement
- operator
summary: Cyclic architecture audit — 10-category scorecard, improvement plan, implement
  waves, re-verify
max_body_lines: 240
---
# Cyclic project architecture audit (10 categories → plan → implement)

N-итерационный цикл: **оценить архитектуру по 10 категориям** → **сформировать
план улучшений** → **реализовать** debt-safe waves → re-verify.

| Layer | Source |
| --- | --- |
| Domain method | `prompt.architecture.review` (hexagonal / C4 / arc42) |
| Scorecard SSOT | `reports/quality/architecture-quality-scorecard.json` (10 categories) |
| Loop shell | `prompt.audit.orchestrator` |

Default **`N=10`**, **`MODE=full`**, **`INCLUDE_PIPELINE=true`**,
**`LAYERS=all`**, **`SCORE_SOURCE=live+committed`**, все **`ALLOW_*=true`**.

Operator **full-run** paste must set `ALLOW_ISSUE_WRITE/PUSH/MERGE/CLOSE=true`
explicitly before Phases G–I mutate GitHub/git. Without flags → plan/payloads only.

Пустые циклы запрещены. Early-stop: 2 подряд итерации без новых actionable
PROVEN P0/P1, без regression и без падения `integral_score` / category scores.

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `src/bioetl/` (+ `tests/architecture`, configs, compose as needed) |
| `MODE` | `full` (`audit` \| `audit+plan` \| `audit+issues` \| `full`) |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` \| `differential` |
| `INCLUDE_PIPELINE` | `true` (arch CI, import-linter, architecture tests) |
| `LAYERS` | `all` or CSV of hexagonal layers |
| `SCORE_SOURCE` | `live+committed` \| `committed` \| `live` |
| `ALLOW_ISSUE_WRITE` | `false` (operator full-run: `true`) |
| `ALLOW_PUSH` | `false` (operator full-run: `true`) |
| `ALLOW_MERGE` | `false` (operator full-run: `true`) |
| `ALLOW_CLOSE` | `false` (operator full-run: `true`) |
| `MAX_ISSUES_PER_ITERATION` | `5` |
| `MAX_WAVES_PER_ITERATION` | `3` |
| `BASE_BRANCH` | `main` |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `WORK_BRANCH` | `fix/architecture-audit-cycle-<shortsha>` |

## BioETL anchors (read, do not reinvent)

- Hexagonal / layers: `RULES.md` §1; **ADR-005** composition
- Medallion: ADR-002 / RULES §2; DQ ADR-027/045 (if SCOPE touches)
- Local-only default: **ADR-010**
- Determinism: ADR-014; observability ports ADR-006/017/019
- Index: `docs/00-project/architecture-index.md`
- Generated dep map: `docs/02-architecture/generated/module-dependency-map.*`
- Architecture tests: `tests/architecture/`
- Machine scorecard: `reports/quality/architecture-quality-scorecard.json`
- Refresh (when available): `python -m scripts.engineering.qa report-architecture-quality-scorecard` or project equivalent
- import-linter: `.importlinter` + `lint-imports`

## 10 categories (canonical scorecard)

Оценивать **ровно эти 10** id (совпадают со scorecard). Score **0.0–10.0**
(выше = лучше). Не добавлять 11-ю категорию без ADR.

| # | `category_id` | Name (RU) | Primary evidence |
| --- | --- | --- | --- |
| 1 | `layer_compliance` | Соответствие слоям | `.importlinter`, dep-map, forbidden imports |
| 2 | `hexagonal_ports_adapters` | Hexagonal / ports & adapters | `domain/ports`, adapters vs ports, ADR-005/048 |
| 3 | `ddd_invariants` | DDD / aggregates / invariants | aggregates, domain purity, identity |
| 4 | `composition_di` | Composition root / DI | factories, no service locator outside composition |
| 5 | `module_boundaries_coupling` | Границы модулей / coupling | hotspots, fan-in, duplication clusters |
| 6 | `naming_package_consistency` | Naming / packaging | twin pairs, `*Port`/`*Service`/`*Adapter` |
| 7 | `test_strategy_testability` | Тест-стратегия / testability | architecture tests, coverage inventory |
| 8 | `config_contracts_entrypoints` | Config / contracts / entrypoints | contracts, public entrypoints freeze |
| 9 | `determinism_replay_observability` | Determinism / replay / observability | ADR-014, control-plane, metrics/traces ports |
| 10 | `debt_burden_evolution_friction` | Долг / friction эволюции | debt gates, compat debt, residual non-growth |

### Scoring rules

1. **Baseline first:** read committed scorecard if present (`SCORE_SOURCE` includes
   `committed`). Record `integral_score` + per-category scores/weights.
2. **Live re-check:** for each category, run evidence commands (import-linter,
   architecture tests subset, inventories). Adjust score only with PROVEN delta
   vs baseline (or justify “unchanged”).
3. **Integral:** prefer scorecard formula (weighted sum). If live-only, use same
   weights as committed scorecard when known; else equal weights and state so.
4. **surface_score 0–3** (audit-scale) from integral:
   - ≥ 9.0 → 3; ≥ 7.5 → 2; ≥ 5.0 → 1; else 0
   - Cap surface_score at 1 if any **P0** open; at 2 if any **P1** open.
5. Tag each finding with `category=<category_id>` (or `pipeline` / `adr-drift`
   when orthogonal; still map impact to nearest scorecard category).

### Interpretation bands (integral)

| Band | integral | Action bias |
| --- | --- | --- |
| excellent | ≥ 9.5 | Hygiene / docs freshness only |
| good_targeted_improvements | 8.5–9.49 | Small waves, density/drift |
| needs_work | 7.0–8.49 | Focused structural paydown |
| weak | &lt; 7.0 | P0/P1 first; stop mass refactors without plan |

## Preflight

1. `git status --porcelain`; SHA; branch; `gh auth status` (no tokens).
2. Dirty foreign work → worktree or read-only audit substeps.
3. SCOPE empty → STOP.
4. `run_id = <UTC>-arch-cycle-<shortsha>`
5. Load scorecard baseline → `baseline-scorecard.json` copy under run dir.
6. Artifacts: `reports/audit-runs/<run_id>/` + mirror `reports/audit/architecture/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Restore** | C4 context/container (container ≠ Docker): systems → units → modules → ports → stores → externals. Dep graph for SCOPE (command/version). |
| **B Score (10 categories)** | Fill `scorecard.json`: per-category score, weight, evidence, delta vs baseline. Compute `integral_score` + `surface_score`. |
| **C Boundaries / runtime** | Import direction; cycles; injection; runtime min scenarios (startup, pipeline run, authz if any, failure/retry). |
| **D Docs/ADR drift** | ADR/diagram claim → path; differential vs `origin/BASE_BRANCH` if set. |
| **E Findings** | PROVEN-only `findings.json` (finding-schema); map to categories; P0–P3. |
| **F Plan** | `plan.json`: ordered waves (≤ MAX_WAVES_PER_ITERATION). Each wave: goal, category_ids, findings, files, risk, test plan, debt effect (↓ or flat), acceptance, rollback. |
| **G Issues** | Dedupe architecture labels. Create if ALLOW_ISSUE_WRITE + PROVEN. Cap MAX_ISSUES_PER_ITERATION. One issue per root-cause. |
| **H Implement** | On WORK_BRANCH: minimal diffs for top waves; no drive-by; no budget raises; no mass layer moves without migration plan. |
| **I Validate** | import-linter / architecture subset; re-score touched categories; PR+checks if ALLOW_PUSH; merge if ALLOW_MERGE. |
| **J Post** | Per finding: resolved \| unchanged \| regressed \| new. Score delta table. `iteration-i/delta.md`. |

`MODE=audit` → stop after E. `audit+plan` → stop after F. `audit+issues` → stop after G (issues only, no implement H). `full` → through J.

If `INCLUDE_PIPELINE=true`: audit arch CI jobs, import-linter wiring, architecture gate; tag `pipeline`.

## Improvement plan contract (`plan.json`)

```json
{
  "iteration": 1,
  "integral_score_before": 9.41,
  "surface_score_before": 2,
  "waves": [
    {
      "id": "W1",
      "priority": "P2",
      "category_ids": ["module_boundaries_coupling"],
      "title": "one checkable outcome",
      "findings": ["ARCH-…"],
      "debt_effect": "flat",
      "risk": "low",
      "files": ["path/…"],
      "test_plan": ["lint-imports", "pytest tests/architecture/…"],
      "acceptance": ["measurable assertion"],
      "rollback": "revert commit / PR"
    }
  ],
  "deferred": [],
  "rejected_policy": []
}
```

Order waves: P0 → P1 → categories with lowest score / largest negative delta →
quick wins (effort S) that raise a category without budget growth.

## Focus checklist (each cycle)

- [ ] All 10 categories scored with evidence
- [ ] `integral_score` + `surface_score` recorded
- [ ] Layer map; no unlisted `interfaces→infrastructure`
- [ ] Plan waves debt-neutral or debt-reducing only
- [ ] ADR-010: no new mandatory Docker/Redis for local default
- [ ] Determinism / architecture gates not weakened
- [ ] Implementation only from plan waves (no drive-by)
- [ ] Re-score after implement; no category regression unexplained
- [ ] No whole-repo code-level diagram dump

## Priority hints

- **P0**: authz break, data ownership corruption, wrong medallion write, secret/data-loss
- **P1**: forbidden layer import, silent contract break, non-deterministic critical write
- **P2**: coupling/hotspot cost, ADR/docs drift, score category &lt; baseline without gate fail
- **P3**: naming/placement, diagram freshness, inventory prose lag

## Outputs

```text
reports/audit-runs/<run_id>/
  run.json
  baseline-scorecard.json          # snapshot of committed scorecard at start
  iteration-<i>/
    architecture-map.md
    dependency-notes.md
    scorecard.json                 # 10 categories + integral + surface_score
    findings.json
    plan.json                      # improvement waves
    issues.jsonl
    summary.md                     # includes score table
    delta.md                       # findings + score deltas
  final-summary.md                 # all iterations, score trend, plan outcomes
reports/audit/architecture/
  report.md
  findings.json
  scorecard.json                   # latest mirror
```

### Required score table in every `summary.md`

| category_id | score | weight | delta | top gap |
| --- | ---: | ---: | ---: | --- |
| (10 rows) | | | | |
| **integral** | | | | |

## Stop

- Empty SCOPE; whole-repo code diagram
- P0 authz/data ownership “fixed” by raising budgets
- Mass layer moves without operator-approved migration plan
- Score inventing without evidence
- Orchestrator hard-stop

## Success

- 10-category `scorecard.json` + findings + plan under run dir
- Plan waves implemented under ALLOW_* or explicitly deferred with reason
- No new P0/P1 boundary regression; category scores ↓ only if explained + residual tracked
- `final-summary.md` after N or early-stop

## Related

- One-shot review: `prompt.architecture.review`
- Tech-debt cycle (adjacent residual): `prompt.audit.tech-debt-cycle`
- Dual-agent: `prompt.audit.dual-agent-cycle` +
  `AUDIT_PROMPT_SOURCE=prompt.architecture.cycle`
- Closeout: `prompt.closeout.grok`
