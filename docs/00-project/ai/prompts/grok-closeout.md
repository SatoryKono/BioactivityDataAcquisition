# Grok Closeout Prompt (short)

*Status: internal working prompt | Class: operator aid | Not governance SSOT*

Use this instead of 45–70 KB multi-cycle megaprompts. Canonical rules stay in
`AGENTS.md` / `docs/00-project/NORMATIVE_SOURCES.md`.

## Paste template

```text
# BioETL closeout

## Params
- REPO: SatoryKono/BioactivityDataAcquisition
- BASE: main
- WORK_BRANCH: create fix/<slug> if on main; never commit to main
- SCOPE: issues <list> OR path cluster <paths>
- MODE: closeout
- CYCLE_COUNT: 1
- LANGUAGE: ru (code/ids/paths original)

## Read (do not restate)
1. AGENTS.md
2. docs/00-project/NORMATIVE_SOURCES.md
3. docs/00-project/ai/agents/guides/MEMORY_USAGE.md (if AI/memory surfaces)

## Git / safety
- Do not edit/delete others' uncommitted work
- No reset --hard, no force-push, no .env edits without explicit approval
- Prefer worktree if main dirty
- Push feature branch only; open PR to main

## Execution
For each issue in SCOPE:
1. Confirm against current origin/main (code wins)
2. Fix product root cause OR mark VERIFIED_ALREADY_RESOLVED with evidence
3. Run focused tests/checks for the surface
4. PR if product/docs delta; else evidence-only
5. Use .venv-win/Scripts/python.exe on Windows or .venv/bin/python in WSL/Linux
6. Run proof-or-stop assemble + verify; prose is a claim, not DONE state
7. Only ADMIT at the required trust tier qualifies closeout; DEGRADED/STOP stay open
8. Optional vendor evidence cannot override the offline core verifier
9. Issue comment with acceptance + commands; close if admitted and done
Blocked: leave issue OPEN with exact blocker and acceptance gaps

## Done table
| Issue | Verdict | SHA/PR | Checks |
```

## Notes

- Prefer VERIFIED_ALREADY_RESOLVED when main already fixed.
- Do not grow tech-debt / quality budgets.
- Ship-profile (`permission_mode=always-approve`) is optional and short-lived;
  default operator profile is ask — see
  `docs/00-project/ai/agents/guides/grok-operator-runbook.md`.
