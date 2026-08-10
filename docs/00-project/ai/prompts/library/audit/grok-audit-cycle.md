---
id: prompt.audit.grok-cycle
version: 2.1.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, codex, any]
params: [REPO, BASE, WORK_BRANCH, SCOPE, MODE, CYCLE_COUNT, AUDIT_MODE, REQUIRE_GH_TRACKING, LANGUAGE]
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
related_ssot:
  - AGENTS.md
  - docs/00-project/NORMATIVE_SOURCES.md
  - docs/00-project/ai/agents/guides/MEMORY_USAGE.md
anti_patterns:
  - Nine simultaneous Principal roles
  - Full RULES/ADR dump in the prompt
  - CYCLE_COUNT=5 with mandatory empty cycles
  - 24-section mandatory report outline every time
tags: [audit, grok, operator]
summary: Short one-cycle audit paste template
---

# BioETL audit cycle

Default **one** full cycle per session. Raise to 2 only if explicitly requested.
Do not run empty cycles "for form".

## Params

| Param | Default |
| --- | --- |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `BASE` | `main` |
| `WORK_BRANCH` | `fix/<audit-slug>` (never main) |
| `SCOPE` | surface list or theme |
| `MODE` | `audit` |
| `CYCLE_COUNT` | `1` |
| `AUDIT_MODE` | `full` \| `differential` |
| `REQUIRE_GH_TRACKING` | `true` |
| `LANGUAGE` | `ru` (code/ids/paths original) |

## Stage 1 — Findings

- Inventory only paths that exist in this checkout
- Each finding: severity, path, symbol, claim, evidence (test/command/snippet)
- No finding without file-level proof; mark `NOT_PROVEN` otherwise

## Stage 2 — GitHub tracking

- Search open issues before create
- Create/reopen/link one issue per root cause (or path-cluster)
- No duplicate issues

## Stage 3 — Remediation

- Fix available findings; do not close blocked items
- Tests/checks listed; no tech-debt budget growth
- PR for product/docs deltas

## Cycle closeout

| Finding | Issue | State | Commit/PR | Verification |
| --- | --- | --- | --- | --- |

If `NO_ACTIONABLE_FINDINGS`: stop (do not invent work for remaining cycles).
