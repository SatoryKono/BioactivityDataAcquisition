# Mistral Vibe - Compatibility Wrapper

Compatibility surface for the canonical `scripts/ai/vibe` launcher.

## ⚡ Quick Start

Preferred public entrypoint:

```bash
python -m scripts.ai vibe --help
python -m scripts.ai vibe check
python -m scripts.ai vibe setup
python -m scripts.ai vibe
python -m scripts.ai vibe "explain this code"
```

This directory is retained for setup helpers and historical context; prefer the
canonical `scripts.ai.vibe` surface for actual launch commands.

Edit the compatibility env file, then launch through the canonical surface:

```bash
nano scripts/ai/mistrallvibe/.env.mistrallvibe
python -m scripts.ai vibe
```

## 📋 Commands

```bash
python -m scripts.ai vibe --help  # Preferred public entrypoint
python -m scripts.ai vibe check   # Preferred setup verification
python -m scripts.ai vibe setup   # Preferred installer/bootstrap
python -m scripts.ai vibe         # Preferred interactive mode
python -m scripts.ai vibe "explain this code"
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
- `scripts/ai/mistrallvibe/helper/setup-env.sh` - retained compatibility setup helper
- `scripts/ai/mistrallvibe/helper/setup-env.ps1` - retained compatibility setup helper

## 🏗️ Structure

`scripts/ai/mistrallvibe/` keeps historical setup helpers and compatibility
context, but the actual launch path is now `scripts/ai/vibe/launch.sh` and
`scripts/ai/vibe/launch.ps1`.

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
python -m scripts.ai vibe
```
