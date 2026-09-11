---
name: bioetl-session
description: Bootstrap a BioETL Grok session — read order, Windows venv, branch safety, mode routing. Use when starting work, /bioetl-session, or when the operator has not locked SCOPE/MODE.
---

# BioETL session bootstrap

Not runtime SSOT. Follow `AGENTS.md` precedence when anything conflicts.

## When to use

- New Grok session on BioETL
- Operator gave a goal but not a full paste template
- Need to choose implement / audit / closeout / plan-only / ci-rebind

## Mandatory steps

1. Confirm checkout path and that work is not on `main` for commits.
2. Windows: use only `.\.venv-win\Scripts\python.exe` (or activate `.venv-win`).
3. Lock **TASK**, **MODE**, **SCOPE**, **WORK_BRANCH**.
4. Load by **task class** from `AGENTS.md` (do not dump RULES/ADR):

| Task class | Read | Memory |
| --- | --- | --- |
| hash-only / `ci-rebind` / date stamp / remote-main | drift runbook + touched reporter | `BIOETL_AI_MEMORY_MODE=off`; skip NORMATIVE + full `pre-task` |
| V1 docs/prompt | `AGENTS.md` guardrails + POST_CHANGE docs slice | read-only optional |
| V2 focused code | + matching role/skill for SCOPE | `pre-task` |
| V3/V4 | full package via `AGENTS.md` (includes NORMATIVE slices) | `pre-task` required |

5. Substantial work → memory pre-task when the workflow is available:
   `.\.venv-win\Scripts\python.exe -m memory.tooling.workflow pre-task ...`
6. Prefer plan mode when SCOPE is large or cross-layer.

## Mode routing

| MODE | Action |
| --- | --- |
| plan-only | Explore + plan; no writes unless upgraded |
| implement | Edit + focused tests |
| audit | Render `prompt.audit.cycle` |
| closeout | Render `prompt.closeout.grok` or use skill `bioetl-closeout` |
| ci-rebind | Coupled `refresh-ci-drift-families`; reuse existing worktree; memory `off` |

Render helpers:

```powershell
.\.venv-win\Scripts\python.exe -m scripts.ai.prompts render prompt.session.grok-bootstrap `
  --param TASK="..." --param MODE=implement --param SCOPE="..."
```

Do not invent telemetry or test-governance SHA; use `prompt.session.grok-bootstrap`
(includes `prompt.fragment.generated-artifact-ci`).

After merge, reinstall local Grok skills with `.\scripts\ai\grok\install_skills.ps1`.
Do not commit `~/.grok/skills`.

## Guardrails (do not restate full RULES)

- No `.env` create/edit/delete without explicit approval
- No tech-debt budget / exemption / threshold increases
- No root scratch (`_tmp_*.py`, `nul`/`NUL`)
- After markdown link or `Owner:` / `Status:` / `Class:` header changes, run
  `python -m scripts.docs generate-cleanup-inventory --update` in the same
  changeset (`--check` reads the working tree, not HEAD)
- No `reset --hard`, force-push, or commits to `main`
- Protect foreign uncommitted WIP; `git worktree list` then reuse; add only if missing
- Answer in Russian when the operator writes Russian; keep technical literals original

## Done shape

Report: what changed, evidence (paths/commands), tests run, post-change status,
and any `BLOCKED` / `DEGRADED_MCP` notes.
