# Mistral Vibe CLI Wrapper Scripts

Canonical and compatibility wrappers for launching Mistral Vibe with automatic
PATH setup and repository context.

## Files

- `scripts/ai/vibe/launch.sh` — Canonical Bash launcher (Linux/WSL)
- `scripts/ai/vibe/launch.ps1` — Canonical PowerShell launcher (Windows via WSL)
- `scripts/vibe` — Compatibility Bash wrapper
- `scripts/vibe.ps1` — Compatibility PowerShell wrapper

## Usage

### Linux/WSL
```bash
cd /path/to/repo
bash scripts/ai/vibe/launch.sh
bash scripts/ai/vibe/launch.sh "explain this code"
python -m scripts.ai vibe --help
```

### Windows (PowerShell)
```powershell
cd C:\path\to\repo
.\scripts\ai\vibe\launch.ps1
.\scripts\ai\vibe\launch.ps1 "explain this code"
.\scripts\vibe.ps1 --help
```

## Features

- Automatic PATH setup (includes `~/.local/bin`)
- Environment setup for uv-installed tools
- Automatic repository root detection
- Vibe installation check
- Error handling with helpful messages
- Works with `vibe --workdir` for proper context

## Installation

### Install Mistral Vibe

Choose one method:

```bash
# Official installer
curl -LsSf https://mistral.ai/vibe/install.sh | bash

# Or via pip (--user for system-protected Python)
python3 -m pip install --user mistral-vibe

# Or via pipx (recommended)
pipx install mistral-vibe
```

### Make scripts executable

```bash
chmod +x scripts/ai/vibe/launch.sh
```

## Examples

### Interactive Chat
```bash
bash scripts/ai/vibe/launch.sh
```

### Send a prompt
```bash
bash scripts/ai/vibe/launch.sh "refactor this function for better performance"
```

### Code analysis
```bash
bash scripts/ai/vibe/launch.sh "analyze security issues in this code"
```

### Show help
```bash
python -m scripts.ai vibe --help
```

## Comparison with script-mistrallvibe

| Feature | `scripts/ai/vibe` | `script-mistrallvibe` |
|---------|---|---|
| **Scope** | Canonical Vibe launch tooling | Full Mistral Vibe management (server, CLI, web UI) |
| **Purpose** | Direct access to vibe command | Complete Mistral environment |
| **Commands** | `vibe` (passthrough) | `start`, `chat`, `server`, `status`, etc. |
| **Use case** | Quick code assistance | Production setup, multiple interfaces |
| **Setup** | Simple wrapper | Full initialization |

## Troubleshooting

### "vibe command not found"

Make sure Mistral Vibe is installed:

```bash
# Check installation
which vibe
vibe --version

# If not found, install
curl -LsSf https://mistral.ai/vibe/install.sh | bash

# Restart terminal or run
export PATH="${HOME}/.local/bin:${PATH}"
```

### PATH issues

The script automatically adds `~/.local/bin` to PATH. If still having issues:

```bash
# Manual fix
export PATH="${HOME}/.local/bin:${PATH}"

# Make permanent (add to ~/.bashrc or ~/.zshrc)
echo 'export PATH="${HOME}/.local/bin:${PATH}"' >> ~/.bashrc
source ~/.bashrc
```

### uv environment

If using uv-installed tools, the script sources `~/.local/bin/env` automatically.

## Related

- `scripts/ai/vibe/` — Canonical Vibe launch tooling
- `script-mistrallvibe/` — Full Mistral Vibe environment setup
- `script-codex/` — Similar wrapper for Codex
- `script-gemini/` — Similar wrapper for Gemini
