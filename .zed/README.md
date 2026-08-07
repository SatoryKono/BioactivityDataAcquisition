# Zed Editor Configuration for BioETL Project

Project-local Zed config for BioETL. Source of truth for contracts:

`tests/unit/repo_backed/scripts/test_zed_workspace_config.py`

## Support contract (Windows first)

| Mode | Status | Notes |
|------|--------|--------|
| **Native Windows Zed** | **Canonical / supported** | Tracked `.zed/tasks.json` invokes `.venv-win/Scripts/python.exe` directly. |
| **WSL / Linux Zed** | CLI wrappers only | Project tasks are **not** a cross-platform task set. Use `setup_env_wsl.sh` + `run_pytest.sh` / `run_mypy.sh` from a WSL shell. |
| Dual-OS checkout | Supported with **separate** venvs | Never share one venv between PowerShell and WSL. |

Native Windows recovery and bootstrap:

```powershell
.\scripts\engineering\dev\setup_env_windows.ps1
# Task: Environment: verify
```

WSL / Linux recovery:

```bash
bash scripts/engineering/dev/setup_env_wsl.sh
bash scripts/engineering/dev/run_pytest.sh tests/smoke --narrow --timeout=120
```

`basedpyright` project config may pin `venv = ".venv-win"` for Windows analysis.
That does **not** imply WSL task parity; WSL development stays on repository shell wrappers.

## Files

| File | Purpose |
|------|---------|
| `settings.json` | Editor, LSP, agent profiles (**no agent MCP**), terminal/venv |
| `tasks.json` | Quality/test tasks via `.venv-win` (+ doctor-guarded launcher) |
| `mcp.json` | Optional workspace MCP inventory (prefer shared HTTP plane; not attached to Agent profiles) |
| `USER_SETTINGS_NO_AGENT_MCP.overlay.json` | Snippet for user-level Zed settings (disable extension MCP + thrash agents) |
| `snippets/` | Canonical bioetl-* snippets (repo SSOT; user mirror may be needed) |
| `README.md` | This guide |

Zed loads `.zed/settings.json` and `.zed/tasks.json` from the worktree root automatically.

## Login / account (Zed AI)

Zed **does not** expose a CLI `login` subcommand in current Windows builds
(`zed --help` is open-path only). Account auth is **in-app**:

