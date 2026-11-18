---
name: bioetl-closeout
description: Close BioETL GitHub issues with evidence against origin/main. Use for issue closeout, VERIFIED_ALREADY_RESOLVED, PR ship, or /bioetl-closeout.
---

# BioETL issue closeout

Canonical paste card: `prompt.closeout.grok`.
Operator runbook: `docs/00-project/ai/agents/guides/grok-operator-runbook.md`.
Guardrails and task class: `AGENTS.md`.

## When to use

- Operator lists issue numbers to close or verify
- Need evidence-only close because main already fixed the root cause
- Ship PR and issue comments after a fix

## Procedure

For each issue in SCOPE:

1. Confirm the claim against current `origin/main`.
2. Verdict: still present, `VERIFIED_ALREADY_RESOLVED`, or `BLOCKED`.
3. Run focused checks and list the commands.
4. Post-change via skill `bioetl-post-change`.
5. Ship a PR when product or docs changed; otherwise comment with evidence.
6. Close only when acceptance is met.

```powershell
.\.venv-win\Scripts\python.exe -m scripts.ai.prompts render prompt.closeout.grok `
  --param SCOPE="issues: #NNNN"
```

| Issue | Verdict | SHA/PR | Checks | Notes |
| --- | --- | --- | --- | --- |

Verdicts: `DONE` | `VERIFIED_ALREADY_RESOLVED` | `BLOCKED`
