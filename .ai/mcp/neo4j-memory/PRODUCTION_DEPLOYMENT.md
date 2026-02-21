# MCP Neo4j Memory - Production Deployment Guide

Complete guide for deploying the Neo4j Memory Management MCP server in production.

## Overview

This is a production-grade MCP server implementation using fastmcp that provides:

✅ Neo4j memory management and optimization
✅ Real-time health monitoring
✅ Containerized deployment (Docker + docker-compose)
✅ 12 MCP tools for comprehensive memory management
✅ Integration with Neo4j 5.x

## Project Structure

```
.ai/mcp/neo4j-memory/
├── src/mcp_neo4j_memory/
│   ├── __init__.py              # Package initialization
│   ├── main.py                  # Entry point (mcp-neo4j-memory command)
│   ├── server.py                # MCP server with 12 tools
│   ├── neo4j_connection.py       # Neo4j driver wrapper (test, health, stats)
│   └── memory_manager.py         # Memory profile management
│
├── pyproject.toml               # Build config (hatchling)
├── Dockerfile                   # Python 3.13.8 slim image
├── docker-compose.yml           # Neo4j + MCP server stack
├── .dockerignore
├── README.md                    # Usage documentation
└── SETUP_COMPLETE.md            # Initial setup summary
```

## Quick Start - Local Development

### 1. Install

```bash
cd .ai/mcp/neo4j-memory
pip install -e .
```

### 2. Start Neo4j Separately

```bash
# In another terminal
docker compose -f docker-compose.yml up neo4j -d
```

### 3. Run MCP Server

```bash
# Connects to neo4j:7687 by default (inside docker network)
export NEO4J_URL=bolt://localhost:7687
export NEO4J_PASSWORD=bioetl_secure_password
mcp-neo4j-memory
```

## Production Deployment

### Option 1: Docker Compose (Recommended for Simple Deployments)

```bash
# 1. Set environment
cp .env.example .env
vim .env  # Update NEO4J_AUTH, NEO4J_PASSWORD

# 2. Start full stack
docker-compose up -d

# 3. Verify
docker-compose ps
docker-compose logs neo4j-mcp
```

### Option 2: Docker Only (MCP Server)

```bash
# 1. Build image
docker build -t bioetl-neo4j-mcp:latest .

# 2. Run container
docker run -d \
  --name bioetl-neo4j-mcp \
  -e NEO4J_URL=bolt://neo4j-host:7687 \
  -e NEO4J_USERNAME=neo4j \
  -e NEO4J_PASSWORD=your-password \
  -p 8000:8000 \
  bioetl-neo4j-mcp:latest
```

### Option 3: Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: neo4j-mcp-server
spec:
  replicas: 1
  selector:
    matchLabels:
      app: neo4j-mcp
  template:
    metadata:
      labels:
        app: neo4j-mcp
    spec:
      containers:
      - name: neo4j-mcp
        image: bioetl-neo4j-mcp:latest
        ports:
        - containerPort: 8000
        env:
        - name: NEO4J_URL
          value: "bolt://neo4j:7687"
        - name: NEO4J_USERNAME
          value: "neo4j"
        - name: NEO4J_PASSWORD
          valueFrom:
            secretKeyRef:
              name: neo4j-credentials
              key: password
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
```

## MCP Tools Reference

### Memory Profiles (5 tools)

1. **get_memory_profile**(profile_name: str)
   - Get configuration for a profile
   - Returns: heap, pagecache, transaction limits

2. **list_memory_profiles()** → dict
   - List all available profiles
   - Returns: All profiles (built-in + custom)

3. **get_current_profile()** → dict
   - Get currently active profile
   - Returns: Current profile configuration

4. **set_memory_profile**(profile_name: str) → dict
   - Activate a profile
   - Returns: Success confirmation

5. **save_custom_profile**(...) → dict
   - Create custom profile
   - Args: name, description, heap_initial, heap_max, pagecache, etc.
   - Returns: Success confirmation

### Recommendations & Configuration (2 tools)

6. **recommend_memory_configuration**(available_ram_gb: float) → dict
   - Get recommendations based on host RAM
   - Returns: Recommended heap, pagecache, and allocation percentages

7. **export_environment_variables**(profile_name?: str) → dict
   - Export profile as environment variables
   - Returns: NEO4J_HEAP_INITIAL, NEO4J_HEAP_MAX, NEO4J_PAGECACHE, etc.

### Monitoring & Health (4 tools)

8. **check_neo4j_health()** → dict
   - Full health check
   - Returns: Connected status, server info, memory config, memory usage, transactions, database stats

9. **get_memory_usage()** → dict
   - Current memory usage
   - Returns: total_bytes, used_bytes, free_bytes, max_bytes, used_percent

10. **get_transaction_statistics()** → dict
    - Transaction stats
    - Returns: active_transactions, avg_age_ms, max_age_ms

11. **get_database_statistics()** → dict
    - Database stats
    - Returns: nodes count, relationships count

### Troubleshooting (1 tool)

12. **get_troubleshooting_guide()** → dict
    - Common issues and solutions
    - Returns: Guides for OOM, slow queries, transaction timeouts

## Configuration

### Environment Variables

```bash
# Neo4j Connection
NEO4J_URL=bolt://neo4j:7687              # Neo4j URL
NEO4J_USERNAME=neo4j                     # Username
NEO4J_PASSWORD=password                  # Password
NEO4J_DATABASE=neo4j                     # Database name
NEO4J_ENCRYPTED=true                     # Encryption enabled
NEO4J_TRUST=TRUST_ALL_CERTIFICATES       # Certificate trust

