---
id: prompt.architecture.review
version: 2.3.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [any]
params: [SCOPE, MODE, LANGUAGE, AUDIT_MODE]
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
related_ssot:
  - AGENTS.md
  - docs/00-project/RULES.md
  - docs/00-project/NORMATIVE_SOURCES.md
  - docs/02-architecture/decisions/
anti_patterns:
  - Drive-by refactors outside SCOPE
  - Raising debt budgets to “pass” review
  - Findings without path-level evidence
  - Huge code-level diagram of entire repo
  - C4 “container” assumed to mean Docker
tags: [architecture, review, operator, audit]
summary: Read-only architecture review (hexagonal/C4/arc42) and refactor waves
max_body_lines: 150
---

# Architecture review and refactoring assessment

Restore **actual** architecture from code, manifests, infra, CI, and runtime
relationships; compare to documented architecture. Separate proven fact from
inference. Default mode does **not** apply code changes.

Full generic megaprompts (archive):  
`archive/campaigns/generic-nine-audit-kit-2026-08.md` (prompt 9);  
`archive/campaigns/project-audit-orchestrator-kit-2026-08-11.md` (architecture + loop).


**Machine outputs:** always pair `report.md` + `findings.json` under `reports/audit/architecture/`. For multi-iteration loops use `prompt.audit.orchestrator` and `reports/audit-runs/<run_id>/`.

## Params

| Param | Default |
| --- | --- |
| `SCOPE` | path cluster (e.g. `src/bioetl/domain`) |
| `MODE` | `read-only` \| `propose-patches` |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` \| `differential` |

## BioETL focus

- Layer boundaries: domain / application / infrastructure / composition /
  interfaces (hexagonal)
- No forbidden `interfaces → infrastructure` imports; constructor injection
- Medallion + DQ contracts only as they touch SCOPE
- Determinism, config/schema contracts, **local-only** default runtime
- Debt budgets must not grow

## Method

1. Bottom-up: systems → deployable units → modules → public interfaces →
   stores/queues → external systems (C4 context/container; container ≠ Docker
   by default).
2. Language-native dependency graph for SCOPE (record exact command/version).
3. Boundaries: direction, cycles, shared state, cross-layer imports, data
   ownership, hidden FS/network contracts, migration/rollback.
4. Runtime scenarios (min): startup; main transaction; authz; async/jobs;
   external integration; failure/retry; migration; deploy/rollback.
5. Docs/ADR/diagram drift: each diagram element → implementation path; each
   major deployable → architecture view.
6. Refactor waves: impact, risk, test plan, debt effect (budget-neutral or
   reducing only).
7. If `MODE=propose-patches`: minimal patches only after operator approval.

## Output

- `reports/audit/architecture/report.md`
- `reports/audit/architecture/findings.json` (finding-schema)
- optional extras listed below or in method notes
- `surface_score` 0–3 (map any 0–5 dimensions via audit-scale)
- findings per finding-schema; top remediations
- `MODE=propose-patches` / write modes: only after operator approval and ALLOW flags when orchestrated

## Stop

Empty SCOPE → STOP. No whole-repo code-level diagram. P0 authorization/data
ownership breaks → escalate; do not “fix” by raising debt budgets.
