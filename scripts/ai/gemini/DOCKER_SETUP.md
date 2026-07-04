# Gemini CLI - Docker Setup

Alternative to WSL-based launch. Use Docker to run Gemini CLI without WSL.

## Prerequisites

1. **Docker Desktop** installed and running
   - Download: https://www.docker.com/products/docker-desktop/
   - Start Docker Desktop after installation

2. **Gemini API Key**
   - Get from: https://aistudio.google.com/app/apikeys

## Quick Start

### 1. Configure API Key

Edit `scripts/ai/gemini/.env.gemini`:

```bash
GEMINI_API_KEY=your-actual-api-key-here
# Optional model override
# GEMINI_MODEL=gemini-2.5-flash
```

### 2. Build Docker Image

```powershell
.\scripts\ai\gemini\run-gemini-docker.ps1 build
```

First run will auto-build the image.

### 3. Run Gemini

**Interactive mode:**
```powershell
.\scripts\ai\gemini\run-gemini-docker.ps1
```

**Single prompt:**
```powershell
.\scripts\ai\gemini\run-gemini-docker.ps1 "analyze this codebase"
```

**Auto-execute mode (YOLO approvals):**
```powershell
.\scripts\ai\gemini\run-gemini-docker.ps1 exec "fix all formatting issues"
```

## Commands

```powershell
.\scripts\ai\gemini\run-gemini-docker.ps1 check      # Check Docker setup
.\scripts\ai\gemini\run-gemini-docker.ps1 build      # Rebuild Docker image
.\scripts\ai\gemini\run-gemini-docker.ps1 start      # Interactive mode
.\scripts\ai\gemini\run-gemini-docker.ps1 exec       # Auto-execute mode
.\scripts\ai\gemini\run-gemini-docker.ps1 shell      # Shell in container
.\scripts\ai\gemini\run-gemini-docker.ps1 clean      # Remove containers and image
```

## Architecture

- **Dockerfile.gemini**: Node.js 22 + Gemini CLI
- **docker-compose.gemini.yml**: Container orchestration
- **Volume mounts**: Project root + persistent Gemini home
- **Non-root user**: Security best practice

## Troubleshooting

### "Docker not found"
Install Docker Desktop from https://www.docker.com/products/docker-desktop/

### "Docker is not running"
Start Docker Desktop application

### "GEMINI_API_KEY not set"
Edit `scripts/ai/gemini/.env.gemini` and add your API key

### Build fails
Check Docker Desktop has enough resources (RAM, disk)

### Container cannot access files
Ensure Docker Desktop has access to your drive:
- Docker Desktop Settings → Resources → File Sharing → Add drive

## Comparison with WSL Mode

| Feature | Docker Mode | WSL Mode |
|---------|-------------|----------|
| Prerequisites | Docker Desktop | WSL + Node.js |
| Setup complexity | Low | Medium |
| Performance | Good (container overhead) | Better (native) |
| MCP integration | Limited (no host MCP) | Full (native MCP) |
| Recommended for | Quick testing | Daily development |

## Notes

- Docker mode runs Gemini CLI in isolated container
- Project files are mounted as volume
- Gemini CLI home directory persists in Docker volume
- MCP servers (filesystem, git, docker) work inside container only
- For full MCP integration with host services, use WSL mode
