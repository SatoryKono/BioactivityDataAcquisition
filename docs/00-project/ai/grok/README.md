# Grok surfaces for BioETL

*Status: internal | Not runtime SSOT*

Machine-local Grok state lives under root `.grok/` (gitignored — absolute LSP
paths and host config). Tracked sources for operators live here.

## Layout

| Path | Purpose |
| --- | --- |
| `skills/*/SKILL.md` | Project skill sources (install to Grok skill dirs) |
| `agents/*.md` | Tracked Grok child agents (`mcpInheritance.named`, no `github`) |
| `personas/*.toml` | Overlay personas (no tools/MCP; enable via `/personas`) |
| `../agents/guides/grok-operator-runbook.md` | Operator SOP |
| `../agents/guides/grok-tui-config-checklist.md` | `~/.grok/config.toml` checklist |
| `../agents/guides/grok-lsp-status.md` | LSP binary status notes |
| `../prompts/library/session/grok-bootstrap.md` | Session paste card |
| `../prompts/library/audit/grok-audit-cycle.md` | Audit paste card |
| `../prompts/library/closeout/grok-closeout.md` | Closeout paste card |

## Install skills

```powershell
# User-wide (default): ~/.grok/skills/<name>/SKILL.md
.\scripts\ai\grok\install_skills.ps1

# Project-local: <repo>/.grok/skills/ (still gitignored)
.\scripts\ai\grok\install_skills.ps1 -Project

# Dry run
.\scripts\ai\grok\install_skills.ps1 -WhatIf
```

The same script copies `agents/*.md` into `~/.grok/agents/` and
`personas/*.toml` into `~/.grok/personas/` (or `<repo>/.grok/` with
`-Project`). Root `.grok/` stays gitignored.

After install, start a **new** Grok session (or restart TUI) so skills,
agents, and personas are rediscovered. `/config-agents` should list `explore`,
`plan`, the six `py-*` types, plus Grok-only `implementer` and `obs-dashboard`.
Children must not inherit MCP `github`.

### When to spawn

| Type | Use when | Not for |
| --- | --- | --- |
| parent / `general-purpose` | GitHub write, closeout, `gh`, merge/push; hash-only / date-stamp / remote-main rebind in the **existing** worktree | long product patches in the orchestrator context |
| `py-config-bot` | `configs/**` contracts | product `src/` patches |
| `implementer` | bounded **product/docs** write in a worktree of a **new** branch; parent merges. Reuse the same-branch worktree; do not add a second copy | `gh` / `git push` / GitHub MCP; hash-only SHA rebind; date-stamp-only dataflow |
| `obs-dashboard` | dashboard JSON / PromQL with grafana+prometheus MCP | daily parent session; starting monitoring compose unless asked |
| `py-debug-bot` / `explore` | RCA | patches (use `rca-handoff` overlay, then parent or `implementer`) |

Personas are overlays, not `spawn_subagent` types. After install, pick in
`/personas`:

| Persona | Overlay on | Contract |
| --- | --- | --- |
| `rca-handoff` | `py-debug-bot` / `explore` | `DBG-*` table; no patch; no `gh` |
| `closeout-table` | parent | Issue / Verdict / SHA/PR / Checks; GitHub-write stays parent |

Wave `SUBAGENT-20260910` E–G: Grok-only `implementer` (#10318),
`obs-dashboard` (#10319), personas (#10320). Governed `py-*` catalog stays **6**.

## Related

- Epic #8274 (Grok TUI config)
- Epic #10313 (subagent least-privilege)
- Prompt library epic #8513
- `AGENTS.md` precedence
