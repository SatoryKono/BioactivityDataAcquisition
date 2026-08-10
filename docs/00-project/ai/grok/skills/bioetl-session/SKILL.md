---
name: bioetl-session
description: Bootstrap a BioETL Grok session — read order, Windows venv, branch safety, mode routing. Use when starting work, /bioetl-session, or when the operator has not locked SCOPE/MODE.
---

# BioETL session bootstrap

Not runtime SSOT. Follow `AGENTS.md` precedence when anything conflicts.

## When to use

- New Grok session on BioETL
- Operator gave a goal but not a full paste template
- Need to choose implement / audit / closeout / plan-only

## Mandatory steps

1. Confirm checkout path and that work is not on `main` for commits.
2. Windows: use only `.\.venv-win\Scripts\python.exe` (or activate `.venv-win`).
3. Lock **TASK**, **MODE**, **SCOPE**, **WORK_BRANCH**.
4. Read only what SCOPE needs:
   - `AGENTS.md`
   - `docs/00-project/NORMATIVE_SOURCES.md` (relevant slices)
   - role/memory sheets only if AI/memory surfaces are in SCOPE
5. Substantial work → memory pre-task when the workflow is available:
   `.\.venv-win\Scripts\python.exe -m memory.tooling.workflow pre-task ...`
6. Prefer plan mode when SCOPE is large or cross-layer.

## Mode routing

| MODE | Action |
| --- | --- |
| plan-only | Explore + plan; no writes unless upgraded |
| implement | Edit + focused tests |
| audit | Render `prompt.audit.grok-cycle` |
| closeout | Render `prompt.closeout.grok` or use skill `bioetl-closeout` |

Render helpers:

```powershell
.\.venv-win\Scripts\python.exe -m scripts.ai.prompts render prompt.session.grok-bootstrap `
  --param TASK="..." --param MODE=implement --param SCOPE="..."
```

## Guardrails (do not restate full RULES)

- No `.env` create/edit/delete without explicit approval
- No tech-debt budget / exemption / threshold increases
- No root scratch (`_tmp_*.py`, `nul`/`NUL`)
- No `reset --hard`, force-push, or commits to `main`
- Protect foreign uncommitted WIP; use worktree if main is dirty
- Answer in Russian when the operator writes Russian; keep technical literals original

## Done shape

Report: what changed, evidence (paths/commands), tests run, post-change status,
and any `BLOCKED` / `DEGRADED_MCP` notes.
