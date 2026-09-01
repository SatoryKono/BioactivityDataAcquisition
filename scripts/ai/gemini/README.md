# Gemini - Coding Agent Launcher

Canonical launcher for Google Gemini CLI from `scripts/ai/gemini`.

This surface mirrors the operational shape of `scripts/ai/codex`: one entrypoint, managed repo-local npm install, explicit `check/setup/update`, WSL proxy support, and portable PowerShell delegation.

## Structure

```text
scripts/ai/gemini/
├── setup.ps1                      # PowerShell setup orchestrator for WSL
├── setup-gemini-wsl.bat           # cmd.exe WSL setup transport
├── launch-gemini-wsl.ps1          # Thin PowerShell alias over run-gemini.ps1
├── run-gemini.ps1                 # PowerShell entrypoint, delegates to WSL
├── run-gemini.sh                  # WSL/Bash entrypoint
├── headless.ps1                   # PowerShell transport that skips MCP sync
├── headless.sh                    # WSL/Bash launcher without MCP sync
├── .env.gemini                    # Local API key config, git-ignored
├── npm-tooling/                   # Integrity-pinned Node/Gemini dependency graph
│   ├── package.json
│   └── package-lock.json
├── helper/
│   ├── check-env.ps1              # PowerShell compatibility check wrapper
│   ├── check-env.sh               # Environment check
│   ├── ensure-gemini-cli.sh       # Managed Gemini CLI bootstrap
│   ├── ensure-mcp.sh              # Sync .gemini/settings.json MCP config
│   ├── setup-env.sh               # Setup managed CLI and env template
│   └── run-gemini-impl.sh         # Runtime launcher implementation
└── README.md
```

## Quick Start

From PowerShell:

```powershell
.\scripts\ai\gemini\setup.ps1
.\scripts\ai\gemini\run-gemini.ps1 check
notepad .\scripts\ai\gemini\.env.gemini
.\scripts\ai\gemini\launch-gemini-wsl.ps1
```

From WSL/Bash:

```bash
bash scripts/ai/gemini/run-gemini.sh check
bash scripts/ai/gemini/run-gemini.sh setup
nano scripts/ai/gemini/.env.gemini
bash scripts/ai/gemini/run-gemini.sh
bash scripts/ai/gemini/headless.sh
```

## Commands

```bash
bash scripts/ai/gemini/run-gemini.sh                # Interactive Gemini CLI
bash scripts/ai/gemini/run-gemini.sh "prompt"      # Headless prompt mode
bash scripts/ai/gemini/run-gemini.sh prompt "..."  # Explicit headless prompt
bash scripts/ai/gemini/run-gemini.sh exec "..."    # Headless YOLO approvals
bash scripts/ai/gemini/run-gemini.sh check         # Check setup
bash scripts/ai/gemini/run-gemini.sh setup         # Install managed CLI
bash scripts/ai/gemini/run-gemini.sh mcp-check     # Check MCP configuration
bash scripts/ai/gemini/run-gemini.sh mcp-setup     # Sync MCP configuration
bash scripts/ai/gemini/run-gemini.sh update        # Reinstall pinned CLI toolchain
bash scripts/ai/gemini/headless.sh exec "..."      # Launch without MCP sync
```

```powershell
.\scripts\ai\gemini\run-gemini.ps1                 # Interactive Gemini CLI via WSL
.\scripts\ai\gemini\run-gemini.ps1 "prompt"        # Headless prompt mode via WSL
.\scripts\ai\gemini\run-gemini.ps1 exec "..."      # Headless YOLO approvals via WSL
.\scripts\ai\gemini\run-gemini.ps1 check           # Check setup via WSL
.\scripts\ai\gemini\run-gemini.ps1 setup           # Install managed CLI via WSL
.\scripts\ai\gemini\run-gemini.ps1 mcp-check       # Check MCP configuration
.\scripts\ai\gemini\run-gemini.ps1 mcp-setup       # Sync MCP configuration
.\scripts\ai\gemini\run-gemini.ps1 update          # Reinstall pinned CLI toolchain
.\scripts\ai\gemini\launch-gemini-wsl.ps1 start    # Thin alias for interactive mode
```

`exec` maps to Gemini CLI headless mode with `--approval-mode yolo`. Use it only for tasks where auto-approved file/tool actions are acceptable.

`gemini-interactive.sh` remains as a thin compatibility wrapper over
`run-gemini.sh`; it no longer owns setup or environment validation logic.

## Runtime Model

