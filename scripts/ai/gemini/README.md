# Gemini - Local Launcher

Canonical launcher for Google Gemini from `scripts/ai/gemini`.

This surface mirrors the operational shape of `scripts/ai/codex`: one entrypoint, managed repo-local runtime, explicit `check/setup/update`, WSL proxy support, and portable PowerShell delegation. It is still a Gemini SDK chat/prompt wrapper, not a Codex-style auto-editing coding agent.

## Structure

```text
scripts/ai/gemini/
├── run-gemini.ps1                 # PowerShell entrypoint, delegates to WSL
├── run-gemini.sh                  # WSL/Bash entrypoint
├── .env.gemini                    # Local API key config, git-ignored
├── helper/
│   ├── check-env.ps1              # PowerShell compatibility check wrapper
│   ├── check-env.sh               # Environment check
│   ├── ensure-gemini-cli.sh       # Managed repo-local runtime bootstrap
│   ├── gemini_client.py           # Stable Python SDK client
│   ├── setup-env.sh               # Setup managed runtime and env template
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
bash scripts/ai/gemini/run-gemini.sh              # Interactive mode
bash scripts/ai/gemini/run-gemini.sh "prompt"    # Single prompt
bash scripts/ai/gemini/run-gemini.sh prompt "..." # Explicit single prompt
bash scripts/ai/gemini/run-gemini.sh exec "..."   # Alias for prompt mode
bash scripts/ai/gemini/run-gemini.sh check        # Check setup
bash scripts/ai/gemini/run-gemini.sh setup        # Install managed runtime
bash scripts/ai/gemini/run-gemini.sh update       # Reinstall/update runtime
```

`exec` is intentionally only a single-prompt alias. It does not provide Codex `--full-auto` behavior and does not edit repository files by itself.

## Runtime Model

The managed runtime lives under:

```text
.cache/tools/gemini-sdk/venv
```

`helper/ensure-gemini-cli.sh` owns creation and updates. The launcher no longer depends on the old `$HOME/.cache/tools/gemini-venv` location.

## Configuration

Create or edit `scripts/ai/gemini/.env.gemini`:

```bash
GEMINI_API_KEY=your-api-key-here
GEMINI_MODEL=gemini-2.5-flash
```

Get an API key from https://aistudio.google.com/app/apikeys.

## Notes

- `.env.gemini` is local and git-ignored. Do not copy real keys into docs, logs, reports, or PRs.
- `.wsl_proxy_env.sh` is sourced automatically when present before network/API operations.
- PowerShell does not duplicate setup logic; it resolves the repository WSL path and delegates to `run-gemini.sh`.
