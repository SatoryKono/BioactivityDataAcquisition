---
id: prompt.architecture.cycle
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
  - ALLOW_ISSUE_WRITE
  - ALLOW_PUSH
  - ALLOW_MERGE
  - ALLOW_CLOSE
  - MAX_ISSUES_PER_ITERATION
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
  - fragments/unknown-params.md
  - fragments/reports-output.md
  - fragments/shell-portability.md
  - fragments/orchestrator-guards.md
related_ssot:
  - AGENTS.md
  - docs/00-project/RULES.md
  - docs/00-project/NORMATIVE_SOURCES.md
  - docs/00-project/architecture-index.md
  - docs/02-architecture/decisions/
  - docs/00-project/ai/prompts/library/architecture/review-assessment.md
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
tags: [architecture, audit, cycle, hexagonal, operator]
summary: Cyclic project architecture audit — layers, boundaries, ADR drift, fix waves, re-verify
max_body_lines: 190
---

# Cyclic project architecture audit

N-итерационный **архитектурный аудит проекта**: restore actual architecture from
code → compare to docs/ADR → boundaries/cycles → runtime scenarios → debt-safe
refactor waves → issues → fix → re-verify.

Domain method: `prompt.architecture.review` (hexagonal / C4 / arc42).  
Loop shell: `prompt.audit.orchestrator`.

Default **`N=10`**, **`MODE=full`**, **`INCLUDE_PIPELINE=true`**,
**`LAYERS=all`**, все **`ALLOW_*=true`**.

Пустые циклы запрещены. Early-stop: 2 подряд итерации без новых actionable
PROVEN P0/P1 и без regression.

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `src/bioetl/` (+ `tests/` architecture, configs, compose as needed) |
| `MODE` | `full` (also: `audit` \| `audit+issues`) |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` \| `differential` |
| `INCLUDE_PIPELINE` | `true` (arch CI gates, import-linter, architecture tests) |
| `LAYERS` | `all` or CSV: `domain,application,infrastructure,composition,interfaces` |
| `ALLOW_ISSUE_WRITE` | `true` |
| `ALLOW_PUSH` | `true` |
| `ALLOW_MERGE` | `true` |
| `ALLOW_CLOSE` | `true` |
| `MAX_ISSUES_PER_ITERATION` | `5` |
| `BASE_BRANCH` | `main` |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `WORK_BRANCH` | `fix/architecture-audit-cycle-<shortsha>` |

## BioETL anchors (read, do not reinvent)

- Hexagonal / layers: `docs/00-project/RULES.md` §1; **ADR-005** composition separation
- Medallion: ADR-002 / RULES §2; DQ contracts ADR-027/045 (only if SCOPE touches)
- Local-only default runtime: **ADR-010** (no forced Docker/Redis orchestration)
- Determinism: ADR-014; observability ports ADR-006/017/019
- Architecture index: `docs/00-project/architecture-index.md`
- ADRs: `docs/02-architecture/decisions/`
- Dependency map (generated): `docs/02-architecture/generated/module-dependency-map.*` when present
- Architecture tests: `tests/architecture/` (import boundaries, residual non-growth)
- Debt budgets: **must not increase** (debt-budget-ban / AGENTS.md)

## Preflight

1. `git status --porcelain`; SHA; branch; toolchain; `gh auth status` (no tokens).
2. Dirty foreign work → worktree or **read-only** for pure audit substeps.
3. Confirm SCOPE exists; empty → STOP.
4. `run_id = <UTC>-arch-cycle-<shortsha>`
5. Artifacts: `reports/audit-runs/<run_id>/` and mirror `reports/audit/architecture/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Restore** | Bottom-up C4 context/container (container ≠ Docker by default): systems → deployable units → modules → public ports → stores → externals. Language-native dependency graph for SCOPE (record command/version). Restrict to `LAYERS` if not `all`. |
| **B Boundaries** | Import direction; cycles; shared state; forbidden `interfaces → infrastructure`; constructor injection; data ownership; hidden FS/network contracts; migration/rollback seams. |
| **C Runtime scenarios** | Min set: startup; main transaction/pipeline run; authz if present; async/jobs; external integration; failure/retry; deploy/rollback. Mark Not Verifiable if runtime absent. |
| **D Docs/ADR drift** | Each major diagram/ADR claim in SCOPE → implementation path; each deployable → architecture view. Differential: only changed paths vs `origin/BASE_BRANCH`. |
| **E Normalize** | `findings.json` (finding-schema, PROVEN only) + `report.md`; `surface_score` 0–3; tag `category=boundary\|cycle\|injection\|medallion\|determinism\|adr-drift\|runtime\|pipeline`. |
| **F Issues** | Dedupe (`architecture`, layer labels). Create if ALLOW_ISSUE_WRITE + PROVEN. Title `[architecture][P#] one checkable outcome`. Cap MAX_ISSUES_PER_ITERATION. Prefer one issue per root-cause boundary breach. |
| **G Fix** | Minimal boundary/injection/docs fixes on WORK_BRANCH; **no** drive-by refactors; waves only budget-neutral or debt-reducing; focused architecture/unit tests. |
| **H Validate** | Re-run import-linter / `tests/architecture` subset if available; if ALLOW_PUSH → PR + required checks; merge if ALLOW_MERGE. |
| **I Post** | Per finding: resolved \| unchanged \| regressed \| new → `iteration-i/delta.md`. |

