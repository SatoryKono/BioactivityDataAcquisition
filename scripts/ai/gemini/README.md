# Gemini - Coding Agent Launcher

Canonical launcher for Google Gemini CLI from `scripts/ai/gemini`.

This surface mirrors the operational shape of `scripts/ai/codex`: one entrypoint, managed repo-local npm install, explicit `check/setup/update`, WSL proxy support, and portable PowerShell delegation.

## Structure

```text
scripts/ai/gemini/
├── run-gemini.ps1                 # PowerShell entrypoint, delegates to WSL
├── run-gemini.sh                  # WSL/Bash entrypoint
├── .env.gemini                    # Local API key config, git-ignored
├── helper/
│   ├── check-env.ps1              # PowerShell compatibility check wrapper
│   ├── check-env.sh               # Environment check
│   ├── ensure-gemini-cli.sh       # Managed Gemini CLI bootstrap
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
```

## Commands

```bash
bash scripts/ai/gemini/run-gemini.sh                # Interactive Gemini CLI
bash scripts/ai/gemini/run-gemini.sh "prompt"      # Headless prompt mode
bash scripts/ai/gemini/run-gemini.sh prompt "..."  # Explicit headless prompt
bash scripts/ai/gemini/run-gemini.sh exec "..."    # Headless YOLO approvals
bash scripts/ai/gemini/run-gemini.sh check         # Check setup
bash scripts/ai/gemini/run-gemini.sh setup         # Install managed CLI
bash scripts/ai/gemini/run-gemini.sh update        # Reinstall/update CLI
```

`exec` maps to Gemini CLI headless mode with `--approval-mode yolo`. Use it only for tasks where auto-approved file/tool actions are acceptable.

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

## Notes

- `.env.gemini` is local and git-ignored. Do not copy real keys into docs, logs, reports, or PRs.
- `.wsl_proxy_env.sh` is sourced automatically when present before network/API operations.
- PowerShell does not duplicate setup logic; it resolves the repository WSL path and delegates to `run-gemini.sh`.