# MCP Server Transport
NEO4J_TRANSPORT=stdio                    # stdio or http
NEO4J_MCP_SERVER_HOST=0.0.0.0           # Listen address
NEO4J_MCP_SERVER_PORT=8000              # Listen port
NEO4J_MCP_SERVER_PATH=/mcp/              # Server path
NEO4J_MCP_SERVER_ALLOWED_HOSTS=localhost,127.0.0.1
```

### Docker Environment (.env)

```bash
# Neo4j Service
NEO4J_VERSION=5.15-community
NEO4J_HTTP_PORT=7474
NEO4J_BOLT_PORT=7687
NEO4J_AUTH=neo4j/your_secure_password

# Memory Settings
NEO4J_HEAP_INITIAL=512m
NEO4J_HEAP_MAX=2g
NEO4J_PAGECACHE=1g
NEO4J_TX_MAX_SIZE=2g
NEO4J_GLOBAL_TX_MAX=20g

# MCP Server
NEO4J_MCP_SERVER_PORT=8000
```

## Health Checks

### Docker

```bash
# Container health
docker inspect bioetl-neo4j-mcp --format='{{.State.Health.Status}}'

# Service connectivity
docker-compose ps

# Check logs
docker-compose logs neo4j-mcp -f --tail=50
```

### Manual

```bash
# Python import test
python -c "from mcp_neo4j_memory import Neo4jMemoryMCP; print('OK')"

# Direct MCP connection test (if HTTP transport)
curl -X POST http://localhost:8000/rpc -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

## Monitoring

### Memory Usage

```bash
# Docker stats
docker stats bioetl-neo4j-mcp

# Get via MCP tool
mcp call get_memory_usage
```

### Transaction Activity

```bash
# Get via MCP tool
mcp call get_transaction_statistics

# Real-time monitoring
watch -n 5 'mcp call get_transaction_statistics'
```

### Health Status

```bash
# Full health check
mcp call check_neo4j_health

# Database stats
mcp call get_database_statistics
```

## Troubleshooting

### Connection Failed

```python
from mcp_neo4j_memory.neo4j_connection import Neo4jConnection, Neo4jSettings

settings = Neo4jSettings(url="bolt://localhost:7687")
conn = Neo4jConnection(settings)

if not conn.test_connection():
    print("Cannot connect to Neo4j")
    # Check: Is Neo4j running? Port correct? Credentials?
```

### MCP Server Not Starting

```bash
# Check logs
docker-compose logs neo4j-mcp

# Verify dependencies
pip list | grep fastmcp
pip list | grep neo4j

# Test import
python -c "import fastmcp; import neo4j; print('OK')"
```

### Memory Issues

```bash
# Get troubleshooting guide
mcp call get_troubleshooting_guide

# Check current memory
mcp call get_memory_usage

# Get recommendations for your host
mcp call recommend_memory_configuration --args '{"available_ram_gb": 8}'
```

## Development

### Setup Dev Environment

```bash
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest tests/ -v --cov=src/mcp_neo4j_memory
```

### Code Quality

```bash
# Type checking
mypy src/

# Linting
ruff check src/

# Formatting
black src/ --check
```

## Performance Considerations

### Memory Allocation Rules

- **Heap**: 25-40% of host RAM (JVM memory)
- **PageCache**: 40-50% of host RAM (graph data cache)
- **OS Buffer**: 10-20% of host RAM (system operations)

Example for 16GB host:
- Heap: 6GB (37.5%)
- PageCache: 7GB (43.75%)
- OS Buffer: 3GB (18.75%)

### Scaling

For production:
1. Use `production` profile (8g heap, 6g pagecache)
2. Monitor actual usage with `get_memory_usage()`
3. Adjust based on workload patterns
4. Use custom profiles for specific needs

## Security

### Credentials

```bash
# Use environment variables (never in code)
export NEO4J_PASSWORD=$(aws secretsmanager get-secret-value --secret-id neo4j-password --query SecretString --output text)

# Or use secrets management
docker run -e NEO4J_PASSWORD="$(cat /run/secrets/neo4j_password)" ...
```

### Network

```bash
# Restrict MCP server port to internal network
docker-compose down
# Edit docker-compose.yml: "8000:8000" → "127.0.0.1:8000:8000"
docker-compose up -d

# Or use firewall rules in production
```

## Backup & Recovery

```bash
# Backup Neo4j data
docker exec bioetl-neo4j neo4j-admin database dump neo4j /var/lib/neo4j/backups/neo4j-dump-$(date +%Y%m%d).dump

# Restore from backup
docker exec bioetl-neo4j neo4j-admin database load neo4j /var/lib/neo4j/backups/neo4j-dump-20250221.dump --overwrite-existing
```

## References

- [fastmcp Documentation](https://github.com/modelcontextprotocol/python-sdk)
- [Neo4j Python Driver](https://neo4j.com/docs/python-manual/)
- [Neo4j Memory Configuration](https://neo4j.com/docs/operations-manual/current/performance/memory-configuration/)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)

## Support

For issues:
1. Check troubleshooting guide: `mcp call get_troubleshooting_guide`
2. Review logs: `docker-compose logs neo4j-mcp`
3. Test connectivity: Verify Neo4j is running and accessible
4. Check configuration: Verify all environment variables are set

## Version

- **mcp-neo4j-memory**: 1.0.0
- **fastmcp**: >= 2.0.0
- **neo4j**: >= 5.26.0
- **Python**: >= 3.11
- **Neo4j Server**: 5.x

---

Setup completed. The system is ready for production use.
