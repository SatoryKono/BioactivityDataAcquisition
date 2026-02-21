# MCP Neo4j Memory Management Server

Production-grade Model Context Protocol server for Neo4j memory management and optimization.

## Features

- 🔧 **Memory Profile Management** - Pre-configured profiles (dev/staging/prod)
- 📊 **Real-time Monitoring** - Neo4j health, memory usage, transactions
- 🎯 **Smart Recommendations** - Configuration suggestions based on available RAM
- 🐳 **Docker Support** - Containerized MCP server + Neo4j
- 🔌 **MCP Integration** - Works with Claude, Cursor, and other MCP clients
- 📈 **Performance Analysis** - Database statistics and troubleshooting

## Installation

### From Source

```bash
cd .ai/mcp/neo4j-memory

# Install dependencies
pip install fastmcp>=2.0.0 neo4j>=5.26.0

# Install package
pip install -e .
```

### Docker

```bash
cd .ai/mcp/neo4j-memory

# Build MCP server
docker build -t bioetl-neo4j-mcp:latest .

# Run both Neo4j and MCP server
docker-compose up -d
```

## Usage

### Command Line

```bash
# Start the MCP server
mcp-neo4j-memory

# Environment variables for Neo4j
export NEO4J_URL=bolt://localhost:7687
export NEO4J_USERNAME=neo4j
export NEO4J_PASSWORD=password
```

### Python API

```python
from mcp_neo4j_memory.neo4j_connection import Neo4jConnection, Neo4jSettings
from mcp_neo4j_memory.memory_manager import Neo4jMemoryManager

# Connect to Neo4j
settings = Neo4jSettings(url="bolt://localhost:7687")
conn = Neo4jConnection(settings)
conn.connect()

# Use memory manager
manager = Neo4jMemoryManager()

# Get recommendations
rec = manager.recommend_configuration(8)  # 8GB host RAM
print(rec)

# List profiles
profiles = manager.list_profiles()
print(profiles)

# Get health
health = conn.get_memory_usage()
print(health)
```

### With Docker Compose

```bash
# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f neo4j-mcp

# Stop services
docker-compose down
```

## Available MCP Tools

### Memory Profile Management

- **get_memory_profile**(profile_name) - Get profile configuration
- **list_memory_profiles()** - List all profiles
- **get_current_profile()** - Get active profile
- **set_memory_profile**(profile_name) - Activate profile
- **save_custom_profile**(...) - Create custom profile

### Recommendations & Configuration

- **recommend_memory_configuration**(available_ram_gb) - Get recommendations
- **export_environment_variables**(profile_name) - Export as env vars

### Monitoring & Health

- **check_neo4j_health()** - Full health check
- **get_memory_usage()** - Current memory usage
- **get_transaction_statistics()** - Transaction stats
- **get_database_statistics()** - Database stats

### Troubleshooting

- **get_troubleshooting_guide()** - Common issues & solutions

## Memory Profiles

### Development (4GB host)
```
Heap: 512m → 2g
PageCache: 1g
For: Local development, small datasets
```

### Staging (8GB host)
```
Heap: 1g → 4g
PageCache: 2g
For: Testing, medium datasets
```

### Production (16GB+ host)
```
Heap: 2g → 8g
PageCache: 6g
For: High throughput, large datasets
```

## Configuration

### Environment Variables

```bash
# Neo4j Connection
NEO4J_URL=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
NEO4J_DATABASE=neo4j
NEO4J_ENCRYPTED=true
NEO4J_TRUST=TRUST_ALL_CERTIFICATES

# MCP Server
NEO4J_TRANSPORT=stdio              # or http
NEO4J_MCP_SERVER_HOST=0.0.0.0
NEO4J_MCP_SERVER_PORT=8000

# Memory Configuration
NEO4J_HEAP_INITIAL=512m
NEO4J_HEAP_MAX=2g
NEO4J_PAGECACHE=1g
NEO4J_TX_MAX_SIZE=2g
NEO4J_GLOBAL_TX_MAX=20g
```

### Docker Compose

```bash
# Copy template
cp .env.example .env

# Edit environment
vim .env

# Start services
docker-compose up -d
```

## Architecture

```
IDE / Client
    |
    v
    MCP Protocol
    |
    v
Neo4j Memory MCP Server
    |
    +-- Memory Manager (profiles, recommendations)
    |
    +-- Neo4j Connection (monitoring, health)
    |
    v
Neo4j Database
```

## Development

### Setup Development Environment

```bash
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest tests/ -v
```

### Code Quality

```bash
# Type checking
mypy src/

# Linting
ruff check src/

# Formatting
black src/
```

## Troubleshooting

### Connection Issues

```python
from mcp_neo4j_memory.neo4j_connection import Neo4jConnection, Neo4jSettings

settings = Neo4jSettings()
conn = Neo4jConnection(settings)

if conn.test_connection():
    print("Connected to Neo4j")
else:
    print("Failed to connect")
```

### Out of Memory

Use the troubleshooting guide:

```bash
# Get solutions
mcp-neo4j-memory --troubleshooting
```

Or programmatically:

```python
from mcp_neo4j_memory.memory_manager import Neo4jMemoryManager

manager = Neo4jMemoryManager()
guide = manager.get_troubleshooting_guide()
print(guide['out_of_memory'])
```

## Project Structure

```
.ai/mcp/neo4j-memory/
├── src/mcp_neo4j_memory/
│   ├── __init__.py
│   ├── main.py                  # Entry point
│   ├── server.py                # MCP server
│   ├── neo4j_connection.py       # Neo4j connection
│   └── memory_manager.py         # Memory management
├── pyproject.toml               # Project metadata
├── Dockerfile                   # Container image
├── docker-compose.yml           # Full stack
├── .dockerignore
├── README.md                    # This file
└── SETUP_COMPLETE.md            # Setup guide
```

## References

- [Neo4j Documentation](https://neo4j.com/docs/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Docker Documentation](https://docs.docker.com/)
- [Python Neo4j Driver](https://neo4j.com/docs/python-manual/current/)

## License

MIT License - See LICENSE file for details

## Support

For issues and questions:
1. Check the troubleshooting guide
2. Review logs: `docker-compose logs neo4j-mcp`
3. Test connection: `python -c "from mcp_neo4j_memory.neo4j_connection import Neo4jConnection; Neo4jConnection().test_connection()"`

## Version

- **Package**: mcp-neo4j-memory 1.0.0
- **Neo4j Driver**: >= 5.26.0
- **FastMCP**: >= 2.0.0
- **Python**: >= 3.11
