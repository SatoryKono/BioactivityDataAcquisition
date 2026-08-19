---
id: prompt.audit.cycle.tech-debt
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, codex, any]
params:
  - N = `10`
  - SCOPE =  `src/bioetl/ configs/quality/` 
  - MODE = `full`
  - LANGUAGE  = `ru` 
  - AUDIT_MODE = `full`
  - ALLOW_ISSUE_WRITE = `true` 
  - ALLOW_PUSH = `true` 
  - ALLOW_MERGE = `true` 
  - ALLOW_CLOSE = `true` 
  - MAX_ISSUES_PER_ITERATION  = `10`
  - BASE_BRANCH = `main`
  - REPO = `SatoryKono/BioactivityDataAcquisition` 
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
  - docs/00-project/governance/08-debt-ownership-playbook.md
  - docs/00-project/ai/prompts/library/audit/tech-debt.md
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
  - configs/quality/debt_scorecard.yaml
  - reports/quality/debt-governance-gates.json
anti_patterns:
  - Raising debt/quality budgets or exemptions
  - Priority by TODO count instead of blast radius
  - Treating every style nit as technical debt
  - Deleting residual pins without regenerating via SSOT scripts
  - Empty form cycles
tags: [audit, debt, cycle, quality, operator]
summary: Cyclic technical-debt audit — register, trend, paydown, residual re-check
max_body_lines: 240
---

# Cyclic technical-debt audit

N-итерационный аудит **технического долга**: evidence register → risk order →
paydown → residual re-check. Domain method: `prompt.audit.tech-debt`.
Loop shell: `prompt.audit.orchestrator`.

**УВЕЛИЧИВАТЬ бюджеты техдолга ЗАПРЕЩЕНО** (debt-budget-ban / `AGENTS.md`).

Default **`N=10`**, **`MODE=full`**, все **`ALLOW_*=true`**. Пустые циклы запрещены.

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

## BioETL anchors

- Ownership: `docs/00-project/governance/08-debt-ownership-playbook.md`
- Scorecard: `configs/quality/debt_scorecard.yaml`
- Gates: `reports/quality/debt-governance-gates.json`
- Residual snapshot: `reports/quality/live-residual-snapshot.json`
- Architecture residual tests: do not weaken non-growth contracts
- Windows: `.\.venv-win\Scripts\python.exe`

Separate deliberate tradeoffs, historical constraints, maintainability debt,
obsolete deps, test debt, and architecture drift. Style nits are not debt
unless they hide correctness or blast radius.

## Preflight

1. `git status --porcelain`; SHA; branch.
2. Load current budgets/registries **read-only**; record baseline hashes/paths.
3. `run_id = <UTC>-debt-cycle-<shortsha>`
4. Artifacts: `reports/audit-runs/<run_id>/` + mirror `reports/audit/tech-debt/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Register** | Collect TODO/FIXME/HACK, suppressions, shims, disabled gates, oversized modules, import cycles. Cross-check debt-governance gates + residual snapshot **trend** (no higher limits). |
| **B Risk order** | Blast radius: P0 security/data → P3 local cleanup. Each item: owner suggestion, tests protecting the refactor, paydown step that **reduces or holds** residual. |
| **C Issues** | Dedupe (`tech-debt`, `quality`). Create only if ALLOW_ISSUE_WRITE + PROVEN. One cluster per root-cause. |
| **D Paydown** | Pay down only. Never raise budgets/exemptions/hotspot caps. Refresh inventories only via project scripts. |
| **E Validate** | Re-run debt/residual gates when project commands exist. Architecture residual non-growth must still pass. |
| **F Post** | Residual delta table: before/after for touched families. List rejected “raise budget” ideas as `REJECTED_POLICY`. |

## Focus checklist (each cycle)

- [ ] No budget/exemption/threshold increase in plan or PR
- [ ] Top items have path + evidence + blast radius
- [ ] Security/data integrity items not buried under style nits
- [ ] Disabled checks/quarantines have owner or tracked issue
- [ ] Residual snapshot / gates trend documented (↓ or flat)
- [ ] Fix PRs include focused tests where behavior changes

## Stop

Any remediation that **raises** a budget/exemption → **reject**.
Do not delete residual pins without regenerating via SSOT scripts.
Orchestrator hard-stop applies.

## Success

- Debt register + findings under `reports/audit-runs/<run_id>/`
- Residual metrics non-increasing for touched surfaces
- Accepted paydowns validated; deferred items have owner/date
- `surface_score` 0–3; cap at 1 if any P0 remains

## Related

- Domain: `prompt.audit.tech-debt`
- Dual-agent: `prompt.audit.dual-agent-cycle` +
  `AUDIT_PROMPT_SOURCE=prompt.audit.tech-debt`
- Closeout: `prompt.closeout.grok`
- Previous: `prompt.audit.cycle.tests` · Next: `prompt.audit.cycle.architecture`