The managed runtime lives under:

```text
.cache/tools/gemini-cli/
├── npm-global/   # lockfile-backed node_modules plus managed bin links
├── npm-cache/
└── home/         # GEMINI_CLI_HOME
```

`helper/ensure-gemini-cli.sh` copies the tracked `npm-tooling/package.json` and
`package-lock.json` into the managed prefix and runs `npm ci --ignore-scripts`.
The lockfile currently pins `@google/gemini-cli@0.57.0` plus the Linux x64/arm64
Node 22.18.0 binary packages, including npm registry integrity hashes. `update`
deliberately reinstalls that reviewed dependency graph; version changes arrive
through the dedicated Dependabot configuration and review. The cache identity
combines the lockfile SHA with the selected Linux architecture, so a cache
created for x64 is never accepted on arm64 (or vice versa).

## Configuration

Create or edit `scripts/ai/gemini/.env.gemini`:

Launcher and setup scripts do not create `.env.gemini` by default. Create it
manually, or set `BIOETL_CREATE_LOCAL_ENV_FILES=1` when you explicitly want a
local template generated. Agents must not create, edit, rename, move, overwrite,
or delete `.env*` files without explicit per-task approval.

```bash
GEMINI_API_KEY=your-api-key-here
# GEMINI_MODEL=gemini-2.5-flash
```

Get an API key from https://aistudio.google.com/app/apikeys.

### Proxy from PowerShell to WSL

The PowerShell launchers forward non-empty `HTTP_PROXY`, `HTTPS_PROXY`,
`ALL_PROXY`, and `NO_PROXY` variables to the WSL Gemini process for that
single launch. Their values are passed through `WSLENV`, are not written to
`.env.gemini` or tracked configuration, and are not printed by the launcher.
An explicitly supplied proxy takes precedence over the repository's optional
WSL fallback proxy script.

```powershell
$env:HTTP_PROXY = "http://<user>:<password>@<host>:<port>"
$env:HTTPS_PROXY = $env:HTTP_PROXY
$env:ALL_PROXY = $env:HTTP_PROXY
.\scripts\ai\gemini\run-gemini.ps1
```

Use `Remove-Item Env:HTTP_PROXY, Env:HTTPS_PROXY, Env:ALL_PROXY` after the
session when the proxy should no longer apply.

## MCP Configuration

Gemini CLI reads MCP servers from Gemini settings, not from the repository `.mcp.json` file directly. The launcher synchronizes the workspace-level `.gemini/settings.json` before startup so the CLI sees the repository MCP servers after `cd "${REPO_ROOT}"`.

`run-gemini.sh` writes only the workspace settings file and does not mutate the managed user home at `.cache/tools/gemini-cli/home/.gemini/settings.json`, because that file can contain OAuth state and user UI preferences. The workspace `.gemini/settings.json` file is local-only/untracked on `main` and may contain machine-local absolute WSL paths.

Environment switches:

- `GEMINI_SKIP_MCP_SETUP=1` launches without synchronizing MCP.
- `GEMINI_RESPECT_MCP_DISABLES=1` keeps existing Gemini `/mcp disable` choices; by default, core servers such as `filesystem` are re-enabled for coding-agent use.
- `GEMINI_VALIDATE_MCP_LIST=1` additionally runs `gemini mcp list`.
- `GEMINI_REQUIRE_MCP_LIST=1` makes that runtime validation fatal.
- `GEMINI_MCP_CHECK_TIMEOUT=15` controls the validation timeout in seconds.

Docker-backed MCP servers require Docker Desktop or a working Docker CLI. If Docker is not running, those servers will show as disconnected until Docker is started.

## Notes

- `.env.gemini` is local and git-ignored. Do not copy real keys into docs, logs, reports, or PRs.
- `scripts/engineering/dev/bash/.wsl_proxy_env.sh` is sourced automatically as a fallback when no explicit proxy variables are present.
- PowerShell does not duplicate setup logic; it resolves the repository WSL path, forwards explicit proxy variables through `WSLENV`, and delegates to `run-gemini.sh`. PowerShell launchers use `BIOETL_WSL_DISTRO` when it is set and otherwise use the default WSL distro.
- `setup.ps1` and `setup-gemini-wsl.bat` are Windows setup transports. They delegate to `run-gemini.sh setup` inside WSL and then run `mcp-check`.
- `headless.sh` / `headless.ps1` set `GEMINI_SKIP_MCP_SETUP=1` for one launch and then delegate back to the canonical launcher.
