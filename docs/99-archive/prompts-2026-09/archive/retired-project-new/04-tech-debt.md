---
id: prompt.audit.project.new.tech-debt
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
  - docs/00-project/governance/08-debt-ownership-playbook.md
  - docs/00-project/ai/prompts/library/audit/tech-debt.md
  - configs/quality/debt_scorecard.yaml
  - reports/quality/debt-governance-gates.json
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
anti_patterns:
  - Inventing REQ-* IDs not in REQUIREMENTS.md / the traceability CSV
  - Raising debt/quality budgets or exemptions
  - Priority by TODO count instead of blast radius
  - Treating every style nit as technical debt
  - Deleting residual pins without regenerating via SSOT scripts
  - Empty form cycles
  - Mutations without PROVEN + requirement_id
tags: [audit, debt, cycle, quality, operator]
summary: Improved cyclic tech-debt audit — register, blast-radius paydown, residual re-check, ALLOW_* true, early-stop
max_body_lines: 220
---

# Improved cyclic technical-debt audit

Улучшает `prompt.audit.cycle.tech-debt` + `prompt.audit.tech-debt-cycle`.
Method: `prompt.audit.tech-debt`. Loop: `prompt.audit.orchestrator`.

Library defaults: **`ALLOW_*=true`**. Пустые циклы запрещены.
**УВЕЛИЧИВАТЬ бюджеты техдолга ЗАПРЕЩЕНО.**

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `src/bioetl/ configs/quality/` |
| `MODE` | `full` (`audit` \| `audit+issues` \| `full`) |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` \| `differential` |
| `ALLOW_ISSUE_WRITE` | `true` |
| `ALLOW_PUSH` | `true` |
| `ALLOW_MERGE` | `true` |
| `ALLOW_CLOSE` | `true` |
| `MAX_ISSUES_PER_ITERATION` | `5` |
| `BASE_BRANCH` | `main` |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `WORK_BRANCH` | `fix/tech-debt-cycle-new-<shortsha>` |

## Anchors

- Scorecard: `configs/quality/debt_scorecard.yaml` (read-only budgets)
- Gates: `reports/quality/debt-governance-gates.json`
- Residual: `reports/quality/live-residual-snapshot.json` when present
- Refresh inventories only via project scripts
- PROVEN finding MUST have `requirement_id`

## Preflight

1. `git status --porcelain`; SHA. Load budgets **read-only**; record hashes.
2. `run_id = <UTC>-debt-new-<shortsha>`. Marker: `Cycle-run: <run_id>`.
3. Artifacts: `reports/audit-runs/<run_id>/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Register** | TODO/FIXME/HACK, suppressions, shims, disabled gates, hotspots. Trend vs gates — no higher limits. |
| **B Risk** | Blast radius P0 security/data → P3 local. Owner, protecting tests, paydown that ↓ or holds residual. |
| **C Issues** | ALLOW_ISSUE_WRITE + PROVEN + `requirement_id`. Title `[tech-debt][<REQ-id>][P#]`. |
| **D Paydown** | Pay down only. Never raise budgets/exemptions/hotspot caps. |
| **E Validate** | Re-run debt/residual gates when commands exist. Architecture residual non-growth still passes. |
| **F Post** | Residual delta table. List rejected “raise budget” as `REJECTED_POLICY`. Close only on `origin/main` if ALLOW_CLOSE. |

## Early-stop

`new_issues_i == 0` **и** `open_cycle_issues == 0` → STOP.
Два подряд цикла без новых PROVEN P0/P1 и без residual worsen → STOP.

## Success

- Residual/budget delta ↓ or flat
- `REJECTED_POLICY` captured; no silent budget growth
