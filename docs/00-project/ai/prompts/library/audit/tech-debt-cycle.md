---
id: prompt.audit.tech-debt-cycle
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
  - docs/00-project/governance/08-debt-ownership-playbook.md
  - docs/00-project/ai/prompts/library/audit/tech-debt.md
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
  - configs/quality/debt_scorecard.yaml
  - reports/quality/debt-governance-gates.json
  - reports/quality/live-residual-snapshot.json
anti_patterns:
  - Raising debt/quality budgets or exemptions
  - Priority by TODO count instead of blast radius
  - Empty form cycles
  - Treating every style nit as technical debt
tags: [audit, debt, cycle, quality, operator]
summary: Cyclic technical-debt audit — register, trend, paydown, fix, residual re-check
max_body_lines: 160
---

# Cyclic technical debt audit

N-итерационный **аудит техдолга**: evidence register → risk order → paydown →
residual re-check. Domain method: `prompt.audit.tech-debt`. Loop shell:
`prompt.audit.orchestrator`.

**УВЕЛИЧИВАТЬ бюджеты техдолга ЗАПРЕЩЕНО** (debt-budget-ban / AGENTS.md).

Default **`N=10`**, **`MODE=full`**, все **`ALLOW_*=false`**. Operator full-run must set `ALLOW_ISSUE_WRITE/PUSH/MERGE/CLOSE=true` explicitly.

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | path cluster / theme (e.g. `src/bioetl/domain/`, `scripts/`, quality configs) |
| `MODE` | `full` (also: `audit` \| `audit+issues`) |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` \| `differential` |
| `ALLOW_ISSUE_WRITE` | `false` (operator full-run: `true`) |
| `ALLOW_PUSH` | `false` (operator full-run: `true`) |
| `ALLOW_MERGE` | `false` (operator full-run: `true`) |
| `ALLOW_CLOSE` | `false` (operator full-run: `true`) |
| `MAX_ISSUES_PER_ITERATION` | `5` |
| `BASE_BRANCH` | `main` |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |

## BioETL anchors

- Ownership: `docs/00-project/governance/08-debt-ownership-playbook.md`
- Scorecard: `configs/quality/debt_scorecard.yaml`
- Gates: `reports/quality/debt-governance-gates.json` (+ `.md`)
- Residual snapshot: `reports/quality/live-residual-snapshot.json`
- Registry: `configs/quality/technical_debt_audit_registry.yaml` (when present)
- Closeout pins under `reports/quality/tech-debt-issues-*-closeout.json`
- Architecture residual tests: do not weaken non-growth contracts

## Preflight

1. `git status --porcelain`; SHA; branch.
2. Load current budgets/registries **read-only**; record baseline hashes/paths.
3. `run_id = <UTC>-debt-cycle-<shortsha>`
4. Artifacts: `reports/audit-runs/<run_id>/`

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Audit** | Run `prompt.audit.tech-debt` on SCOPE. Collect TODO/FIXME/HACK, suppressions, shims, disabled gates, oversized modules, cycles. Cross-check debt-governance gates + residual snapshot **trend** (no higher limits). |
| **B Plan** | Order by blast radius (P0 security/data → P3 local cleanup). Each item: owner suggestion, tests protecting refactor, paydown step that **reduces or holds** residual. |
| **C Issues** | Dedupe (`tech-debt`, `quality`, debt labels). Create only if ALLOW_ISSUE_WRITE + PROVEN. Prefer one cluster per root cause. |
| **D Fix** | Pay down only; never raise budgets/exemptions/hotspot caps. Refresh inventories only via project scripts when required. |
| **E Validate** | Re-run debt/residual gates if project provides commands; architecture residual non-growth must still pass. |
| **F Post** | Residual delta table: before/after for touched families; list rejected “raise budget” ideas as `REJECTED_POLICY`. |

`MODE=audit` → stop after A. `audit+issues` → stop after C (no implement). `full` → through F.

## Focus checklist (each cycle)

- [ ] No budget/exemption/threshold increase in plan or PR
- [ ] Top items have path + evidence + blast radius
- [ ] Security/data integrity items not buried under style nits
- [ ] Disabled checks/quarantines have owner or tracked issue
- [ ] Residual snapshot / gates trend documented (↓ or flat)
- [ ] Fix PRs include focused tests where behavior changes

## Stop

Any remediation that **raises** a budget/exemption → **reject**. Hard stop on
orchestrator-guards. Do not delete residual pins without regenerating via SSOT scripts.

## Success

- Debt register + findings under `reports/audit-runs/<run_id>/`
- Residual metrics non-increasing for touched surfaces
- Accepted paydowns validated; deferred items have owner/date

## Related

- Domain: `prompt.audit.tech-debt`
- Dual-agent: `prompt.audit.dual-agent-cycle` +
  `AUDIT_PROMPT_SOURCE=prompt.audit.tech-debt`
- Closeout: `prompt.closeout.grok`
