# MCP Neo4j Memory Management Server

Production-grade Model Context Protocol server for Neo4j memory management and optimization.

## Features

- 12 MCP tools for memory management
- Real-time Neo4j health monitoring
- Pre-configured memory profiles (dev/staging/prod)
- Docker containerization
- Full type hints and error handling

## Installation

```bash
pip install -e .ai/mcp/neo4j-memory
```

## Usage

### Command Line

```bash
export NEO4J_PASSWORD=password
mcp-neo4j-memory
```

### Docker

```bash
cd .ai/mcp/neo4j-memory
docker-compose up -d
```

### Python API

```python
from mcp_neo4j_memory.memory_manager import Neo4jMemoryManager

manager = Neo4jMemoryManager()
profiles = manager.list_profiles()
rec = manager.recommend_configuration(8)  # For 8GB RAM
```

## 12 MCP Tools

### Memory Profiles (5)
- `get_memory_profile` - Get profile configuration
- `list_memory_profiles` - List all profiles
- `get_current_profile` - Get active profile
- `set_memory_profile` - Activate profile
- `save_custom_profile` - Create custom profile

### Configuration (2)
- `recommend_memory_configuration` - Get recommendations
- `export_environment_variables` - Export as env vars

### Monitoring (4)
- `check_neo4j_health` - Full health check
- `get_memory_usage` - Memory statistics
- `get_transaction_statistics` - Transaction stats
- `get_database_statistics` - Database stats

### Troubleshooting (1)
- `get_troubleshooting_guide` - Solutions for common issues

## Memory Profiles

| Profile | Heap | PageCache | Use Case |
|---------|------|-----------|----------|
| development | 512m→2g | 1g | Local dev (4GB host) |
| staging | 1g→4g | 2g | Testing (8GB host) |
| production | 2g→8g | 6g | High throughput (16GB+) |

## Configuration

Set environment variables:

```bash
NEO4J_URL=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
NEO4J_DATABASE=neo4j
NEO4J_TRANSPORT=stdio  (or http)
```

## Project Structure

```
.ai/mcp/neo4j-memory/
├── src/mcp_neo4j_memory/
│   ├── __init__.py
│   ├── main.py
│   ├── server.py          (12 MCP tools)
│   ├── neo4j_connection.py
│   └── memory_manager.py
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Next Steps

1. Test locally: `mcp-neo4j-memory`
2. Or use Docker: `docker-compose up -d`
3. Call tools via MCP
4. Read PRODUCTION_DEPLOYMENT.md for deployment patterns

Status: **Production Ready** ✅
