# Mistral Vibe - Consolidated Setup

Единая точка входа для запуска Mistral Vibe CLI на любой машине.

## 📁 Структура

```
script-mistrallvibe/
├── vibe.ps1                   ⭐ CLI wrapper (Windows → WSL)
├── vibe                       ⭐ CLI wrapper (Linux/WSL)
├── run-mistrallvibe.ps1       ⭐ Full manager (PowerShell)
├── run-mistrallvibe.sh        ⭐ Full manager (WSL/Bash)
├── .env.mistrallvibe          # API key configuration
├── vibe-cli.py                # Python chat CLI
├── vibe-server.js             # Node.js web server
├── vibe-ui.html               # Web UI (HTML/JS)
├── docker-compose.mistrallvibe.yml  # Docker compose
├── ARCHITECTURE.md            # Architecture overview
├── README.md                  # Full documentation
└── helper/
    ├── check-env.ps1          # Check environment (PowerShell)
    ├── check-env.sh           # Check environment (Bash)
    ├── setup-env.ps1          # Setup (PowerShell)
    ├── setup-env.sh           # Setup (Bash)
    ├── run-mistrallvibe-impl.ps1  # Implementation (PowerShell)
    └── run-mistrallvibe-impl.sh   # Implementation (Bash)
```

## 🚀 Quick Start

### CLI Mode (Direct Vibe)

#### From PowerShell (Windows)

```powershell
cd script-mistrallvibe

# Interactive mode (via WSL)
.\vibe.ps1

# With prompt
.\vibe.ps1 "explain this code"

# Show help
.\vibe.ps1 --help
```

#### From WSL (Ubuntu/Linux)

```bash
cd script-mistrallvibe

# Interactive mode
./vibe

# With prompt
./vibe "explain this code"

# Show help
./vibe --help
```

### Full Manager Mode (Server + Chat + Web UI)

#### From PowerShell

```powershell
cd script-mistrallvibe

# Setup first time
.\run-mistrallvibe.ps1 setup

# Interactive chat
.\run-mistrallvibe.ps1 chat large

# Start web server
.\run-mistrallvibe.ps1 start

# Check status
.\run-mistrallvibe.ps1 status
```

#### From WSL

```bash
cd script-mistrallvibe

# Setup first time
bash run-mistrallvibe.sh setup

# Interactive chat
bash run-mistrallvibe.sh chat large

# Start web server
bash run-mistrallvibe.sh start

# Check status
bash run-mistrallvibe.sh status
```

## 📋 Commands

### CLI Wrapper (vibe / vibe.ps1)

```
Usage: ./vibe [prompt]

Examples:
  ./vibe                          # Interactive
  ./vibe "analyze the code"       # Send prompt
  ./vibe --help                   # Help
```

**Platform note:**
- Windows: Use `vibe.ps1` (runs via WSL)
- Linux/WSL: Use `vibe` (native bash)

### Full Manager (run-mistrallvibe)

```powershell
.\run-mistrallvibe.ps1 help           # Show help
.\run-mistrallvibe.ps1                # Start web server
.\run-mistrallvibe.ps1 start          # Start in foreground
.\run-mistrallvibe.ps1 daemon         # Start as daemon
.\run-mistrallvibe.ps1 stop           # Stop service
.\run-mistrallvibe.ps1 status         # Check status
.\run-mistrallvibe.ps1 logs           # View logs
.\run-mistrallvibe.ps1 browser        # Open web UI
.\run-mistrallvibe.ps1 chat           # Interactive chat
.\run-mistrallvibe.ps1 chat large     # Chat with large model
.\run-mistrallvibe.ps1 api-key        # Show API key
.\run-mistrallvibe.ps1 check          # Check setup
.\run-mistrallvibe.ps1 setup          # Install Vibe
```

## 🔧 What vibe wrapper does

1. **Check installation** (~1 sec) - Validates Vibe CLI
2. **Auto setup** (if needed) - Installs via pipx/pip
3. **Immediate launch** - Runs Vibe with repo context
4. **Setup completion** - Missing components finish in background

✅ **Key feature**: Works from anywhere with repository context (`--workdir`).

