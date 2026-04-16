# Archive - Extended Features

Additional tools for Mistral Vibe: web server, chat mode, and full environment management.

## 📁 Contents

### Managers
- `run-mistrallvibe.ps1` - Full manager (Windows)
- `run-mistrallvibe.sh` - Full manager (Linux/WSL)

### CLI Wrappers (Alternative)
- `vibe.ps1` - Windows CLI wrapper
- `vibe` - Linux/WSL CLI wrapper

### Web Components
- `vibe-server.js` - Node.js web server
- `vibe-ui.html` - Web UI (HTML/JS)
- `vibe-cli.py` - Python chat interface
- `docker-compose.mistrallvibe.yml` - Docker setup

### Documentation
- `QUICK_START.md` - 5-minute guide
- `SETUP.md` - 30-second setup
- `ARCHITECTURE.md` - Design overview
- `ALIGNMENT.md` - Alignment check

## 🚀 Usage

### Full Manager (All Features)

```powershell
# Windows
.\run-mistrallvibe.ps1 setup         # Install
.\run-mistrallvibe.ps1 start         # Web server
.\run-mistrallvibe.ps1 chat large    # Chat mode
```

```bash
# Linux/WSL
bash run-mistrallvibe.sh setup       # Install
bash run-mistrallvibe.sh start       # Web server
bash run-mistrallvibe.sh chat large  # Chat mode
```

### Web Server

```bash
./run-mistrallvibe.sh start
# Open: http://localhost:5173
```

### Chat Mode

```bash
./run-mistrallvibe.sh chat            # Default (small)
./run-mistrallvibe.sh chat medium
./run-mistrallvibe.sh chat large
```

## 🔧 Commands

Full list from `run-mistrallvibe.sh`:
- `start` - Web server
- `daemon` - Background service
- `stop` - Stop service
- `status` - Check status
- `logs` - View logs
- `chat [model]` - Interactive chat
- `browser` - Open web UI
- `api-key` - Show API key
- `check` - Verify setup
- `setup` - Install Vibe
- `help` - Help

## 📋 When to Use

| Need | Tool |
|------|------|
| Quick code review | `../run-vibe.sh` |
| Interactive chat | `run-mistrallvibe.sh chat` |
| Web interface | `run-mistrallvibe.sh start` |
| Full environment | `run-mistrallvibe.sh` |

## 📚 Documentation

- **QUICK_START.md** - Full walkthrough (5 min)
- **SETUP.md** - Installation guide (30 sec)
- **ARCHITECTURE.md** - Technical overview

## ✨ Features

✅ Web server (Node.js)
✅ Chat mode (Python)
✅ Service management
✅ Background daemon
✅ Browser UI
✅ Status monitoring
✅ Docker support

## 🔐 Configuration

Use `.env.mistrallvibe` in parent directory for:
- `VIBE_API_KEY`
- `VIBE_PORT`
- `VIBE_HOST`

## 🚀 Ready!

Go back to parent directory for quick access:

```powershell
cd ..
.\run-vibe.ps1
```

Or use full manager:

```powershell
.\archive\run-mistrallvibe.ps1 start
```
