# Neo4j Memory Configuration Guide

## Quick Start

1. Copy .env.example to .env:
   ```bash
   cp .env.example .env
   ```

2. Update Neo4j credentials in .env:
   ```bash
   NEO4J_AUTH=neo4j/your_secure_password
   ```

3. Start Neo4j:
   ```bash
   docker compose up -d neo4j
   ```

4. Access Neo4j Browser:
   - URL: http://localhost:7474/browser/
   - Username: neo4j
   - Password: (from NEO4J_AUTH)

## Memory Configuration Profiles

### Development (Local, 4GB host RAM)
```
NEO4J_HEAP_INITIAL=512m
NEO4J_HEAP_MAX=2g
NEO4J_PAGECACHE=1g
NEO4J_TX_MAX_SIZE=2g
```

### Staging (8GB host RAM)
```
NEO4J_HEAP_INITIAL=1g
NEO4J_HEAP_MAX=4g
NEO4J_PAGECACHE=2g
NEO4J_TX_MAX_SIZE=4g
```

### Production (16GB+ host RAM)
```
NEO4J_HEAP_INITIAL=2g
NEO4J_HEAP_MAX=8g
NEO4J_PAGECACHE=6g
NEO4J_TX_MAX_SIZE=8g
NEO4J_GLOBAL_TX_MAX=50g
```

## Memory Allocation Rules

- **Heap Size**: 25-40% of available host RAM
  - Initial: ~1/4 of max heap
  - Max: Keep room for OS and page cache
  
- **Page Cache**: 40-50% of available host RAM
  - Stores graph data pages
  - Critical for query performance
  
- **Transaction Memory**: Leave 10-20% for OS buffer

## Configuration Explanation

| Setting | Purpose | Default |
|---------|---------|---------|
| `NEO4J_HEAP_INITIAL` | Starting JVM heap size | 512m |
| `NEO4J_HEAP_MAX` | Maximum JVM heap size | 2g |
| `NEO4J_PAGECACHE` | Graph store page cache | 1g |
| `NEO4J_TX_MAX_SIZE` | Single transaction memory limit | 2g |
| `NEO4J_GLOBAL_TX_MAX` | All active transactions combined | 20g |
| `NEO4J_JVM_OPTS` | JVM garbage collector settings | G1GC |

## Health Check

```bash
# Check if Neo4j is healthy
docker compose ps neo4j

# View logs
docker compose logs neo4j

# Test connectivity
docker compose exec neo4j cypher-shell -u neo4j -p <password> "RETURN 1"
```

## Useful Commands

```bash
# Start Neo4j only
docker compose up -d neo4j

# Restart Neo4j
docker compose restart neo4j

# View real-time logs
docker compose logs -f neo4j

# Stop Neo4j
docker compose down neo4j
```

## Performance Tuning Tips

1. **Monitor Memory Usage**:
   ```bash
   docker stats bioetl-neo4j
   ```

2. **Check Heap Usage**:
   - Open Neo4j Browser (http://localhost:7474/browser/)
   - Run: `:sysinfo`

3. **If Out of Memory (OOM)**:
   - Increase `NEO4J_HEAP_MAX`
   - Reduce `NEO4J_PAGECACHE`
   - Optimize query patterns

4. **For High Transaction Volume**:
   - Increase `NEO4J_GLOBAL_TX_MAX`
   - Consider connection pooling in application

## Ports

- **7474**: HTTP (Neo4j Browser UI)
- **7687**: Bolt (Binary Protocol - for apps)

## Volumes

- `neo4j-data/`: Graph database store
- `neo4j-logs/`: Application logs
- `neo4j-import/`: Import directory for bulk loading

## Sources

- Neo4j Memory Configuration: https://neo4j.com/docs/operations-manual/current/performance/memory-configuration/
- Neo4j Docker: https://neo4j.com/docker/
- Neo4j Cypher: https://neo4j.com/docs/cypher-manual/current/
