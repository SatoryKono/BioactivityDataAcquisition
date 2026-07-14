# Codex - Consolidated Setup

Единая точка входа для запуска Codex через canonical WSL/Bash launcher.

Root-level launchers such as `codex.ps1`, `codex.bat`,
`setup-codex-wsl.*`, `.wsl_proxy_env.sh`, `run-codex.ps1`, and
`run-codex-wsl.ps1` are retired from the repository root. Use the maintained
launchers under `scripts/**`.

## Retired Root Shim Verification

Last verified: 2026-07-10 for root script hygiene issues #6152-#6158.
This supersedes the earlier root hygiene issue #5994 root-shim delegation
contract by retiring the root files instead of retaining thin wrappers.

The repository root keeps no tracked `.sh`, `.ps1`, `.py`, or `.bat`
compatibility entrypoints:

| Retired root shim | Canonical owner | Retention decision |
| --- | --- | --- |
| `codex.ps1` | `scripts/ai/codex/run-codex.ps1` | root file retired; use the scripts-owned PowerShell transport |
| `codex.bat` | `scripts/ops/codex.bat` | root file retired; use the scripts-owned CMD transport |
| `setup-codex-wsl.bat` | `scripts/ai/codex/setup-codex-wsl.bat` | root file retired; use the scripts-owned Windows setup transport |
| `setup-codex-wsl.ps1` | `scripts/ai/codex/setup.ps1` | root file retired; deletion-first decision retained |
| `setup-codex-wsl.sh` | `scripts/ai/codex/helper/setup-wsl-complete.sh` | root file retired; use the scripts-owned Bash setup helper |
| `.wsl_proxy_env.sh` | `scripts/engineering/dev/bash/.wsl_proxy_env.sh` | root file retired; shared proxy helper is scripts-owned |

Any future root-script restoration must update `.github/root-allowlist.txt`,
`configs/quality/root_hygiene_review_registry.yaml`, operator docs, and wrapper
surface tests in the same change, and requires a fresh owner decision.

## 📁 Структура

```
scripts/ai/codex/
├── run-codex.ps1              PowerShell transport to the canonical WSL launcher
├── run-codex.sh               ⭐ Canonical WSL/Bash entry point
├── headless.ps1               PowerShell transport for headless Codex launch
├── headless.sh                Headless Codex launch without MCP sync
├── diagnose_wsl.ps1           PowerShell transport for WSL diagnostics
├── diagnose_wsl.sh            WSL diagnostics entrypoint
├── diagnose_wsl.bat           Windows batch transport for WSL diagnostics
├── .env.codex                 # API key configuration
├── SETUP_HANG_FIX.md          # 📋 Read if setup hangs
├── helper/
│   ├── check-env.ps1          # Check environment (PowerShell)
│   ├── check-env.sh           # Check environment (Bash)
│   ├── setup-env.sh           # Setup (skips hanging apt, uses Node.js binaries)
│   ├── ensure-mcp.sh          # Sync workspace MCP files and ~/.codex/config.toml
│   ├── diagnose-hang.ps1      # 🔧 Debug setup hangs
│   └── run-codex-impl.sh      # Codex launcher implementation
├── README.md                  # This file
├── QUICK_START.md             # Quick start guide
└── docs/                      # Documentation
```

## 🚀 Quick Start

### From PowerShell (Windows)

```powershell
# Repo-local launchers
.\scripts\ops\codex.bat
.\scripts\ops\codex.bat "analyze the code"

# Or explicit commands
.\scripts\ops\codex.bat help
.\scripts\ops\codex-exec.bat "fix the failing test"
.\scripts\ops\install-codex-cmd.bat
```

`scripts\ops\codex.bat` delegates to the canonical WSL/Bash launcher, so the
WSL transport remains the single source of truth for environment checks, setup,
MCP sync, and Codex execution.

### From WSL (Ubuntu)

```bash
cd scripts/ai/codex

bash run-codex.sh check
bash run-codex.sh setup
bash run-codex.sh "analyze the code"
```

## 📋 Commands

```powershell
# PowerShell
.\run-codex.ps1 help              # Show help
.\run-codex.ps1                   # Interactive mode
.\run-codex.ps1 "prompt"          # With prompt
.\run-codex.ps1 exec "prompt"     # Auto-exec mode
.\run-codex.ps1 check             # Check setup
.\run-codex.ps1 setup             # Install missing components
.\run-codex.ps1 mcp-check         # Check MCP configuration
.\run-codex.ps1 mcp-setup         # Sync MCP configuration
.\run-codex.ps1 login             # Login with API key
.\run-codex.ps1 device-login      # Device auth login
.\headless.ps1 exec "prompt"      # Launch without MCP sync
.\diagnose_wsl.ps1                # Run WSL diagnostics
```

```bash
# WSL/Bash
bash run-codex.sh help            # Show help
bash run-codex.sh                 # Interactive mode
bash run-codex.sh "prompt"        # With prompt
bash run-codex.sh exec "prompt"   # Auto-exec mode
bash run-codex.sh check           # Check setup
bash run-codex.sh setup           # Install missing components
bash run-codex.sh mcp-check       # Check MCP configuration
bash run-codex.sh mcp-setup       # Sync MCP configuration
bash run-codex.sh login           # Login with API key
bash run-codex.sh device-login    # Device auth login
bash headless.sh exec "prompt"    # Launch without MCP sync
bash diagnose_wsl.sh              # Run WSL diagnostics
```

## 🔧 What run-codex does