## 🔧 What run-mistrallvibe does

1. **Environment check** - Validates Python, config files
2. **Auto setup** (if needed) - Installs Mistral Vibe via pipx/pip
3. **Multiple interfaces**:
   - **CLI chat** - Python interactive mode
   - **Web server** - Node.js web UI
   - **Web browser** - Open in browser
4. **Management** - Start, stop, logs, status

## ⚙️ Setup

### 1. Edit .env.mistrallvibe

```powershell
notepad .env.mistrallvibe
```

Add your Mistral API key:

```
VIBE_API_KEY=your-api-key-here
VIBE_PORT=5173
VIBE_HOST=localhost
```

Get API key from: https://console.mistral.ai/api-keys/

### 2. First Run (Auto Setup)

**Option A: CLI only**
```powershell
.\vibe.ps1
```

**Option B: Full environment**
```powershell
.\run-mistrallvibe.ps1 setup
```

This will:
- Check Python 3.7+
- Install Mistral Vibe (via pipx or pip --user)
- Setup configuration
- Add ~/.local/bin to PATH
- Launch immediately

## 🐧 Requirements

- Windows 11 + WSL2 (for CLI wrapper on Windows)
- Python 3.7+
- Node.js 16+ (for web server)
- Internet connection
- Mistral API key

## 🆘 Troubleshooting

### "vibe command not found"

Install Mistral Vibe:

```bash
# Via pipx (recommended)
pipx install mistral-vibe

# Via pip with --user
python3 -m pip install --user mistral-vibe

# Via official installer
curl -LsSf https://mistral.ai/vibe/install.sh | bash
```

Then ensure ~/.local/bin is in PATH:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

### "API key not found"

```powershell
notepad .env.mistrallvibe
```

Make sure you have `VIBE_API_KEY=...` with valid key from https://console.mistral.ai/api-keys/

### "WSL not available" (Windows)

For `vibe.ps1` to work, install WSL2:

```powershell
wsl --install
```

### Check what's wrong

```powershell
.\run-mistrallvibe.ps1 check
```

Or CLI:
```bash
./vibe --help
```

## 📚 Helper Scripts

All logic is in `helper/` folder:

- `check-env.ps1` / `check-env.sh` - Verify setup
- `setup-env.ps1` / `setup-env.sh` - Install components
  - Auto-detects pipx vs pip --user
  - Handles system-protected Python
  - Fixes PATH issues
- `run-mistrallvibe-impl.ps1` / `run-mistrallvibe-impl.sh` - Implementation

## 🔐 API Key

Get from: https://console.mistral.ai/api-keys/

1. Create account on Mistral
2. Go to API keys section
3. Create new API key
4. Copy key
5. Paste into `.env.mistrallvibe`

## ✨ Modes

### 1. CLI Mode (Direct)

```bash
./vibe "explain this code"
```

✅ Fast, minimal setup, repository context

### 2. Chat Mode (Interactive)

```bash
./run-mistrallvibe.sh chat large
```

✅ Multi-turn conversation, model selection

### 3. Web Server Mode

```bash
./run-mistrallvibe.sh start
```

✅ Browser interface, persistent sessions, Web UI at http://localhost:5173

## 📊 Use Cases

| Use Case | Command |
|----------|---------|
| Quick code review | `./vibe "review this"` |
| Interactive session | `./run-mistrallvibe.sh chat large` |
| Web interface | `./run-mistrallvibe.sh start` |
| Background service | `./run-mistrallvibe.sh daemon` |

## 🔗 Related

- `script-codex/` - OpenAI Codex wrapper
- `script-gemini/` - Google Gemini wrapper
- `script-mistrall/` - Local Ollama + Mistral

## 📖 Documentation

- `README.md` - Full feature documentation
- `ARCHITECTURE.md` - Design overview
- `QUICK_START.md` - Step-by-step guide

## ✅ Ready!

Just run:

```powershell
.\vibe.ps1
```

Or setup for all features:

```powershell
.\run-mistrallvibe.ps1 setup
```

🚀 **Mistral Vibe is ready to use!**
