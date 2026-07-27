# Zed Editor Configuration for BioETL Project

Project-local Zed config for BioETL. Source of truth for contracts:

`tests/unit/repo_backed/scripts/test_zed_workspace_config.py`

## Files

| File | Purpose |
|------|---------|
| `settings.json` | Editor, LSP, agent profiles (**no agent MCP**), terminal/venv |
| `tasks.json` | `uv`-based quality/test tasks (pytest lanes + runnables) |
| `mcp.json` | Optional workspace MCP inventory (prefer shared HTTP plane; not attached to Agent profiles) |
| `USER_SETTINGS_NO_AGENT_MCP.overlay.json` | Snippet for user-level Zed settings (disable extension MCP + thrash agents) |
| `snippets/` | Optional copy-into-user snippets |
| `README.md` | This guide |

Zed loads `.zed/settings.json` and `.zed/tasks.json` from the worktree root automatically.

## Agent without MCP thrash

**Problem:** Zed External Agent `grok-build` runs `grok agent stdio`, and user-level
`context_servers` (Brave / Context7 extensions) get started as stdio children —
often in parallel with the BioETL shared HTTP plane → N× MCP processes.

**Project defaults (this repo):**

- `context_servers: {}`
- profiles `bioetl-ask` / `bioetl-write`: `enable_all_context_servers: false`, empty `context_servers`
- default profile: `bioetl-ask`

**User-level (required once on this host):** apply the overlay in
`USER_SETTINGS_NO_AGENT_MCP.overlay.json` into `%APPDATA%\Zed\settings.json`:

1. Set `context_servers.mcp-server-context7.enabled` / `mcp-server-brave-search.enabled` → `false`
2. Remove or disable External Agent entries that spawn thrash (`grok-build` registry) if Grok TUI already covers MCP via shared HTTP
3. Restart Zed fully (quit all windows)

MCP for coding should stay on:

```powershell
.\scripts\ops\runtime\mcp\start-shared.ps1
.\scripts\ops\runtime\mcp\health-shared.ps1
.\scripts\ops\runtime\mcp\apply-shared-to-grok.ps1 -DisableDockerGateways
```

## Design principles (optimized)

1. **Delegate tool config to the repo** — Ruff uses `configurationPreference: filesystemFirst` (`pyproject.toml`).
2. **Cheap diagnostics** — basedpyright `diagnosticMode: openFilesOnly` (full check via tasks/CI).
3. **No agent-attached MCP by default** — `context_servers: {}` and both
   BioETL agent profiles set `enable_all_context_servers: false` with empty
   `context_servers`. MCP runs on the shared HTTP plane (`scripts/ops/runtime/mcp/`)
   for Grok/Codex CLI, not via Zed Agent / External Agent stdio thrash.
   Optional: enable specific remote MCP later under a profile only when needed.
4. **Safe defaults** — terminal tool confirms; secrets/certs denied for file tools; `redact_private_values`.
5. **Tasks without `uv` on PATH** — call
   `$ZED_WORKTREE_ROOT/.venv-win/Scripts/python.exe ...` directly
   (Zed GUI PowerShell often has no `uv` in PATH).
6. **PowerShell-safe pytest markers** — multi-word `-m` expressions live in
   `scripts/engineering/dev/zed_pytest_lane.py` so `and`/`or` are not re-tokenized
   by `powershell -C` into fake file paths.
7. **No autosave thrash** — `autosave: on_focus_change` (better on network/GDrive mounts).
8. **Local pytest defaults** — `VCR_RECORD_MODE=none`, `--no-cov` on non-coverage lanes, gutter runnables on.
9. **Windows dual-OS env** — `VIRTUAL_ENV=.venv-win`; prefer `.venv-win` over broken WSL `.venv`.

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
| **docker-compose** | Compose completion, validation, hover, and formatting via `microsoft/compose-language-service` |
| **pylsp** | Explicitly disabled (`!pylsp`) |

Docker Compose support uses the community **Docker Compose** extension
(`eth0net/zed-docker-compose`). The project declares it in
`auto_install_extensions`, so Zed installs or updates it when the workspace
loads. Project `file_types` map root
`docker-compose*.yml` / `compose*.yml` manifests and the repository's
`scripts/ops/**` Compose manifests to the dedicated language server instead of
generic YAML.

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
- Lint code — `python -m ruff check src tests scripts`
  (uses `[tool.ruff]` from `pyproject.toml`; CI full gate is `src tests`,
  scripts match pre-commit advisory scope)
- Type check — `python -m mypy --config-file pyproject.toml src/bioetl`
  (same product gate as `.github/workflows/type-checking.yml`; not bare `mypy src/`)
- Architecture compliance — `python scripts/engineering/dev/zed_lint_imports.py` (contracts in `.importlinter`)
- Refresh MCP config — `python scripts/ai/codex/setup_mcp.py ...`

**Tests** — see table above.

**Security / hygiene**

- Security scan — `python -m bandit -c pyproject.toml -r src/bioetl`
  (same as pre-commit; skips B101/B104/B311; not bare `bandit -r src/`)
- Dependency audit — `python -m pip_audit --skip-editable --cache-dir .cache/pip-audit`
- Dead code — `python scripts/engineering/dev/zed_vulture.py`
  (same filter as architecture `test_dead_code_vulture`: min confidence 80,
  ignore private names / dunders / reserved API params; not bare `vulture`)
- Complexity check — `python scripts/engineering/dev/zed_xenon.py`
  (CI thresholds B/B/A + xenon excludes from
  `configs/quality/duplication_complexity_exemptions.yaml`)

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
| Compose files use generic YAML | Reload Zed so `auto_install_extensions` can update **Docker Compose**, then run `editor: restart language server` |
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
- `scripts/engineering/dev/zed_task.ps1` — optional Windows helper to run
  `pytest`/`ruff`/`mypy` via `.venv-win` without requiring `uv` on PATH
- https://zed.dev/docs/tasks
- https://zed.dev/docs/languages/python
