---
name: bioetl-closeout
description: Close BioETL GitHub issues with evidence against origin/main. Use for issue closeout, VERIFIED_ALREADY_RESOLVED, PR ship, or /bioetl-closeout.
---

# BioETL issue closeout

Canonical paste card: `prompt.closeout.grok` (v2.2+).
Operator runbook: `docs/00-project/ai/agents/guides/grok-operator-runbook.md`.

## When to use

- Operator lists issue numbers to close or verify
- Need evidence-only close because main already fixed the root cause
- Ship PR + issue comments after a fix

## Procedure

For each issue in SCOPE:

1. **Confirm** the claim against current `origin/main` (code wins over issue text).
2. **Verdict**
   - still present → fix on `fix/<slug>` (never main)
   - already fixed → `VERIFIED_ALREADY_RESOLVED` with SHA, path, command
   - cannot proceed → `BLOCKED` with exact blocker and acceptance gaps
3. **Verify** focused tests/checks; list commands.
4. **Post-change** for touched surfaces (skill `bioetl-post-change`).
5. **Ship** PR if product/docs delta; else evidence-only comment.
6. **Close** only when acceptance is met.

## Render paste

```powershell
.\.venv-win\Scripts\python.exe -m scripts.ai.prompts render prompt.closeout.grok `
  --param SCOPE="issues: #NNNN"
```

## Done table

| Issue | Verdict | SHA/PR | Checks | Notes |
| --- | --- | --- | --- | --- |

Verdicts: `DONE` | `VERIFIED_ALREADY_RESOLVED` | `BLOCKED`

## Safety

- No secrets in issue comments or commits
- Default permissions: ask; ship profile (`always-approve`) is short-lived only
- No force-push / reset --hard / commit to main
- Prefer `VERIFIED_ALREADY_RESOLVED` when main already fixed the root cause
