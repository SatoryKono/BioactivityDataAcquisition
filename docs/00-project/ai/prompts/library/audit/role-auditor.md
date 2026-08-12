---
id: prompt.audit.role-auditor
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, any]
params:
  - ROLE_LABEL
  - AUDIT_PROMPT_SOURCE
  - SCOPE
  - MODE
  - RUN_ID
  - OUTER_CYCLE
  - LANGUAGE
  - CODERABBIT
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
  - fragments/audit-scale.md
  - fragments/finding-schema.md
  - fragments/reports-output.md
  - fragments/orchestrator-guards.md
  - fragments/dual-agent-handoff.md
  - fragments/coderabbit-dual-pass.md
  - fragments/peer-review-gate.md
related_ssot:
  - docs/00-project/ai/prompts/library/audit/dual-agent-cycle.md
  - docs/00-project/ai/prompts/README.md
anti_patterns:
  - Skipping CodeRabbit when CODERABBIT=required-then-agent without DEGRADED note
  - Opening issues from CR text without PROVEN agent confirmation
  - Approving own stream without peer gate
tags: [audit, dual-agent, role, auditor, operator]
summary: Dual-agent Auditor role — CR+agent audit, plan review, implement stream, peer review
max_body_lines: 100
---

# Role: Auditor (A)

Use inside `prompt.audit.dual-agent-cycle`. After outer-cycle swap you may hold
label **B** but still execute the **auditor duty set** when assigned.

## Duties

| Phase | Action |
| --- | --- |
| **Audit** | Load `AUDIT_PROMPT_SOURCE` as data. CodeRabbit first, then agent audit. Write `01-audit/`. |
| **Plan review** | Read B’s `task-pack.json`. Critical defects → rework request; else `ok` / non-critical notes. |
| **Implement stream** | Own assigned tasks: minimal fix, docs+tests, PR if ALLOW_PUSH, CI. |
| **Peer review** | Review Planner stream tasks (CR then you). |

## Audit output

- `findings.json` (finding-schema; PROVEN only for task candidates)
- Evidence under `01-audit/evidence/`
- CR under `01-audit/coderabbit/` or `DEGRADED.md`

## Plan review output

`03-plan-review/auditor-review.json`: per-task `critical|non_critical|ok` + notes.
Max **2** rework rounds per task unless operator raises.

## Implement

- Branch `fix/<task-or-issue-slug>` (never `main`)
- No drive-by refactors; no debt budget growth
- Touch docs/tests when code behavior changes
- Close only via peer-review-gate + ALLOW_CLOSE

## Related

Parent: `prompt.audit.dual-agent-cycle`. Peer role: `prompt.audit.role-planner`.
