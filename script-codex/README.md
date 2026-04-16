# Codex - Consolidated Setup

Единая точка входа для запуска Codex на безголовой машине.

## 📁 Структура

```
script-codex/
├── run-codex.ps1              ⭐ Main entry point (PowerShell) - Non-blocking!
├── run-codex.sh               ⭐ Main entry point (WSL/Bash)
├── .env.codex                 # API key configuration
├── SETUP_HANG_FIX.md          # 📋 Read if setup hangs
├── helper/
│   ├── check-env.ps1          # Check environment (PowerShell)
│   ├── check-env.sh           # Check environment (Bash)
│   ├── setup-env.sh           # Setup (skips hanging apt, uses Node.js binaries)
│   ├── diagnose-hang.ps1      # 🔧 Debug setup hangs
│   └── run-codex-impl.sh      # Codex launcher implementation
├── README.md                  # This file
├── QUICK_START.md             # Quick start guide
└── docs/                      # Documentation
```

## 🚀 Quick Start

### From PowerShell (Windows) - NON-BLOCKING

```powershell
cd script-codex

# Just run - setup happens in background if needed!
.\run-codex.ps1
.\run-codex.ps1 "analyze the code"

# Or explicit commands
.\run-codex.ps1 check
.\run-codex.ps1 setup
```

⚡ **NEW**: Setup no longer blocks! If components are missing, they install in the background while you use Codex.

### From WSL (Ubuntu)

```bash
cd script-codex

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
.\run-codex.ps1 login             # Login with API key
.\run-codex.ps1 device-login      # Device auth login
```

```bash
# WSL/Bash
bash run-codex.sh help            # Show help
bash run-codex.sh                 # Interactive mode
bash run-codex.sh "prompt"        # With prompt
bash run-codex.sh exec "prompt"   # Auto-exec mode
bash run-codex.sh check           # Check setup
bash run-codex.sh setup           # Install missing components
bash run-codex.sh login           # Login with API key
bash run-codex.sh device-login    # Device auth login
```

## 🔧 What run-codex does

1. **Quick check** (~2 sec) - Validates WSL, Node.js, npm, Codex CLI
2. **Background setup** (if needed) - Auto-installs missing components in background
3. **Immediate launch** - Runs Codex right away (doesn't wait for setup)
4. **Setup completion** - Missing components finish installing in background

✅ **Key improvement**: No blocking on setup! You can start using Codex immediately.

## ⚙️ Setup

### 1. Edit .env.codex

```powershell
notepad .env.codex
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
- Check all dependencies
- Install missing components in background (if any)
- Launch Codex immediately

## 🐧 Requirements

- Windows 11 + WSL2
- Ubuntu in WSL
- Internet connection
- OpenAI API key

Node.js and npm are auto-installed if missing.

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
- [5/5] npm install

**Fixed in new version**: setup-env.sh now skips apt-get if it hangs and downloads Node.js binaries directly.

## 🆘 Troubleshooting

### "API key not found"

```powershell
notepad .env.codex
```

Make sure you have `OPENAI_API_KEY=sk-...` with valid key.

### "Node.js not found"

Run setup (now non-blocking!):
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
  - **NEW**: Skips apt-get if it hangs
  - **NEW**: Downloads Node.js binaries directly
  - **NEW**: 3 retry attempts for npm install
- `diagnose-hang.ps1` - **NEW**: Debug tool for setup hangs
- `run-codex-impl.sh` - Launch Codex with environment

## 🔐 API Key

Get from: https://platform.openai.com/api-keys

1. Create account on OpenAI
2. Go to API keys section
3. Create new secret key
4. Copy (starts with `sk-`)
5. Paste into `.env.codex`

## ✅ Ready!

Just run:

```powershell
.\run-codex.ps1
```

✨ **What happens**:
- Checks components (2 sec)
- If setup needed → starts in background (non-blocking)
- Launches Codex immediately
- Setup finishes quietly in the background

🚀 **No more waiting for setup!**
