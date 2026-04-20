# Pre-Pulled Image Setup Guide

If you have a machine with stable internet and want to avoid slow downloads on your current machine:

## Option A: Save Image from Working Machine (If you have Ollama elsewhere)

```bash
# On source machine (with Ollama already running):
cd scripts/ai/mistrall/helper
./save-image.sh
# Creates: ollama-image.tar.gz (~2GB compressed)
```

Transfer `ollama-image.tar.gz` to your target machine:

```bash
# On target machine:
cp /path/to/ollama-image.tar.gz scripts/ai/mistrall/
cd scripts/ai/mistrall/helper
./load-image.sh
```

## Option B: Download Using Docker Mirror (Faster)

If Docker Hub is slow, try Aliyun mirror (Asia) or Tsinghua mirror (China):

```bash
# Windows PowerShell - Configure Docker daemon.json
$daemonJson = @{
    "registry-mirrors" = @(
        "https://mirror.aliyuncs.com",
        "https://hub-mirror.c.163.com"
    )
} | ConvertTo-Json

# Edit Docker Desktop Settings > Docker Engine, paste above mirrors

# Then retry:
docker pull ollama/ollama:latest
```

## Option C: Use Lightweight Alternative Image

Instead of full `ollama/ollama:latest` (~3.5GB):

**Edit `.env.mistrall`:**
```bash
MISTRALL_MODEL=phi:latest        # ~2.7GB (fastest)
# or
MISTRALL_MODEL=neural-chat:latest # ~4GB
# or
MISTRALL_MODEL=mistral:latest     # ~5GB (full)
```

The container image size is same, but model size varies.

## Option D: Docker Build Context (Advanced)

Create a custom Dockerfile that bakes in the image:

```dockerfile
FROM ollama/ollama:latest
RUN ollama pull mistral:latest
```

Build locally on fast connection, export, import on slow connection.

## Option E: Use Pre-Built Docker Image from Registry

Check if someone published pre-built image:

```bash
# Try alternative registries
docker pull ghcr.io/ollama/ollama:latest
docker pull quay.io/ollama/ollama:latest
```

## Status: Current Setup

Your current machine is attempting to pull but timing out due to slow connection.

**Quick fix:**

```powershell
# Stop current attempt
Ctrl+C  # in PowerShell running the pull

# Clean up
docker system prune -a -f --volumes

# Try with mirror or smaller model:
# Edit .env.mistrall, set MISTRALL_MODEL=phi:latest
# Then: .\run-mistrall.ps1 daemon
```

Which option works best for you?
