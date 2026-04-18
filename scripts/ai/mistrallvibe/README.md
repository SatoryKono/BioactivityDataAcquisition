# Mistral Vibe - CLI Wrapper

Direct Mistral Vibe access with repository context.

## ⚡ Quick Start

### Windows (PowerShell)
```powershell
cd script-mistrallvibe
notepad .env.mistrallvibe    # Add VIBE_API_KEY
.\run-vibe.ps1
```

### Linux/WSL (Bash)
```bash
cd script-mistrallvibe
nano .env.mistrallvibe       # Add VIBE_API_KEY
./run-vibe.sh
```

## 📋 Commands

```bash
./run-vibe.sh                      # Interactive mode
./run-vibe.sh "explain this code"  # Send prompt
./run-vibe.sh --help              # Help
```

## 🔐 Configuration

Edit `.env.mistrallvibe`:
```bash
VIBE_API_KEY=your-api-key-here
```

Get API key from: https://console.mistral.ai/api-keys/

## 📚 Documentation

See `archive/` for additional resources:
- `QUICK_START.md` - Full walkthrough
- `ARCHITECTURE.md` - Design overview
- `SETUP.md` - Setup guide

## 🏗️ Structure

```
script-mistrallvibe/
├── run-vibe.ps1          ⭐ Launcher (Windows)
├── run-vibe.sh           ⭐ Launcher (Linux)
├── README.md             # This file
├── .env.mistrallvibe     # Configuration
├── helper/               # Support scripts
└── archive/              # Additional tools
    ├── run-mistrallvibe.* # Full manager (server, chat, web UI)
    ├── vibe-*.* # Web server, CLI, UI files
    └── *.md # Documentation
```

## 🚀 Features

✅ Direct Vibe CLI access
✅ Repository context (`--workdir`)
✅ Cross-platform (Windows via WSL, Linux, macOS)
✅ Fast startup
✅ No dependencies beyond Mistral Vibe itself

## 📖 Full Features

For web server, chat mode, and more, see `archive/run-mistrallvibe.*`:
```powershell
.\archive\run-mistrallvibe.ps1 start    # Web server
.\archive\run-mistrallvibe.ps1 chat     # Chat mode
.\archive\run-mistrallvibe.ps1 help     # All commands
```

## ✨ Ready!

```powershell
.\run-vibe.ps1
```
