# Zed Editor Configuration for BioETL Project

Project-local Zed config for BioETL. Source of truth for contracts:

`tests/unit/repo_backed/scripts/test_zed_workspace_config.py`

## Files

| File | Purpose |
|------|---------|
| `settings.json` | Editor, LSP, agent profiles, slim MCP context servers |
| `tasks.json` | `uv`-based quality/test tasks |
| `mcp.json` | Generated full MCP inventory (setup_mcp.py) — not all servers are runtime-enabled in Zed |
| `snippets/` | Optional copy-into-user snippets |
| `README.md` | This guide |

Zed loads `.zed/settings.json` and `.zed/tasks.json` from the worktree root automatically.

## Design principles (optimized)

1. **Delegate tool config to the repo** — Ruff uses `configurationPreference: filesystemFirst` (`pyproject.toml`).
2. **Cheap diagnostics** — basedpyright `diagnosticMode: openFilesOnly` (full check via tasks/CI).
3. **Slim agent MCP** — runtime `context_servers`: only `memory`, `fetch`, `deepwiki`.
4. **Safe defaults** — terminal tool confirms; secrets/certs denied for file tools; `redact_private_values`.
5. **Tasks via `uv`** — reproducible env; `cwd: $ZED_WORKTREE_ROOT`.
6. **No autosave thrash** — `autosave: on_focus_change` (better on network/GDrive mounts).

## Python environment

```bash
# Prefer uv (matches tasks)
uv sync --group dev

# Or classic venv
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Zed detects `.venv` via the toolchain selector.

## LSP

| Server | Role |
|--------|------|
| **basedpyright** | Types / navigation (`strict`, open files only) |
| **ruff** | Format + lint (config from `pyproject.toml`) |
| **pylsp** | Explicitly disabled (`!pylsp`) |

Full typecheck: task **Type check** → `uv run mypy src/`.

## Agent profiles

| Profile | Use |
|---------|-----|
| **BioETL Ask** | Read/search/fetch only; no terminal/edits; no MCP |
| **BioETL Write** | Edits + terminal (confirm) + MCP allowlist `memory`/`fetch`/`deepwiki` |

Secret-bearing MCP (GitHub, Brave, Neo4j, Grafana, …) belongs in **user** Zed settings / env — not in this repo.

Do **not** put API tokens in `settings.json` as plain text. Rotate any key that was stored that way.

### Permissions (high level)

- Terminal: default **confirm**; deny `rm -rf /`, `sudo rm`; confirm `git push`, `sudo`, `.env` paths
- File tools: deny `.env`, `secrets/`, `.pem`/`.key`/`.cert`/`.crt` (and `.git` for delete/move)
- `vim_mode: false` in project so Agent Panel input stays editable

## Tasks (Command Palette → Tasks)

All tasks: `command: uv`, `cwd: $ZED_WORKTREE_ROOT`.

**Quality**

- Format code — `uv run ruff format .`
- Lint code — `uv run ruff check .`
- Type check — `uv run mypy src/`
- Architecture compliance — `uv run lint-imports --config pyproject.toml`
- Refresh MCP config — `uv run python scripts/ai/codex/setup_mcp.py ...`

**Tests**

- **Test: current file** (`python-test` tag) — `uv run pytest $ZED_FILE -v`
- Run unit / integration / architecture / E2E smoke / fast unit / coverage

**Security / hygiene**

- Security scan, dependency audit, dead code, complexity

CLI agents (Codex, Devin, Grok) run from a **Terminal thread** in Agent Panel — not as project tasks.

## MCP

| Surface | Role |
|---------|------|
| `.zed/settings.json` → `context_servers` | What Agent Panel actually starts |
| `.zed/mcp.json` | Generated inventory (setup_mcp) |
| Shared `.mcp.json` | Cross-tool manifest |

Refresh:

```bash
uv run python scripts/ai/codex/setup_mcp.py --skip-codex --skip-gemini-settings
```

Or task **Refresh MCP config**. After regenerate, keep Zed runtime servers slim (`memory` / `fetch` / `deepwiki` only).

## Snippets

Zed does not auto-load `.zed/snippets/*.json`. Copy into user snippets (Settings → Snippets) if needed.

Python snippets require `from __future__ import annotations` and avoid retired APIs.

## Formatting

- Line length 88 (soft wrap); Ruff E501 migration target 120 in `pyproject.toml`
- Format on save: Python/YAML/JSON on; Markdown off
- Organize imports via Ruff on format (no `fixAll` on save)

## Troubleshooting

| Issue | Action |
|-------|--------|
| LSP quiet | Select `.venv` / `uv` toolchain; confirm basedpyright + ruff |
| Slow on GDrive | Expected; prefer local clone; openFilesOnly already set |
| Tasks missing | Reload window; check `.zed/tasks.json` is array of objects |
| Agent cannot send | Sign in / pick model (`agent: open settings`) |
| MCP red | Node/`uvx` installed; caches under `.cache/` |

## Related

- `docs/00-project/RULES.md`
- `docs/00-project/ai/mcp-governance.md`
- `scripts/ai/codex/setup_mcp.py`
- https://zed.dev/docs/
