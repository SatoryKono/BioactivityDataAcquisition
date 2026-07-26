# Zed Editor Configuration for BioETL Project

Project-local Zed config for BioETL. Source of truth for contracts:

`tests/unit/repo_backed/scripts/test_zed_workspace_config.py`

## Files

| File | Purpose |
|------|---------|
| `settings.json` | Editor, LSP, agent profiles, slim MCP context servers, terminal/venv |
| `tasks.json` | `uv`-based quality/test tasks (pytest lanes + runnables) |
| `mcp.json` | Generated full MCP inventory (setup_mcp.py) — not all servers are runtime-enabled in Zed |
| `snippets/` | Optional copy-into-user snippets |
| `README.md` | This guide |

Zed loads `.zed/settings.json` and `.zed/tasks.json` from the worktree root automatically.

## Design principles (optimized)

1. **Delegate tool config to the repo** — Ruff uses `configurationPreference: filesystemFirst` (`pyproject.toml`).
2. **Cheap diagnostics** — basedpyright `diagnosticMode: openFilesOnly` (full check via tasks/CI).
3. **Slim agent MCP** — runtime `context_servers`: only `memory`, `fetch`, `deepwiki`.
4. **Safe defaults** — terminal tool confirms; secrets/certs denied for file tools; `redact_private_values`.
5. **Tasks without `uv` on PATH** — call
   `$ZED_WORKTREE_ROOT/.venv-win/Scripts/python.exe -m pytest ...` directly
   (Zed GUI PowerShell often has no `uv` in PATH).
6. **No autosave thrash** — `autosave: on_focus_change` (better on network/GDrive mounts).
7. **Local pytest defaults** — `VCR_RECORD_MODE=none`, `--no-cov` on non-coverage lanes, gutter runnables on.
8. **Windows dual-OS env** — `VIRTUAL_ENV=.venv-win`; prefer `.venv-win` over broken WSL `.venv`.

## Python environment

Dual-OS layout (do **not** share one venv between Windows and WSL):

```powershell
# Windows (canonical for native Zed on Windows)
.\scripts\engineering\dev\setup_env_windows.ps1
# Toolchain to select in Zed: .venv-win
```

```bash
# WSL / Linux
bash scripts/engineering/dev/setup_env_wsl.sh
# Prefer $HOME/.venvs/bioetl or .venv-wsl when present
```

Or with `uv` extras used by quality gates:

```bash
uv sync --extra dev --extra tests --extra tracing
```

In Zed:

1. Open a Python file.
2. Status bar → **toolchain selector** → choose `.venv-win` (Windows) or the WSL/Linux venv.
3. Terminal auto-activates via `terminal.detect_venv` (prefers `.venv-win`, then `.venv`, then `.venv-wsl`).

## LSP

| Server | Role |
|--------|------|
| **basedpyright** | Types / navigation (`strict`, open files only) |
| **ruff** | Format + lint (config from `pyproject.toml`) |
| **pylsp** | Explicitly disabled (`!pylsp`) |

Full typecheck: task **Type check** → `uv run mypy src/`.

## Running tests in Zed

### Gutter runnables (fastest)

1. Open a file under `tests/**/*.py`.
2. Click the **play** icon in the gutter next to a `test_*` / class, or use **editor: toggle code actions** on that line.
3. Bound task: **Test: current file** (`tags: ["python-test"]`) → `uv run pytest $ZED_FILE ...`.

### Task picker

Command Palette → **task: spawn** (default often `Ctrl+Shift+T` / `Cmd+Shift+T` depending on keymap):

| Task | What it runs |
|------|----------------|
| **Test: current file** | Active buffer via pytest (`python-test` runnable) |
| **Test: nearest symbol** | `$ZED_FILE -k $ZED_SYMBOL` |
| **Test: smoke** | `tests/smoke/` |
| **Test: unit-fast** | `tests/unit/` without `repo_backed` / `slow` / `serial` / `benchmark` / `memory` |
| **Test: unit** | Full `tests/unit/` |
| **Test: architecture** | Fast architecture slice |
| **Test: integration-replay** | Offline integration (VCR replay) |
| **Test: contracts** | Offline contracts |
| **Test: security** | `tests/security/` |
| **Test: e2e-smoke** | `e2e_smoke` marker |
| **Test: failed last run** | `--lf` |
| **Test: coverage (gate 85%)** | Stable non-e2e/non-contract coverage gate |

Common flags on local test tasks:

- `--no-cov` (except coverage task)
- `-p no:benchmark`
- `VCR_RECORD_MODE=none`
- `--maxfail=1` / `-q` / `--tb=short` where appropriate

Canonical lane names for CI/telemetry live in `configs/quality/test_matrix.yaml`.
Zed task labels are **local UX shortcuts**, not suite telemetry IDs.

### Debug (pytest + debugpy)

F4 / **debugger: start** can attach to pytest if `debugpy` is available in the selected toolchain.
Prefer gutter/task for ordinary runs; use debugger only when stepping is needed.

### CLI wrappers (when tasks are not enough)

```powershell
.\scripts\engineering\dev\run_pytest.ps1 tests\smoke --narrow --timeout=120
.\scripts\engineering\dev\run_tests.ps1 quick
```

```bash
bash scripts/engineering/dev/run_pytest.sh tests/smoke --narrow --timeout=120
python -m scripts.engineering.dev run-tests smoke
```

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

All tasks: `cwd: $ZED_WORKTREE_ROOT`, interpreter/tool binaries under
`.venv-win/Scripts/` (no PATH dependency on `uv`).

**Quality**

- Format code — `python -m ruff format .`
- Lint code — `python -m ruff check .`
- Type check — `python -m mypy src/`
- Architecture compliance — `lint-imports.exe --config pyproject.toml`
- Refresh MCP config — `python scripts/ai/codex/setup_mcp.py ...`

**Tests** — see table above.

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
| `uv` not recognized | Expected: tasks no longer call `uv`. Reload window and re-run task |
| Wrong interpreter | Toolchain selector → `.venv-win` (Windows) or WSL venv |
| Missing `.venv-win` | `.\scripts\engineering\dev\setup_env_windows.ps1` |
| LSP quiet / bad imports | Same toolchain; `editor: restart language server` |
| Slow on GDrive | Expected; prefer local clone; `openFilesOnly` already set |
| Tasks missing | Reload window; check `.zed/tasks.json` is a JSON array |
| Runnable play missing | `gutter.runnables: true`; open a `test_*.py` buffer |
| VCR / network flakes | Local tasks force `VCR_RECORD_MODE=none` |
| Coverage slow | Use non-coverage tasks by default; only **Test: coverage** enables cov |
| Agent cannot send | Sign in / pick model (`agent: open settings`) |
| MCP red | Node/`uvx` installed; caches under `.cache/` |

## Related

- `docs/00-project/RULES.md`
- `docs/03-guides/testing.md`
- `docs/00-project/ai/mcp-governance.md`
- `scripts/ai/codex/setup_mcp.py`
- `scripts/engineering/dev/run_pytest.ps1` / `run_pytest.sh`
- https://zed.dev/docs/tasks
- https://zed.dev/docs/languages/python
