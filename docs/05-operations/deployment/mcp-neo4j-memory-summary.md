---
Version: 1.0.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-29'
---

# MCP Neo4j Memory Configuration - Setup Summary

> Scope note: This document describes auxiliary MCP tooling setup. It is not BioETL runtime deployment guidance and does not change ADR-010 Local-Only policy.

## Status: ✅ COMPLETE

MCP Neo4j Memory Management has been successfully configured for BioETL.

---

## What Was Done

### 1. Docker Compose Integration
- Added `neo4j` service to `docker-compose.yml`
- Configured with memory environment variables
- Set up health checks
- Created persistent volumes: data, logs, import
- Ports: 7474 (HTTP), 7687 (Bolt)

### 2. Environment Configuration
- Updated `.env.example` with Neo4j Memory section
- Memory profiles: development, staging, production
- Credentials configuration
- JVM tuning options

### 3. MCP Server Setup
- Created `.ai/mcp/neo4j-memory/` directory
- Implemented Python MCP server (`server.py`)
- Alternative Node.js implementation (`server.js`)
- Memory storage system (`memory.json`)
- Registered in `.codex/settings.json`

### 4. Documentation & Examples
- Full README with usage guide
- Python examples demonstrating all features
- Troubleshooting guide
- Quick reference (NEO4J-MEMORY-SETUP.md)

---

## Files Created/Modified

### Created
```
.ai/mcp/neo4j-memory/
├── __init__.py              # Package marker
├── server.py                # Python MCP server (PRIMARY)
├── server.js                # Node.js MCP server (alternative)
├── memory.json              # Configuration storage
├── examples.py              # Usage examples
├── README.md                # Full documentation
└── SETUP-COMPLETE.md        # Setup summary

NEO4J-MEMORY-SETUP.md         # Quick reference guide
```

### Modified
```
docker-compose.yml            # Added neo4j service
.env.example                  # Added Neo4j configuration
.codex/settings.json          # Registered neo4j-memory MCP
```

---

## Memory Profiles

| Profile | Host RAM | Heap | PageCache | Best For |
|---------|----------|------|-----------|----------|
| **development** | 4GB | 512m → 2g | 1g | Local dev, small datasets |
| **staging** | 8GB | 1g → 4g | 2g | Testing, medium datasets |
| **production** | 16GB+ | 2g → 8g | 6g | High throughput, large data |

---

## Quick Start

### 1. Prepare Environment
```bash
cp .env.example .env
# Edit .env and change NEO4J-AUTH password
```

### 2. Start Neo4j
```bash
docker compose up -d neo4j
```

### 3. Verify
```bash
docker compose ps neo4j              # Check status
docker stats bioetl-neo4j            # Monitor memory
docker compose logs -f neo4j         # View logs
```

### 4. Access
- Browser: http://localhost:7474/browser/
- Bolt: bolt://localhost:7687
- Credentials: neo4j / (from .env)

---

## MCP Server Usage

### Command Line
```bash
# Show current configuration
python .ai/mcp/neo4j-memory/server.py

# Run examples
python .ai/mcp/neo4j-memory/examples.py
```

### Python API
```python
from .ai.mcp.neo4j-memory.server import Neo4jMemoryMCP

mcp = Neo4jMemoryMCP()

# Get recommendations
rec = mcp.recommend-configuration(8)  # 8GB RAM
print(rec)

# Switch profile
mcp.update-memory-profile("staging")

# Export environment variables
env = mcp.export-env-file("production")

# Check health
health = mcp.check-neo4j-health()

# Save custom config
mcp.save-custom-configuration("custom", "4g", "16g", "8g")
```

---

## Available MCP Functions

| Function | Purpose |
|----------|---------|
| `get-memory-profile(profile)` | Get profile (dev/staging/prod) |
| `get-current-configuration()` | Get active config |
| `get-memory-allocation-rules()` | Get allocation rules |
| `check-neo4j-health()` | Check container health |
| `recommend-configuration(ram-gb)` | Get recommendations |
| `update-memory-profile(profile)` | Switch profile |
| `save-custom-configuration(...)` | Save custom config |
| `export-env-file(profile)` | Export as env vars |
| `get-troubleshooting-guide()` | Common issues & solutions |

---

## Configuration Reference

### Environment Variables

