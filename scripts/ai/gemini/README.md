# Gemini - Coding Agent Launcher

Canonical launcher for Google Gemini CLI from `scripts/ai/gemini`.

This surface mirrors the operational shape of `scripts/ai/codex`: one entrypoint, managed repo-local npm install, explicit `check/setup/update`, WSL proxy support, and portable PowerShell delegation.

## Structure

```text
scripts/ai/gemini/
├── run-gemini.ps1                 # PowerShell entrypoint, delegates to WSL
├── run-gemini.sh                  # WSL/Bash entrypoint
├── headless.ps1                   # PowerShell transport that skips MCP sync
├── headless.sh                    # WSL/Bash launcher without MCP sync
├── .env.gemini                    # Local API key config, git-ignored
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
.\scripts\ai\gemini\run-gemini.ps1 check
.\scripts\ai\gemini\run-gemini.ps1 setup
notepad .\scripts\ai\gemini\.env.gemini
.\scripts\ai\gemini\run-gemini.ps1
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
bash scripts/ai/gemini/run-gemini.sh update        # Reinstall/update CLI
bash scripts/ai/gemini/headless.sh exec "..."      # Launch without MCP sync
```

`exec` maps to Gemini CLI headless mode with `--approval-mode yolo`. Use it only for tasks where auto-approved file/tool actions are acceptable.

`gemini-interactive.sh` remains as a thin compatibility wrapper over
`run-gemini.sh`; it no longer owns setup or environment validation logic.

## Runtime Model

The managed runtime lives under:

```text
.cache/tools/gemini-cli/
├── npm-global/   # node@22 + @google/gemini-cli
├── npm-cache/
└── home/         # GEMINI_CLI_HOME
```

`helper/ensure-gemini-cli.sh` installs `node@22` and `@google/gemini-cli@latest` into the repo-local prefix. The local Node 22 is required because current Gemini CLI uses JavaScript features unsupported by the system Node 18 in this WSL image.

## Configuration

Create or edit `scripts/ai/gemini/.env.gemini`:

```bash
GEMINI_API_KEY=your-api-key-here
# GEMINI_MODEL=gemini-2.5-flash
```

Get an API key from https://aistudio.google.com/app/apikeys.

## MCP Configuration

Gemini CLI reads MCP servers from Gemini settings, not from the repository `.mcp.json` file directly. The launcher synchronizes the workspace-level `.gemini/settings.json` before startup so the CLI sees the repository MCP servers after `cd "${REPO_ROOT}"`.

`run-gemini.sh` writes only the workspace settings file and does not mutate the managed user home at `.cache/tools/gemini-cli/home/.gemini/settings.json`, because that file can contain OAuth state and user UI preferences.

Environment switches:

- `GEMINI_INTERACTIVE_MCP_SERVERS=memory,filesystem` controls the fast-start MCP allowlist used by interactive mode.
- `GEMINI_INTERACTIVE_ALL_MCP=1` disables the fast-start allowlist and lets Gemini start every configured MCP server.
- `GEMINI_SKIP_MCP_SETUP=1` launches without synchronizing MCP.
- `GEMINI_RESPECT_MCP_DISABLES=1` keeps existing Gemini `/mcp disable` choices; by default, core servers such as `filesystem` are re-enabled for coding-agent use.
- `GEMINI_VALIDATE_MCP_LIST=1` additionally runs `gemini mcp list`.
- `GEMINI_REQUIRE_MCP_LIST=1` makes that runtime validation fatal.
- `GEMINI_MCP_CHECK_TIMEOUT=15` controls the validation timeout in seconds.

Docker-backed MCP servers require Docker Desktop or a working Docker CLI. If Docker is not running, those servers will show as disconnected until Docker is started.

## Notes

- `.env.gemini` is local and git-ignored. Do not copy real keys into docs, logs, reports, or PRs.
- `.wsl_proxy_env.sh` is sourced automatically when present before network/API operations.
- PowerShell does not duplicate setup logic; it resolves the repository WSL path and delegates to `run-gemini.sh`. PowerShell launchers use `BIOETL_WSL_DISTRO` when it is set and otherwise use the default WSL distro.
- `headless.sh` / `headless.ps1` set `GEMINI_SKIP_MCP_SETUP=1` for one launch and then delegate back to the canonical launcher.
