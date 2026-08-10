---
id: prompt.closeout.grok
version: 2.1.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, codex, any]
params: [REPO, BASE, WORK_BRANCH, SCOPE, MODE, CYCLE_COUNT, LANGUAGE]
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
  - docs/00-project/ai/agents/guides/grok-operator-runbook.md
anti_patterns:
  - Full RULES/ADR dump in the paste
  - Multi-cycle megaprompts (45–70 KB)
  - Committing to main
tags: [closeout, grok, operator]
summary: Short issue/PR closeout paste template
---

# BioETL closeout

Use instead of 45–70 KB multi-cycle megaprompts. Canonical rules stay in
`AGENTS.md` / `docs/00-project/NORMATIVE_SOURCES.md`.

## Params

| Param | Default |
| --- | --- |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `BASE` | `main` |
| `WORK_BRANCH` | create `fix/<slug>` if on main; never commit to main |
| `SCOPE` | issues `<list>` OR path cluster `<paths>` |
| `MODE` | `closeout` |
| `CYCLE_COUNT` | `1` |
| `LANGUAGE` | `ru` (code/ids/paths original) |

## Execution

For each issue in SCOPE:

1. Confirm against current `origin/main` (code wins)
2. Fix product root cause **or** mark `VERIFIED_ALREADY_RESOLVED` with evidence
3. Run focused tests/checks for the surface
4. PR if product/docs delta; else evidence-only
5. Issue comment with acceptance + commands; close if done

Blocked: leave issue OPEN with exact blocker and acceptance gaps.

## Done table

| Issue | Verdict | SHA/PR | Checks |
| --- | --- | --- | --- |

Verdicts: `DONE` | `VERIFIED_ALREADY_RESOLVED` | `BLOCKED`

## Notes

- Prefer `VERIFIED_ALREADY_RESOLVED` when main already fixed.
- Ship-profile (`permission_mode=always-approve`) is optional and short-lived;
  default operator profile is ask — see grok-operator-runbook.