```bash
# Memory Settings
NEO4J-HEAP-INITIAL=512m              # Initial JVM heap
NEO4J-HEAP-MAX=2g                    # Max JVM heap
NEO4J-PAGECACHE=1g                   # Graph page cache
NEO4J-TX-MAX-SIZE=2g                 # Transaction max
NEO4J-GLOBAL-TX-MAX=20g              # Global transaction limit

# Server Settings
NEO4J-AUTH=neo4j/password            # Credentials
NEO4J-VERSION=5.15-community         # Image version
NEO4J-HTTP-PORT=7474                 # Browser port
NEO4J-BOLT-PORT=7687                 # Bolt port

# JVM Tuning
NEO4J-JVM-OPTS=-XX:+UseG1GC -XX:G1HeapRegionSize=16m
```

### Memory Allocation Rules

- **Heap**: 25-40% of available host RAM
- **PageCache**: 40-50% of available host RAM
- **OS Buffer**: 10-20% of available host RAM

Example for 16GB host:
- Heap: 6GB (37.5%)
- PageCache: 7GB (43.75%)
- OS Buffer: 3GB (18.75%)

---

## Common Tasks

### Switch to Production
```bash
# Update environment
export NEO4J-HEAP-INITIAL=2g
export NEO4J-HEAP-MAX=8g
export NEO4J-PAGECACHE=6g

# Restart
docker compose restart neo4j
```

### Monitor Performance
```bash
docker stats bioetl-neo4j --no-stream
docker compose exec neo4j cypher-shell -u neo4j -p <password> ":sysinfo"
```

### View Logs
```bash
docker compose logs neo4j -f --tail=100
```

### Connect to Shell
```bash
docker compose exec neo4j cypher-shell -u neo4j -p <password>
```

### Run Query
```bash
docker compose exec neo4j cypher-shell -u neo4j -p <password> "MATCH (n) RETURN COUNT(n)"
```

### Troubleshooting

**Out of Memory (Exit 137)**
```python
mcp = Neo4jMemoryMCP()
guide = mcp.get-troubleshooting-guide()
print(guide['out-of-memory'])
```

**Slow Queries**
- Increase `NEO4J-PAGECACHE`
- Check page cache hit ratio in `:sysinfo`
- Profile queries with `PROFILE` clause

**Connection Issues**
- Check health: `docker compose ps neo4j`
- View logs: `docker compose logs neo4j`
- Test: `docker compose exec neo4j cypher-shell -u neo4j -p <password> "RETURN 1"`

---

## Architecture

```
IDEs / Applications (Claude, Cursor, etc.)
           |
           v
   .codex/settings.json
    (MCP Configuration)
           |
           v
neo4j-memory MCP Server
           |
    +------+------+
    |      |      |
    v      v      v
Docker  Memory  Tools
Compose Storage Functions
    |
    v
Neo4j Container (bioetl-neo4j)
```

---

## Integration Points

✅ **Docker Compose**: Neo4j service configured and ready
✅ **Environment Files**: `.env` template with Neo4j variables
✅ **MCP Protocol**: Registered as "neo4j-memory" server
✅ **Python API**: Full programmatic access
✅ **CLI**: Command-line examples
✅ **Documentation**: Comprehensive guides

---

## Next Steps

1. **Copy environment template**:
   ```bash
   cp .env.example .env
   ```

2. **Update credentials**:
   - Edit `.env` and change `NEO4J-AUTH` password

3. **Start Neo4j**:
   ```bash
   docker compose up -d neo4j
   ```

4. **Verify setup**:
   ```bash
   python .ai/mcp/neo4j-memory/server.py
   ```

5. **Access Neo4j Browser**:
   - Visit: http://localhost:7474/browser/

6. **Start using**:
   - Connect application to `bolt://localhost:7687`
   - Or use `docker compose exec neo4j cypher-shell`

---

## Resources

- **Neo4j Official**: https://neo4j.com/
- **Neo4j Memory Configuration**: https://neo4j.com/docs/operations-manual/current/performance/memory-configuration/
- **Neo4j Docker**: https://neo4j.com/docker/
- **Cypher Query Language**: https://neo4j.com/docs/cypher-manual/
- **MCP Protocol**: https://modelcontextprotocol.io/
- **Docker Compose**: https://docs.docker.com/compose/

---

## Summary

✅ Neo4j Memory MCP fully configured and integrated
✅ Docker Compose service created with memory optimization
✅ Three memory profiles (dev/staging/prod) pre-configured
✅ Python MCP server with 7+ management functions
✅ Comprehensive documentation and examples
✅ Ready for production use

**Setup completed**: 2026-02-21

Let me know if you have any other questions!
