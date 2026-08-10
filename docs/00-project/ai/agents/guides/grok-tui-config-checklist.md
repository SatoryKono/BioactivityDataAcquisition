# Grok TUI Config Checklist (operator host)

*Status: internal | Checklist for `~/.grok/config.toml` — never commit secrets*

Use with [grok-operator-runbook.md](grok-operator-runbook.md). Tracks epic #8274.

## Before change

- [ ] Backup: `cp ~/.grok/config.toml ~/.grok/config.toml.bak-YYYYMMDD`
- [ ] Confirm trusted folder includes BioETL checkout

## P0 Permissions (#8275)

- [ ] `permission_mode = "ask"` (default)
- [ ] `remember_tool_approvals = true`
- [ ] `default_selected_permission = "allow_once"`
- [ ] `yolo = false`
- [ ] Ship profile documented as temporary exception only

## P1 MCP slim (#8276)

Always-on (≤8):

- [ ] github
- [ ] fetch
- [ ] brave-search (optional if web_search enough)
- [ ] context7
- [ ] ast-grep
- [ ] code-analyzer
- [ ] memory

Disabled by default (enable on demand): docker, grafana, prometheus, mutmut,
github-actions, deepwiki, ref, neo4j-*, mermaid, deja, adr-analysis,
mcp-code-interpreter, filesystem, dockerhub

- [ ] `startup_timeout_sec` ≤ 45 for local daemons
- [ ] No API keys in git

## P2 Models/session (#8277)

- [ ] `[models] default` / `web_search` pinned
- [ ] `temperature` ≤ 0.3 for closeout sessions
- [ ] `auto_compact_threshold_percent` ≤ 80

## P3 Tools (#8278)

- [ ] `respect_gitignore = true`
- [ ] `[toolset.bash] timeout_secs` ≥ 180 for BioETL pytest comfort

## P5 LSP (#8280)

- [ ] `.venv-win/Scripts/basedpyright-langserver.exe` exists
- [ ] `.grok/lsp.json` paths still valid for this checkout

## P6 Skills + prompts (#8279 / #8513)

- [ ] `.\scripts\ai\grok\install_skills.ps1` (user) or `-Project`
- [ ] Skills present: `bioetl-session`, `bioetl-closeout`, `bioetl-post-change`
- [ ] Prompt render smoke:
  `.\.venv-win\Scripts\python.exe -m scripts.ai.prompts render prompt.session.grok-bootstrap --param TASK=smoke --param MODE=plan-only --param SCOPE=docs`

## After change

- [ ] Restart Grok TUI / new session
- [ ] Spot-check: permission prompt appears for risky bash
- [ ] Spot-check: MCP list matches slim profile
- [ ] Spot-check: skills listed / invocable after restart
