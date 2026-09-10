# Grok TUI Config Checklist (operator host)

*Status: internal | Checklist for `~/.grok/config.toml` — never commit secrets*

Use with [grok-operator-runbook.md](grok-operator-runbook.md). Tracks epic #8274
and wave `SUBAGENT-20260910` (#10313).

## Before change

- [ ] Backup: `cp ~/.grok/config.toml ~/.grok/config.toml.bak-YYYYMMDD`
- [ ] Confirm trusted folder includes BioETL checkout

## P0 Permissions (#8275)

- [ ] `permission_mode = "ask"` (default)
- [ ] `remember_tool_approvals = true`
- [ ] `default_selected_permission = "allow_once"`
- [ ] `yolo = false`
- [ ] Ship profile documented as temporary exception only

## P1 MCP slim (#8276 / #10314 SUBAGENT-01)

Daily parent always-on (**≤4 live**, including `github`):

- [ ] github (required; GitHub write stays on the parent orchestrator)
- [ ] ast-grep
- [ ] code-analyzer
- [ ] context7 (keep in the target set; **disable** if handshake FAIL — do not
      hold a dead server "just in case")

Optional only if actually connected: `memory` (MCP file, not
`python -m memory.tooling.workflow`), `fetch`.

**Not** daily parent (named-inherit only on `obs-dashboard` later, #10319):
`grafana`, `prometheus`.

Disabled for BioETL daily (all agents except explicit opt-in): `filesystem`,
`docker`, `grafana`, `prometheus`, `neo4j-cypher`, `neo4j-memory`, `mermaid`,
`mutmut`, `mcp-code-interpreter`, `github-actions`, `deepwiki`, `ref`,
`brave-search`, `deja`, `adr-analysis`, `google_drive`, `tasks`.

- [ ] FAIL handshake servers are **off**, not left enabled
- [ ] `startup_timeout_sec` ≤ 45 for local daemons
- [ ] No API keys in git
- [ ] Do not commit `~/.grok/config.toml`

## P1b Grok skills (#10314)

Enabled on parent (≤7): `bioetl-session`, `bioetl-closeout`,
`bioetl-post-change`, `long-running-background-tasks`, `pr-babysit`, `review`,
`gh-address-comments`.

`[skills] disabled` MUST include: `pc-agent-session`, `cloudflare-deploy`,
`vercel-deploy`, `render-deploy`, `frontend-design`, `playwright`, `screenshot`,
`doc`, `docx`, `pdf`, `pptx`, `imagegen`, `imagine`, `skill-creator`,
`skill-installer`, `create-skill`, `create-workflow`, `build-with-ai`, `design`,
`execute-plan`, `resume-claude`, `resume-codex`, `resume-cursor`, `statusline`,
`learn`.

Do not copy all 14 `.codex/skills` into `~/.grok/skills`.

Child agents: see [../../grok/agents/](../../grok/agents/). Install with
`.\scripts\ai\grok\install_skills.ps1`. Children use `mcpInheritance.named`
**without** `github` and must not run `gh`.

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
- [ ] `grok inspect` (or `/context`): connected MCP ⊆ daily core 4 (or fewer if
      `context7` is dead); **`github` connected on parent**
- [ ] `google_drive` / `tasks` / neo4j / grafana / deepwiki **not** connected
- [ ] `[skills] disabled` covers the non-BioETL list; `pc-agent-session` does
      not auto-invoke
- [ ] Child spawn (`explore` / `py-audit-bot`): no MCP `github`; no `gh`
- [ ] `python scripts/ai/codex/doctor.py static --no-write`
- [ ] `python scripts/ai/codex/setup_mcp.py --check`
- [ ] `bash scripts/ai/junie/check_junie_mirror.sh --check` after `.codex`/`.junie` edits
- [ ] Spot-check: permission prompt appears for risky bash
- [ ] `~/.grok/config.toml` still untracked