1. Install/open Zed (`zed .` from the repo root, or the Start-menu app).
2. Use the account control (status bar / title-bar avatar) → **Sign in**.
3. Complete browser OAuth at [zed.dev](https://zed.dev) (GitHub or email).
4. Confirm Agent Panel can send: Command Palette → `agent: open settings` →
   pick a model. Project `settings.json` keeps `"show_sign_in": true`.
5. For **zed.dev** hosted models, a Zed subscription/plan that includes Agent
   is required; local/OpenAI-compatible providers use keys in **user** settings
   only (never commit tokens).

**Host checklist (this machine):**

| Check | Expected |
|-------|----------|
| CLI on PATH | `%LOCALAPPDATA%\Programs\Zed\bin\zed.exe` |
| Project config | `.zed/settings.json`, `.zed/tasks.json` |
| User config | `%APPDATA%\Zed\settings.json` (machine-local; may hold keys) |
| Agent MCP thrash | Apply `USER_SETTINGS_NO_AGENT_MCP.overlay.json` so extension MCP stays off |
| Python toolchain | `.venv-win` after `setup_env_windows.ps1` |
| Environment | Task **Environment: verify** exits 0 |

If Agent shows “Sign in” or cannot send: sign in again, reload window, then
re-select the default model. Do **not** paste API tokens into project `.zed/`.

## Environment doctor (P0)

Tracked quality tasks expect a complete `.venv-win` with the developer extras.

| Task / helper | Behavior |
|---------------|----------|
| **Environment: verify** | Read-only doctor (`scripts/engineering/dev/zed_env_doctor.py`) |
| `zed_run.py` | Doctor, then `python -m <tool>` or a helper script |
| `zed_pytest_lane.py`, `zed_lint_imports.py`, `zed_vulture.py`, `zed_xenon.py`, `zed_mypy.py` | Call `ensure_ready()` before tool imports |

Missing `.venv-win` or packages (e.g. `importlinter`) produce an actionable
diagnostic and non-zero exit — **not** a raw architecture traceback.

Routine tasks **do not** auto-install dependencies. Recover with:

```powershell
.\scripts\engineering\dev\setup_env_windows.ps1
```

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

## Design principles

1. **Delegate tool config to the repo** — Ruff uses `configurationPreference: filesystemFirst` (`pyproject.toml`).
2. **Cheap diagnostics** — basedpyright `diagnosticMode: openFilesOnly` (full check via tasks/CI).
3. **No agent-attached MCP by default** — `context_servers: {}` and both BioETL agent profiles set `enable_all_context_servers: false`.
4. **Safe defaults** — global Agent permission default is `confirm`; secrets/certs denied; `redact_private_values`.
5. **Tasks without `uv` on PATH** — call `$ZED_WORKTREE_ROOT/.venv-win/Scripts/python.exe ...` (never bare `uv` / `uv run` in tasks).
6. **PowerShell-safe pytest markers** — multi-word `-m` expressions live in `zed_pytest_lane.py`.
7. **No autosave thrash** — `autosave: on_focus_change`; global `format_on_save: off` (Python off; YAML/JSON/Compose on).
8. **Local pytest defaults** — `VCR_RECORD_MODE=none`, `--no-cov` on non-coverage lanes, gutter runnables on.
9. **Windows dual-OS env detection** — terminal prefers `.venv-win`, then `.venv`, then `.venv-wsl`.

## Python environment

```powershell
# Windows (canonical for native Zed on Windows)
.\scripts\engineering\dev\setup_env_windows.ps1
# Toolchain to select in Zed: .venv-win
```

```bash
# WSL / Linux (CLI wrappers; not project Zed tasks)
bash scripts/engineering/dev/setup_env_wsl.sh
```

In Zed (Windows):

1. Open a Python file.
2. Status bar → **toolchain selector** → choose `.venv-win`.
3. Terminal auto-activates via `terminal.detect_venv` (prefers `.venv-win`).
4. Run **Environment: verify**.

## LSP

| Server | Role |
|--------|------|
| **basedpyright** | Types / navigation (`strict`, open files only) |
| **ruff** | Format + lint (config from `pyproject.toml`) |
| **docker-compose** | Compose completion/validation via `microsoft/compose-language-service` |
| **pylsp** | Explicitly disabled (`!pylsp`) |

Full typecheck: task **Check: types** → mypy on `src/bioetl` (same product gate as CI).

## Running tests in Zed

### Gutter runnables (fastest)

1. Open a file under `tests/**/*.py`.
2. Click the **play** icon next to a `test_*` / class.
3. Bound task: **Test: current file** → `zed_pytest_lane.py file $ZED_FILE`.

### Task picker

Command Palette → **task: spawn**:

| Task | What it runs | Authority |
|------|----------------|-----------|
| **Test: current file** | Active buffer | local |
| **Test: nearest symbol** | `$ZED_FILE -k $ZED_SYMBOL` | local |
| **Test: smoke** | matrix `smoke` | local projection of matrix |
| **Test: unit-fast** | matrix `unit-fast` | local projection of matrix |
| **Test: unit** | full `tests/unit/` convenience | local only |
| **Test: architecture-fast** | matrix `architecture-fast-boundary` | local projection |
| **Test: integration-replay** | matrix `integration-replay` + VCR none | local projection |
| **Test: contracts** | matrix `contracts` | local projection |
| **Test: security** | matrix `security` | local projection |
| **Test: e2e-smoke** | matrix `e2e-smoke` bounded files | local projection |
| **Test: failed last run** | `--lf` | local |
| **Coverage: local estimate (85%)** | advisory coverage estimate | **not** `coverage-verify` |

Canonical suite definitions: `configs/quality/test_matrix.yaml`.
Zed labels are **local UX shortcuts**; merge-blocking coverage remains the
sharded `coverage-verify` lane / CI, not the Zed estimate task.

Common flags on local test tasks:

- `--no-cov` (except coverage estimate)
- `-p no:benchmark`
- `VCR_RECORD_MODE=none`
- `--maxfail=1` / `-q` / `--tb=short` where appropriate

### CLI wrappers (WSL / when tasks are not enough)

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
| **BioETL Ask** (default) | Read/search/fetch only; no terminal/edits; no MCP |
| **BioETL Write** | Edits + terminal (confirm) + empty project MCP attachment |

Project Agent profiles keep `context_servers: {}` and
`enable_all_context_servers: false`. Secret-bearing MCP belongs in **user**
settings / the shared HTTP plane — not in this repo.

### Permissions (native Windows)

- Global tool default: **confirm** (unlisted tools are not implicitly allowed)
- Read/search/fetch tools: **allow** (low friction in Ask)
- File mutators: **confirm**, with unconditional deny for `.env`, `secrets/`, keys/certs
- Terminal: **confirm**; deny Unix `rm -rf`, PowerShell `Remove-Item -Recurse/-Force`,
  `rmdir /s`, `del /s`, `git clean -f*`, `git reset --hard`, force-push patterns;
  confirm `git push`, `sudo`, `.env` paths, broader `Remove-Item`/`del`/`git reset`
- `spawn_agent`: disabled on both profiles
- Zed terminal sandboxing on Windows applies only to actions inside WSL; native
  PowerShell safety depends on these permission rules

Do **not** put API tokens in `settings.json` as plain text.

## Tasks (behavior policy)

All tasks: `cwd: $ZED_WORKTREE_ROOT`, interpreter under `.venv-win/Scripts/`.

| Category | `save` | `reveal` | `hide` | concurrent |
|----------|--------|----------|--------|------------|
| Current-file / nearest | `current` | `always` | `never` | false |
| Fast checks (lint, MCP check, env verify) | `all` / `none` | `no_focus` or `always` | `on_success` | false |
| Long tests / audits / generate | `all` | `always` | `never` | false |
| Format | `all` | `always` | `on_success` | false |

**Quality**

- Format: code — `zed_run.py -m ruff format .`
- Check: lint — `zed_run.py -m ruff check src tests scripts`
- Check: types — `zed_run.py -m mypy --config-file pyproject.toml src/bioetl`
- Check: architecture imports — `zed_lint_imports.py` (contracts in `.importlinter`)
- Environment: verify — `zed_env_doctor.py`

**Security / hygiene**

- Audit: security — bandit with `pyproject.toml`
- Audit: dependencies — `pip_audit --skip-editable`
- Audit: dead code — `zed_vulture.py`
- Audit: complexity — `zed_xenon.py`

**MCP**

- Check: MCP manifests — `setup_mcp.py --check` (read-only, no writes)
- Generate: MCP tracked manifests — regenerates tracked portable projections

CLI agents (Codex, Devin, Grok) run from a **Terminal** thread — not as project tasks.

## MCP

| Surface | Role |
|---------|------|
| `.zed/settings.json` → `context_servers` | What Agent Panel starts (empty by default) |
| `.zed/mcp.json` | Generated portable inventory (`bash` + `.sh` wrappers) |
| Shared `.mcp.json` | Cross-tool portable SSOT |

Read-only parity:

```powershell
.\.venv-win\Scripts\python.exe scripts\ai\codex\setup_mcp.py --check --skip-codex --skip-gemini-settings
```

Regenerate (mutating):

```powershell
.\.venv-win\Scripts\python.exe scripts\ai\codex\setup_mcp.py --skip-codex --skip-gemini-settings
```

Tracked portable inventory always uses POSIX wrappers (`bash` + `.sh`) so
Windows and Linux checkouts share one deterministic SSOT.

## Snippets

Zed does **not** auto-load `.zed/snippets/*.json`. Copy into **user** snippets
(Settings → Snippets) if needed. Installation is optional and non-destructive.

Python snippets require `from __future__ import annotations` and avoid retired APIs.

## Formatting and file scan

| Setting | Value |
|---------|-------|
| Global `tab_size` | `4` |
| YAML / JSON / JSONC / Compose | `tab_size: 2` |
| Global `format_on_save` | `off` |
| Python / Markdown format on save | `off` |
| YAML / JSON / JSONC / Compose format on save | `on` |
| Autosave | `on_focus_change` (does not reformat Python) |
| Soft wrap | preferred line length 88 |

Scan exclusions include local venvs/caches (`.venv-win`, `.venv-wsl`, `.cache`,
`.worktrees`) and the large tracked debug export tree `data/debug_exports`
(discoverability tradeoff: hide heavy debug dumps from project search; other
`data/**` and `reports/**` remain navigable).

## Troubleshooting

| Issue | Action |
|-------|--------|
| `ModuleNotFoundError: importlinter` | Run **Environment: verify**, then `setup_env_windows.ps1` |
| Missing `.venv-win` | `.\scripts\engineering\dev\setup_env_windows.ps1` |
| `uv` not recognized | Expected: tasks never call `uv`. Use `.venv-win` python |
| Wrong interpreter | Toolchain selector → `.venv-win` |
| LSP quiet / bad imports | Same toolchain; `editor: restart language server` |
| Compose files use generic YAML | Reload so **Docker Compose** extension installs; restart LS |
| Slow on cloud sync | Prefer local clone; `openFilesOnly` already set |
| Tasks missing | Reload window; `.zed/tasks.json` must be a JSON array |
| Runnable play missing | `gutter.runnables: true`; open a `test_*.py` buffer |
| VCR / network flakes | Local tasks force `VCR_RECORD_MODE=none` |
| Coverage slow / CI mismatch | Use non-coverage tasks; estimate is advisory only |
| Agent cannot send | Sign in / pick model (`agent: open settings`) |
| MCP red | Prefer shared HTTP plane; project Agent MCP stays empty |

## Related

- `docs/00-project/RULES.md`
- `docs/03-guides/testing.md`
- `docs/00-project/ai/mcp-governance.md`
- `configs/quality/test_matrix.yaml`
- `scripts/ai/codex/setup_mcp.py`
- `scripts/engineering/dev/setup_env_windows.ps1`
- `scripts/engineering/dev/zed_env_doctor.py`
- `scripts/engineering/dev/zed_run.py`
- `scripts/engineering/dev/zed_pytest_lane.py`
- `scripts/engineering/dev/run_pytest.ps1` / `run_pytest.sh`
- https://zed.dev/docs/tasks
- https://zed.dev/docs/languages/python

## Canonical LSP stack (project)

| Language | Server | Role | CI gate |
|----------|--------|------|---------|
| Python | **basedpyright** | semantic/types/navigation | IDE; product gate remains **mypy** |
| Python | **ruff** | lint + format + organize imports | pre-commit + CI |
| YAML | default YAML language server | schema/diagnostics | — |
| JSON/JSONC | default JSON language server | format/diagnostics | — |
| Docker Compose | docker-compose | compose diagnostics | — |

**Not active in project Python `language_servers`:** `pylsp`, legacy `ruff-lsp` (native `ruff` server), `ty`, second pyright flavor.

Do not enable multiple Python semantic servers together.

## Snippets (`bioetl-*`)

Tracked under `.zed/snippets/`. In current Zed builds, project snippets may need to be
mirrored into user snippet config depending on version; the tracked files remain the
**repo source of truth** and are guarded by `test_zed_workspace_config.py`.

### Required Python prefixes

| Prefix | Layer |
|--------|--------|
| `bioetl-vo` | domain |
| `bioetl-port` | domain |
| `bioetl-impl` | infrastructure |
| `bioetl-config` | domain/config |
| `bioetl-factory` | composition |
| `bioetl-error` | domain |
| `bioetl-test-unit` / `bioetl-test-async` / `bioetl-test-arch` | tests |
| `bioetl-extract` / `bioetl-transform` / `bioetl-validate` / `bioetl-export` | pipelines |
| `bioetl-log` | application via LoggerPort |
| `bioetl-event` | domain events |

### Required YAML prefixes

| Prefix | Source shape |
|--------|----------------|
| `bioetl-pipeline-config` | `configs/entities/*` |
| `bioetl-dq-rule` | entity quality ranges/required_fields |
| `bioetl-retry-policy` / `bioetl-rate-limit` | `configs/providers/*` |
| `bioetl-composite-enricher` / `bioetl-field-priority` | ADR-026 composites |

Snippets must not invent retired paths (`bioetl.pipelines`, `data/silver`, parquet sinks) or use `print()`.
