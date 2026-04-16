# Codex Consolidated Structure

## ✅ Consolidation Complete!

Структура полностью реорганизована с единой точкой входа.

## 📁 New Structure

```
script-codex/
├── run-codex.ps1 ⭐              Main entry point (PowerShell)
├── run-codex.sh ⭐               Main entry point (Bash)
├── .env.codex                    API key configuration
├── helper/                       Helper scripts
│   ├── check-env.ps1            Environment check (PS)
│   ├── check-env.sh             Environment check (Bash)
│   ├── setup-env.sh             Setup missing components
│   └── run-codex-impl.sh        Codex implementation
├── README.md                     Full documentation
└── docs/
    ├── CODEX_AUTHENTICATION.md   Auth methods
    ├── POWERSHELL_QUICK_START.md Commands
    └── ...
```

## 🎯 Main Features

### 1. **Single Entry Point**
   - `run-codex.ps1` (Windows/PowerShell)
   - `run-codex.sh` (WSL/Bash)

### 2. **Automatic Environment Check**
   - Verifies WSL, Node.js, npm, Codex
   - Creates missing files
   - Shows clear status

### 3. **Automatic Setup**
   - Installs Node.js if missing
   - Installs npm if missing
   - Installs Codex CLI if missing
   - All done automatically!

### 4. **Helper Scripts Separated**
   - `helper/check-env.ps1` - Check (PowerShell)
   - `helper/check-env.sh` - Check (Bash)
   - `helper/setup-env.sh` - Setup components
   - `helper/run-codex-impl.sh` - Launch Codex

## 💻 Usage

### PowerShell

```powershell
cd script-codex
.\run-codex.ps1 check              # Check setup
.\run-codex.ps1 setup             # Setup if needed
.\run-codex.ps1                   # Run Codex
.\run-codex.ps1 "analyze code"    # With prompt
```

### WSL/Bash

```bash
cd script-codex
bash run-codex.sh check            # Check setup
bash run-codex.sh setup            # Setup if needed
bash run-codex.sh                  # Run Codex
bash run-codex.sh "analyze code"   # With prompt
```

## 🔄 How it Works

### On First Run:

1. **Check** - run-codex.ps1 calls helper/check-env.ps1
2. **Detect Missing** - If anything missing, runs setup
3. **Setup** - helper/setup-env.sh installs components
4. **Launch** - helper/run-codex-impl.sh starts Codex

### On Subsequent Runs:

1. **Quick Check** - Verifies everything is OK
2. **Direct Launch** - Skips setup, runs Codex

## 📋 Commands

| Command | Purpose |
|---------|---------|
| `run-codex.ps1` | Start interactive Codex |
| `run-codex.ps1 "prompt"` | With prompt |
| `run-codex.ps1 exec "prompt"` | Auto-execute |
| `run-codex.ps1 check` | Check setup |
| `run-codex.ps1 setup` | Install components |
| `run-codex.ps1 login` | API key login |
| `run-codex.ps1 device-login` | Device auth |
| `run-codex.ps1 help` | Show help |

## 🎓 Code Flow

```
User runs: .\run-codex.ps1
    ↓
run-codex.ps1 (main entry)
    ↓
Call helper/check-env.ps1
    ↓
Components OK? → YES → Launch Codex
         ↓
         NO
         ↓
Call helper/setup-env.sh (in WSL)
         ↓
Install components (Node.js, npm, Codex)
         ↓
Launch helper/run-codex-impl.sh
         ↓
Run Codex with environment
```

## 📦 Helper Scripts

### check-env.ps1 / check-env.sh
- Checks WSL availability
- Checks Node.js & npm
- Checks Codex CLI
- Checks API key
- Returns status

### setup-env.sh
- Installs Node.js
- Installs npm
- Installs Codex
- Creates .env.codex template
- Verifies API key

### run-codex-impl.sh
- Loads .env.codex
- Sets up environment
- Launches Codex
- No setup logic here

## ✨ Benefits

✅ Single entry point (run-codex.ps1 or run-codex.sh)  
✅ Automatic environment checks  
✅ Automatic component installation  
✅ Clear status messages  
✅ Modular helper scripts  
✅ Works on first run  
✅ No manual configuration needed  
✅ Portable (can copy entire folder)

## 🚀 Getting Started

1. Edit `.env.codex` with your API key
2. Run: `.\run-codex.ps1`
3. That's it! Codex will setup and launch

## 📝 Notes

- All setup logic is automatic
- No sudo password needed (setup-env.sh handles it)
- Works for headless machines
- Fully consolidated in one folder
- Can be copied to other machines

---

**Status**: ✅ Complete and ready to use!

Just run: `.\run-codex.ps1` 🚀
