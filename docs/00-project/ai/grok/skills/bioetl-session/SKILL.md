---
name: bioetl-session
description: Bootstrap a BioETL Grok session — read order, Windows venv, branch safety, mode routing. Use when starting work, /bioetl-session, or when the operator has not locked SCOPE/MODE.
---

# BioETL session bootstrap

Not runtime SSOT. Task class, memory mode, and guardrails:
`AGENTS.md`. On conflict, follow that file.

## When to use

- New Grok session on BioETL
- Operator gave a goal but not a full paste template
- Need to choose implement / audit / closeout / plan-only / ci-rebind

## Mandatory steps

1. Confirm checkout path and that commits are not made on `main`.
2. Windows: use `.\.venv-win\Scripts\python.exe`.
3. Lock **TASK**, **MODE**, **SCOPE**, **WORK_BRANCH**.
4. Load the task class from `AGENTS.md`. Do not copy that table into this skill.

## Mode routing

| MODE | Action |
| --- | --- |
| plan-only | Explore and plan |
| implement | Edit and run focused tests |
| audit | Render `prompt.audit.cycle` |
| closeout | Skill `bioetl-closeout` |
| ci-rebind | Coupled `refresh-ci-drift-families`; memory `off` |

```powershell
.\.venv-win\Scripts\python.exe -m scripts.ai.prompts render prompt.session.grok-bootstrap `
  --param TASK="..." --param MODE=implement --param SCOPE="..."
```

After merge, reinstall local Grok skills with `.\scripts\ai\grok\install_skills.ps1`.
Do not commit `~/.grok/skills`.
