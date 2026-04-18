# Mistral - AI Model Server (via Ollama)

Analogous scripts to `script-codex` for running Mistral models via Ollama in Docker.

## Quick Start

### Linux/WSL
```bash
chmod +x script-mistrall/*.sh script-mistrall/helper/*.sh
./run-mistrall.sh daemon  # Start in background
./run-mistrall.sh pull    # Pull Mistral model
./run-mistrall.sh status  # Check if running
./run-mistrall.sh logs    # View logs
```

### Windows (PowerShell)
```powershell
.\run-mistrall.ps1 daemon
.\run-mistrall.ps1 pull
.\run-mistrall.ps1 status
.\run-mistrall.ps1 logs
```

## Commands

| Command | Description |
|---------|-------------|
| `start` | Start Mistral in foreground (interactive) |
| `daemon` | Start Mistral as background service |
| `stop` | Stop running Mistral service |
| `status` | Check if Mistral is running |
| `logs` | View Mistral service logs |
| `shell` | Access Mistral container shell |
| `pull` | Pull latest Mistral model |
| `check` | Check environment setup |
| `setup` | Setup missing components (Docker, Ollama) |
| `help` | Show help |

## Environment Variables

Edit `.env.mistrall` to customize:

- `MISTRALL_PORT` - Ollama API port (default: 11434)
- `MISTRALL_MODEL` - Model to pull (default: mistral:latest)
- `MISTRALL_MEMORY` - Memory allocation (default: 2g)
- `DOCKER_BUILDKIT` - Enable Docker BuildKit (default: 1)

## Structure

```
script-mistrall/
├── run-mistrall.sh              # Main entry point (Linux/WSL)
├── run-mistrall.ps1             # Main entry point (Windows)
├── .env.mistrall                # Configuration
├── docker-compose.mistrall.yml  # Docker Compose definition
└── helper/
    ├── check-env.sh             # Environment check (bash)
    ├── check-env.ps1            # Environment check (PowerShell)
    ├── setup-env.sh             # Setup and configure
    ├── run-mistrall-impl.sh      # Implementation (bash)
    └── run-mistrall-impl.ps1     # Implementation (PowerShell)
```

## API Access

Once running, access Mistral via:

```bash
# Get available models
curl http://localhost:11434/api/tags

# Generate completion
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model": "mistral:latest", "prompt": "Why is the sky blue?"}'
```

## Requirements

- Docker (Docker Desktop on Windows/macOS, Docker Engine on Linux)
- Docker Compose (usually included)
- WSL (for Windows bash scripts)
- ~4GB free disk space for model

## Troubleshooting

### Port already in use
Change `MISTRALL_PORT` in `.env.mistrall`:
```bash
MISTRALL_PORT=11435
```

### Model not pulling
Models require internet. For offline use, pre-pull the model on a connected machine.

### Out of memory
Adjust `MISTRALL_MEMORY` in `.env.mistrall` and Docker resource limits.

### Docker not found
Ensure Docker is installed and running. On Windows, start Docker Desktop first.
