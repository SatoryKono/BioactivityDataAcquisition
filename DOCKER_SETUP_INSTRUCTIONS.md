# Docker Setup Instructions for BioETL

## Current Status
Docker Desktop is experiencing startup issues on this Windows host. Below are the steps to resolve this and configure Docker for BioETL.

## Option 1: Fix Docker Desktop (Recommended)

### Step 1: Restart Docker Desktop
```powershell
# Stop Docker Desktop
Stop-Process -Name "Docker Desktop" -Force -ErrorAction SilentlyContinue

# Start Docker Desktop
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# Wait for Docker to be ready (may take 2-3 minutes)
Start-Sleep -Seconds 120

# Verify Docker is running
docker info
```

### Step 2: Harden Docker Desktop Settings
```powershell
# Run the BioETL hardening script
powershell -ExecutionPolicy Bypass -File "scripts/ops/runtime/docker/ensure-stable.ps1" -WithNeo4j
```

This script will:
- Harden WSL config (6GB memory limit)
- Configure Docker Desktop settings (Resource Saver off, AutoStart on)
- Start Docker Desktop
- Verify Docker is ready

### Step 3: Start BioETL Stack
```bash
# Start main stack
python scripts/ops/runtime/docker/runtime_manager.py start --stack main --timeout 180

# Check status
python scripts/ops/runtime/docker/runtime_manager.py status --stack main

# Verify health
curl http://127.0.0.1:8000/health/ready
```

## Option 2: Use WSL2 Directly (Alternative)

If Docker Desktop continues to have issues, you can use WSL2 directly:

### Step 1: Install Docker in WSL2
```bash
# In WSL2 Ubuntu
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

### Step 2: Start BioETL Stack
```bash
# From the Linux filesystem mirror
cd /mnt/e/github/BioactivityDataAcquisition

# Start main stack
docker compose -f docker-compose.yml up -d

# Check status
docker compose ps
```

## Option 3: Use Python Runtime (Canonical)

Docker is optional for BioETL. The canonical runtime is Python/venv:

### Step 1: Setup Python Environment
```bash
# Install dependencies
make install

# Run tests
make test

# Run local pipeline
make run-local
```

### Step 2: Setup Optional Services
```bash
# Start Neo4j (optional, for graph memory)
docker compose -f docker-compose.neo4j.yml up -d

# Start monitoring (optional, for Grafana/Prometheus)
docker compose -f docker-compose.monitoring.yml up -d
```

## Troubleshooting

### Docker Desktop Won't Start
```powershell
# Reset WSL
wsl --shutdown

# Restart Docker Desktop
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# Wait and verify
Start-Sleep -Seconds 120
docker info
```

### Engine Pipe Disappears
```powershell
# Use the recovery script
powershell -ExecutionPolicy Bypass -File "scripts/ops/runtime/docker/restart-docker.ps1" -TimeoutSeconds 180
```

### Out of Memory Errors
```powershell
# Check free RAM
Get-ComputerInfo | Select-Object OsFreePhysicalMemory

# Ensure at least 4GB free before starting Docker stacks
# If less than 4GB, stop other applications or reduce WSL memory limit
```

### Network Issues
```powershell
# Recreate Docker networks
docker network rm bioetl-monitoring bioetl-runtime -ErrorAction SilentlyContinue
docker network create bioetl-monitoring
docker network create bioetl-runtime
```

## Current Recommendations

1. **For development:** Use Python runtime (canonical) - simpler and faster
2. **For production:** Use Docker Desktop with hardened settings
3. **For CI/CD:** Use Docker Compose with WSL2

## Next Steps

Once Docker is running:
1. Start main stack: `python scripts/ops/runtime/docker/runtime_manager.py start --stack main`
2. Verify health: `curl http://127.0.0.1:8000/health/ready`
3. Optionally start Neo4j: `docker compose -f docker-compose.neo4j.yml up -d`
4. Optionally start monitoring: `docker compose -f docker-compose.monitoring.yml up -d`

## Documentation

- `docs/DOCKER_QUICKSTART.md` - Official Docker quick start guide
- `docs/DOCKER_SETUP.md` - Detailed Docker setup instructions
- `scripts/ops/runtime/docker/` - Docker helper scripts
- `scripts/ops/runtime/mcp/` - MCP server configuration

## Support

If you continue to experience issues:
1. Check Docker Desktop logs: Help > Troubleshoot > Logs
2. Check WSL logs: `wsl --list --verbose`
3. Review BioETL memory anchors: `docs/00-project/ai/memory/agent-memory.md`
4. Contact BioETL team for assistance
