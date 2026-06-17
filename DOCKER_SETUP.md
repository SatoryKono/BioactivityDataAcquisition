# BioETL Docker Setup Guide

## Quick Start

### Prerequisites
- Docker Desktop (macOS/Windows) or Docker Engine (Linux)
- Docker Compose v2+
- Bash or PowerShell

### Verify Installation

**Linux/macOS:**
```bash
./quickstart.sh
```

**Windows PowerShell:**
```powershell
.\docker-setup.ps1 check
```

**Or use Makefile:**
```bash
make docker-check
```

---

## Building the Image

### Build BioETL Image
The project uses a **multi-stage Dockerfile** for optimized production images:

**Linux/macOS:**
```bash
./docker-setup.sh build
# or
make docker-build
```

**Windows PowerShell:**
```powershell
.\docker-setup.ps1 build
```

**Manual:**
```bash
docker build -t bioetl:latest -f Dockerfile.bioetl .
```

---

## Starting Services

### ⭐ Option 1: Standalone Full Stack (Recommended)
Start all services in a single compose file (easiest setup, no prerequisites):

```bash
docker compose -f docker-compose.standalone.yml up -d
```

**What starts:**
- `bioetl` - Main application (http://localhost:8081)
- `neo4j` - Graph database (http://localhost:7474)
- `redis` - Cache/queue (localhost:6379)
- `minio` - S3-compatible storage (http://localhost:9001 console)
- `prometheus` - Metrics (http://localhost:9090)
- `grafana` - Dashboards (http://localhost:3000)
- `warp` - Cloudflare Warp tunnel (port 9999)

**Recommended for:**
- Local development
- Testing the full stack
- First-time setup

---

### Option 2: Main Services Only
Start just BioETL and Cloudflare Warp (minimal setup):

**Linux/macOS:**
```bash
./docker-setup.sh start
# or
make docker-start
```

**Windows PowerShell:**
```powershell
.\docker-setup.ps1 start
```

**Manual:**
```bash
docker compose up -d
```

**Note:** Requires Neo4j and monitoring network to be running separately.

---

### Option 3: Modular Services (Advanced)
Start separate infrastructure components:

**Linux/macOS:**
```bash
./docker-setup.sh start-full
# or
make docker-start-full
```

**Windows PowerShell:**
```powershell
.\docker-setup.ps1 start-full
```

**Recommended for:**
- Production deployments
- Scaling infrastructure independently
- Using separate monitoring systems

---

## Service Access Points

After starting services, access them at:

| Service | URL | Default Credentials |
|---------|-----|-------------------|
| **BioETL API** | http://localhost:8081 | - |
| **BioETL Metrics** | http://localhost:8000 | - |
| **Neo4j Browser** | http://localhost:7474 | neo4j / bioetl_secure_password |
| **Neo4j Bolt** | bolt://localhost:7687 | neo4j / bioetl_secure_password |
| **Redis** | localhost:6379 | bioetl_redis_password |
| **MinIO Console** | http://localhost:9001 | minioadmin / minioadmin123 |
| **Prometheus** | http://localhost:9090 | - |
| **Grafana** | http://localhost:3000 | admin / admin123 |

---

## Environment Configuration

### Setup .env File
Copy the example and customize as needed:

```bash
cp .env.example .env
```

**Key variables for standalone setup:**
```env
# Neo4j
NEO4J_AUTH_USERNAME=neo4j
NEO4J_AUTH_PASSWORD=bioetl_secure_password

# Redis
REDIS_PASSWORD=bioetl_redis_password

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123

# Optional API keys
BIOETL_UNIPROT_API_KEY=
BIOETL_PUBMED_API_KEY=
BIOETL_OPENALEX_API_KEY=

# Cloudflare Warp (optional)
TUNNEL_TOKEN=
```

---

## Stopping Services

### Stop Standalone Stack
```bash
docker compose -f docker-compose.standalone.yml down
```

### Stop Main Services
```bash
docker compose down
# or
make docker-stop
```

### Stop with Volumes (delete data)
```bash
docker compose -f docker-compose.standalone.yml down --volumes
```

---

## Debugging & Logs

### View All Logs
```bash
# Standalone
docker compose -f docker-compose.standalone.yml logs -f

# Or main services
make docker-logs
```

### View Specific Service Logs
```bash
# Standalone
docker compose -f docker-compose.standalone.yml logs -f bioetl

# Or main services
docker compose logs -f bioetl
# or
make docker-logs-bioetl
```

### Health Check
```bash
docker compose ps
docker compose logs bioetl | tail -20
```

---

## Shell Access

### Enter BioETL Container
```bash
# Standalone
docker compose -f docker-compose.standalone.yml exec bioetl /bin/bash

# Or main services
docker compose exec bioetl /bin/bash
# or
make docker-shell-bioetl
```

**Inside the container:**
```bash
# Run BioETL commands
bioetl --help
bioetl quarantine serve --port 8081

# Check dependencies
python -c "import bioetl; print(bioetl.__version__)"
```

### Enter Neo4j Container
```bash
docker compose -f docker-compose.standalone.yml exec neo4j cypher-shell -u neo4j -p bioetl_secure_password
```

---

## Volumes & Data Persistence

### BioETL Application Volumes
```yaml
volumes:
  - ./src:/app/src              # Source code (live reload)
  - ./configs:/app/configs      # Configuration files
  - ./data:/app/data            # Data directory
  - ./logs:/app/logs            # Application logs
```

### Named Volumes (Standalone)
- `neo4j-data` - Neo4j database files
- `redis-data` - Redis persistence
- `minio-data` - MinIO object storage
- `prometheus-data` - Prometheus metrics
- `grafana-data` - Grafana dashboards
- `warp-data` - Cloudflare Warp configuration

---

## Production Considerations

### Image Size Optimization
The multi-stage Dockerfile reduces the runtime image by:
1. Using `python:3.12-slim` base (not full)
2. Installing only production dependencies
3. Excluding dev tools and test files
4. Using .dockerignore for build context

### Security
- **Non-root user**: All containers run as non-root (`bioetl`, `warp`)
- **Read-only filesystem**: Application code is read-only
- **Health checks**: Automatic container restart on failure
- **Network isolation**: Services use isolated networks
- **Resource limits**: Check docker-compose files for CPU/memory limits

### For Production
- Use `docker-compose.yml` with modular infrastructure
- Replace default passwords in all .env files
- Enable SSL/TLS for network traffic
- Use external volumes for persistence
- Configure backup strategies for databases
- Set up monitoring and alerting

---

## Common Tasks

### Rebuild Image After Code Changes
```bash
docker compose -f docker-compose.standalone.yml build bioetl
docker compose -f docker-compose.standalone.yml restart bioetl
```

### Clear All Docker Resources
```bash
# Full cleanup
docker compose -f docker-compose.standalone.yml down --volumes
docker system prune -a --volumes

# Or selective
docker rmi bioetl:latest
```

### Monitor Resource Usage
```bash
docker stats --no-stream
```

### Check Network Connectivity
```bash
docker network ls
docker network inspect bioetl_bioetl-network
```

### Test BioETL Health Endpoint
```bash
# From host
curl http://localhost:8081/health/ready

# From container
docker compose -f docker-compose.standalone.yml exec -T bioetl curl http://127.0.0.1:8081/health/ready
```

---

## Troubleshooting

### Docker Daemon Not Running
**macOS/Windows:**
- Start Docker Desktop from Applications

**Linux:**
```bash
sudo systemctl start docker
```

### Port Already in Use
```bash
# Find what's using port 8081
lsof -i :8081

# Use different port mapping
docker compose -f docker-compose.standalone.yml down
# Edit docker-compose.standalone.yml, change ports:
#   ports:
#     - "8082:8081"  # Use 8082 instead
docker compose -f docker-compose.standalone.yml up -d
```

### Container Won't Start
```bash
# Check logs
docker compose -f docker-compose.standalone.yml logs bioetl

# Inspect container
docker inspect bioetl-app
```

### Out of Memory
```bash
# Check resource usage
docker stats

# Clear unused resources
docker system prune -a --volumes

# Check disk space
docker system df
```

### Permission Denied (Linux)
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Apply group changes (logout/login required)
newgrp docker
```

### Neo4j Won't Connect
```bash
# Check Neo4j is running
docker compose -f docker-compose.standalone.yml ps neo4j

# Check logs
docker compose -f docker-compose.standalone.yml logs neo4j

# Verify credentials match .env
grep NEO4J .env
```

---

## Advanced Usage

### Custom Environment Overrides
Create `docker-compose.override.yml`:

```yaml
services:
  bioetl:
    environment:
      LOG_LEVEL: DEBUG
    volumes:
      - ./src:/app/src:cached
```

### Development Mode with Hot Reload
```yaml
services:
  bioetl:
    volumes:
      - ./src:/app/src:cached
    command: ["quarantine", "serve", "--host", "0.0.0.0", "--port", "8081"]
```

### Using Docker BuildKit
```bash
DOCKER_BUILDKIT=1 docker build -t bioetl:latest -f Dockerfile.bioetl .
```

---

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Start services
  run: docker compose -f docker-compose.standalone.yml up -d

- name: Wait for health
  run: sleep 10

- name: Run tests in container
  run: docker compose -f docker-compose.standalone.yml exec -T bioetl pytest tests/

- name: Cleanup
  if: always()
  run: docker compose -f docker-compose.standalone.yml down --volumes
```

---

## References

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [Multi-stage Builds](https://docs.docker.com/build/building/multi-stage/)
- [Security Best Practices](https://docs.docker.com/develop/security-best-practices/)