1. **Check** - Validates the WSL/Bash environment and the managed Codex CLI path
1. **Setup** (if needed) - Installs missing components through the repo-local helper flow
1. **MCP sync before launch** - Regenerates `.mcp.json`, `.vscode/mcp.json`, `.cursor/mcp.json`, `.qodo/mcp.json`, `.codex/settings.json`, `.devin/config.json`, and the Codex-native `~/.codex/config.toml` MCP block
1. **Launch** - Runs Codex from the repo root with the managed Codex CLI

Codex does not read the workspace `.mcp.json` directly. The launcher keeps `~/.codex/config.toml` synchronized so Codex starts with the repository MCP servers configured.

## ⚙️ Setup

### 1. Edit .env.codex

Launcher and setup scripts do not create `.env.codex` by default. Create it
manually, or set `BIOETL_CREATE_LOCAL_ENV_FILES=1` when you explicitly want a
local template generated.

```powershell
# Option 1: Create manually
copy .env.codex.example .env.codex
notepad .env.codex

# Option 2: Generate with opt-in flag
$env:BIOETL_CREATE_LOCAL_ENV_FILES="1"
.\run-codex.ps1 setup
```

Add your OpenAI API key:

```
OPENAI_API_KEY=sk-your-key-here
```

Get API key from: https://platform.openai.com/api-keys

### 2. First Run

```powershell
.\run-codex.ps1
```

This will:

- Check all dependencies through the canonical WSL/Bash launcher
- Install missing components through the repo-local helper flow if needed
- Synchronize MCP configuration for Codex
- Launch Codex from the managed WSL/Bash entrypoint

## MCP configuration

`run-codex.sh` runs `helper/ensure-mcp.sh` before launching Codex. `run-codex.ps1`
delegates to that same flow, and the retained transport launchers
`scripts/ops/launchers/codex/codex.sh` and
`scripts/ops/launchers/codex/codex-exec.sh` now do the same. This writes:

- `.mcp.json` - workspace MCP config used by compatible tools
- `scripts/ai/.mcp.json` - tracked portable mirror of the root workspace MCP config
- `.vscode/mcp.json` - VS Code MCP config
- `.cursor/mcp.json` - Cursor MCP config mirror
- `.qodo/mcp.json` - Qodo Desktop MCP config mirror
- `.codex/settings.json` - local-only generated Codex workspace MCP settings mirror
- `.devin/config.json` - tracked portable Devin runtime projection; generation
  replaces `mcpServers` and preserves Devin-owned top-level settings
- `~/.codex/config.toml` - Codex-native MCP config used by `codex`

The tracked workspace manifests `.mcp.json`, `scripts/ai/.mcp.json`, and
`.devin/config.json` are repo-relative and portable. Local-only runtime outputs
such as `~/.codex/config.toml` and `.codex/settings.json` may contain
machine-local absolute paths for tools that require them.

Set `CODEX_SKIP_MCP_SETUP=1` only when you intentionally want to launch Codex without synchronizing MCP. Set `CODEX_VALIDATE_MCP_LIST=1` to additionally run `codex mcp list --json`; this validation is off by default because some local MCP/server environments can make the CLI list operation hang.

The canonical `headless.sh` / `headless.ps1` launchers set `CODEX_SKIP_MCP_SETUP=1`
for you. `diagnose_wsl.sh`, `diagnose_wsl.ps1`, and `diagnose_wsl.bat` are the
canonical diagnostics entrypoints.

## 🐧 Requirements

- Windows 11 + WSL2
- Ubuntu in WSL
- Internet connection
- OpenAI API key

Node.js and npm are installed through the shared WSL helper flow if missing.

## ⚠️ Setup Hangs / Freezes?

See **[SETUP_HANG_FIX.md](./SETUP_HANG_FIX.md)** for detailed diagnostics.

Quick diagnostics:

```powershell
.\helper\diagnose-hang.ps1
```

This will identify exactly where the hang occurs:

- [1/5] WSL connectivity
- [2/5] Bash execution
- [3/5] apt-get update ← Usually hangs here
- [4/5] Node.js check
- [5/5] helper/setup-env.sh bootstrap

**Fixed in new version**: setup-env.sh now skips apt-get if it hangs and downloads Node.js binaries directly.

## 🆘 Troubleshooting

### "API key not found"

```powershell
notepad .env.codex
```

Make sure you have `OPENAI_API_KEY=sk-...` with valid key.

### "Node.js not found"

Run setup:

```powershell
.\run-codex.ps1 setup
```

Or install manually in WSL:

```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo bash
sudo apt-get install -y nodejs
```

### "WSL not available"

Install WSL2:

```powershell
wsl --install
```

### Check what's wrong

```powershell
.\run-codex.ps1 check
```

## 📚 Helper Scripts

All logic is in `helper/` folder:

- `check-env.ps1` / `check-env.sh` - Verify setup
- `setup-env.sh` - Install components (Node.js, npm, Codex)
- `ensure-mcp.sh` - Sync MCP configs before launching Codex
  - **NEW**: Skips apt-get if it hangs
  - **NEW**: Downloads Node.js binaries directly
  - **NEW**: 3 retry attempts for npm install
- `diagnose-hang.ps1` - **NEW**: Debug tool for setup hangs
- `run-codex-impl.sh` - Launch Codex with environment

## 🔐 API Key

Get from: https://platform.openai.com/api-keys

1. Create account on OpenAI
1. Go to API keys section
1. Create new secret key
1. Copy (starts with `sk-`)
1. Paste into `.env.codex`

## ✅ Ready!

Just run:

```powershell
.\run-codex.ps1
```

✨ **What happens**:

- Checks components through the canonical WSL/Bash launcher
- Runs repo-local setup helpers if needed
- Synchronizes MCP configuration
- Launches Codex from the managed WSL/Bash entrypoint
