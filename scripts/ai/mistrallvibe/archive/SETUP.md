# Mistral Vibe Setup

Установка Mistral Vibe на разных платформах.

## ⚡ 30-Second Setup

### Windows (PowerShell)

```powershell
cd script-mistrallvibe
notepad .env.mistrallvibe          # Add VIBE_API_KEY
.\vibe.ps1                         # Done!
```

### Linux/WSL (Bash)

```bash
cd script-mistrallvibe
nano .env.mistrallvibe             # Add VIBE_API_KEY
./vibe                             # Done!
```

## 📝 Step-by-Step

### 1️⃣ Get API Key

Go to: https://console.mistral.ai/api-keys/

Click **Create API key** and copy it.

### 2️⃣ Add to Configuration

#### Windows
```powershell
cd script-mistrallvibe
notepad .env.mistrallvibe
```

#### Linux/WSL
```bash
cd script-mistrallvibe
nano .env.mistrallvibe
```

**Add this line:**
```
VIBE_API_KEY=your-key-here
```

Replace `your-key-here` with your actual API key.

### 3️⃣ Run Vibe

#### Windows
```powershell
.\vibe.ps1
```

#### Linux/WSL
```bash
./vibe
```

✅ **That's it!** Interactive mode starts automatically.

## 🎯 First Commands

### Ask a question
```
You: explain how Docker containers work
```

### Code analysis
```
You: analyze this function for performance
```

### Exit
```
You: exit
```

Or press `Ctrl+C`.

## 🚀 Advanced Usage

### Different models

```bash
# Small model (fast)
./run-mistrallvibe.sh chat small

# Medium model
./run-mistrallvibe.sh chat medium

# Large model (best quality)
./run-mistrallvibe.sh chat large
```

### Web interface

```bash
./run-mistrallvibe.sh start
# Then open: http://localhost:5173
```

### Background service

```bash
./run-mistrallvibe.sh daemon
./run-mistrallvibe.sh status    # Check status
./run-mistrallvibe.sh logs      # View logs
./run-mistrallvibe.sh stop      # Stop later
```

## ❓ FAQ

### "API key not set"

Edit `.env.mistrallvibe` and add your key:

```bash
VIBE_API_KEY=sk-...
```

### "vibe not found"

Install it:

```bash
# Automatic (runs setup)
./run-mistrallvibe.sh setup

# Manual
python3 -m pip install --user mistral-vibe
```

### "WSL not found" (Windows)

For PowerShell CLI wrapper, need WSL2:

```powershell
wsl --install
```

Or use the full manager instead:
```powershell
.\run-mistrallvibe.ps1 chat
```

### "Permission denied" (Linux)

Make scripts executable:

```bash
chmod +x vibe run-mistrallvibe.sh
```

## 📞 Support

- Check setup: `./run-mistrallvibe.sh check`
- View docs: `README.md`
- View architecture: `ARCHITECTURE.md`
- Run in debug mode: `./run-mistrallvibe.sh setup` then `./vibe`

## 🎓 Examples

### Code Review
```bash
./vibe "review this function for bugs"
```

### Architecture Help
```bash
./vibe "suggest Docker architecture for microservices"
```

### Learning
```bash
./vibe "explain GraphQL in simple terms"
```

### Refactoring
```bash
./vibe "refactor this code for better readability"
```

## ✅ Verified Working

- ✅ Windows 11 + WSL2
- ✅ Ubuntu 22.04
- ✅ macOS (with pipx)
- ✅ Python 3.7 - 3.12
- ✅ Mistral Vibe 2.7.6+

Ready to go! 🚀
