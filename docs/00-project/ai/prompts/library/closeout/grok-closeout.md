---
id: prompt.closeout.grok
version: 2.2.0
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
  - docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md
anti_patterns:
  - Full RULES/ADR dump in the paste
  - Multi-cycle megaprompts (45–70 KB)
  - Committing to main
  - Closing without verification against origin/main
  - Leaving ship profile as long-term default
tags: [closeout, grok, operator]
summary: Issue/PR closeout paste with verdicts, evidence, ship-profile note
max_body_lines: 120
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

## Runtime

- Windows: `.\.venv-win\Scripts\python.exe` only
- Code on `origin/BASE` wins over issue text and memory
- No secrets in issue comments, commits, or reports
- Prefer plan mode only when SCOPE spans many unrelated surfaces

## Per-issue loop

For each issue in SCOPE:

1. **Confirm** claim against current `origin/BASE` + checkout (code wins)
2. **Verdict path**
   - still present → fix on `WORK_BRANCH`
   - already fixed on main → `VERIFIED_ALREADY_RESOLVED` + evidence (SHA, path, command)
   - cannot proceed → `BLOCKED` + exact blocker + acceptance gaps
3. **Verify** focused tests/checks; list commands
4. **Post-change** for touched surfaces (`POST_CHANGE_VALIDATION.md`); mirror parity if runtime trees changed
5. **Ship** PR if product/docs delta; else evidence-only comment
6. **Close** only when acceptance met; comment with verdict + commands + SHA/PR

Blocked: leave issue OPEN with blocker and acceptance gaps.

## Done table

| Issue | Verdict | SHA/PR | Checks | Notes |
| --- | --- | --- | --- | --- |

Verdicts: `DONE` | `VERIFIED_ALREADY_RESOLVED` | `BLOCKED`

## Ship profile (optional, short-lived)

- Default operator profile: `permission_mode=ask` (see grok-operator-runbook)
- Ship session only: `always-approve` for issue comments/closes + PR ops
- Return to **ask** immediately after the session
