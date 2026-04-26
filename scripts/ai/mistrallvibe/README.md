# Mistral Vibe - Compatibility Wrapper

Compatibility surface for the canonical `scripts/ai/vibe` launcher.

## ⚡ Quick Start

### Windows (PowerShell)

```powershell
cd scripts/ai/mistrallvibe
notepad .env.mistrallvibe    # Add MISTRAL_API_KEY
.\run-vibe.ps1
```

### Linux/WSL (Bash)

```bash
cd scripts/ai/mistrallvibe
nano .env.mistrallvibe       # Add MISTRAL_API_KEY
./run-vibe.sh
```

## 📋 Commands

```bash
./run-vibe.sh check                # Verify setup
./run-vibe.sh setup                # Install/configure Vibe
./run-vibe.sh                      # Interactive mode
./run-vibe.sh "explain this code"  # Send prompt
./run-vibe.sh --help               # Help
```

## 🔐 Configuration

Edit `.env.mistrallvibe`:

```bash
MISTRAL_API_KEY=your-api-key-here
```

Get API key from: https://console.mistral.ai/api-keys/

## 📚 Documentation

See the canonical Vibe surface for current behavior and launch options:

- `scripts/ai/vibe/README.md` - primary launcher documentation
- `scripts/ai/vibe/launch.sh` - canonical WSL/Linux entrypoint
- `scripts/ai/vibe/launch.ps1` - canonical Windows PowerShell entrypoint

## 🏗️ Structure

`scripts/ai/mistrallvibe/` keeps historical entrypoints, but the actual launch
path is delegated to `scripts/ai/vibe/launch.sh` and `scripts/ai/vibe/launch.ps1`.

## 🚀 Features

✅ Direct Vibe CLI access
✅ Repository context (`--workdir`)
✅ Cross-platform (Windows via WSL, Linux, macOS)
✅ Fast startup
✅ No dependencies beyond Mistral Vibe itself

## 📖 Notes

This directory is a compatibility wrapper. Advanced and future launcher behavior
should be added to `scripts/ai/vibe`, not to a separate `mistrallvibe`
execution path.

## ✨ Ready!

```powershell
.\run-vibe.ps1
```
