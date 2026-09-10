# Grok surfaces for BioETL

*Status: internal | Not runtime SSOT*

Machine-local Grok state lives under root `.grok/` (gitignored — absolute LSP
paths and host config). Tracked sources for operators live here.

## Layout

| Path | Purpose |
| --- | --- |
| `skills/*/SKILL.md` | Project skill sources (install to Grok skill dirs) |
| `agents/*.md` | Tracked Grok child agents (`mcpInheritance.named`, no `github`) |
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

The same script copies `agents/*.md` into `~/.grok/agents/` (or
`<repo>/.grok/agents/` with `-Project`). Root `.grok/` stays gitignored.

After install, start a **new** Grok session (or restart TUI) so skills and
agents are rediscovered. `/config-agents` should list `explore`, `plan`, and
the six `py-*` types. Children must not inherit MCP `github`.

Wave `SUBAGENT-20260910`: parent daily MCP ≤4 live including `github`; child
agents are the eight files in `agents/` (no `implementer` / `obs-dashboard` in
this wave — those are #10318 / #10319).

## Related

- Epic #8274 (Grok TUI config)
- Epic #10313 (subagent least-privilege)
- Prompt library epic #8513
- `AGENTS.md` precedence