If `INCLUDE_PIPELINE=true`: also audit architecture CI jobs, import-linter config, architecture test gate wiring; tag `pipeline`.

## Domain method — architecture.review (each A–E)

1. Bottom-up: systems → deployable units → modules → public interfaces →
   stores/queues → external systems (C4 context/container).
2. Language-native dependency graph for SCOPE (record exact command/version).
3. Boundaries: direction, cycles, shared state, cross-layer imports, data
   ownership, hidden FS/network contracts, migration/rollback.
4. Runtime scenarios (min list above).
5. Docs/ADR/diagram drift: diagram element → implementation path; major
   deployable → architecture view.
6. Refactor waves: impact, risk, test plan, debt effect (budget-neutral or ↓ only).

## Focus checklist (each cycle)

- [ ] Layer map for SCOPE (domain / application / infrastructure / composition / interfaces)
- [ ] No proven `interfaces → infrastructure` imports (or listed as PROVEN P0/P1)
- [ ] Cycles / shared mutable state documented with paths
- [ ] Constructor injection preserved; no new service locators without ADR
- [ ] Medallion/DQ claims only where SCOPE touches
- [ ] ADR-010: no new mandatory Docker/Redis/orchestration for local default
- [ ] Determinism contracts not weakened
- [ ] Architecture tests / import-linter still meaningful (not gutted)
- [ ] Debt budgets unchanged or reduced
- [ ] No whole-repo code-level diagram dump

## Priority hints

- **P0**: authorization break, data ownership corruption, medallion write to wrong layer, secret/data-loss path
- **P1**: forbidden layer import, silent contract break, non-deterministic write on critical path
- **P2**: cycles/shared state with material cost-of-change, ADR/docs drift
- **P3**: local naming/placement hygiene, diagram freshness

## Outputs

```text
reports/audit-runs/<run_id>/
  run.json
  iteration-<i>/
    architecture-map.md      # C4-level, not whole-repo code graph
    dependency-notes.md      # command + key cycles/edges
    findings.json
    plan.json
    issues.jsonl
    summary.md
    delta.md
  final-summary.md
reports/audit/architecture/   # optional latest mirror
  report.md
  findings.json
```

## Stop

- Empty SCOPE → STOP
- No whole-repo code-level diagram
- P0 authz/data ownership → escalate; do not “fix” by raising debt budgets
- Mass layer moves without operator-approved migration plan
- Orchestrator hard-stop conditions

## Success

- Findings + map under `reports/audit-runs/<run_id>/`
- No new P0/P1 boundary regression after fixes
- PROVEN issues handled under ALLOW_*
- `final-summary.md` after N=10 or early-stop

## Related

- Domain one-shot: `prompt.architecture.review`
- Dual-agent: `prompt.audit.dual-agent-cycle` +
  `AUDIT_PROMPT_SOURCE=prompt.architecture.review`
- Tech-debt cycle (adjacent): `prompt.audit.tech-debt-cycle`
- Closeout: `prompt.closeout.grok`
