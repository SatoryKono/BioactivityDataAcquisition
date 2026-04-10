---
Version: 1.0.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-04-09'
---

# Neo4j Memory Configuration Guide

> Scope note: This guide is for auxiliary Neo4j/MCP tooling only. It is not BioETL runtime deployment guidance and does not change ADR-010 Local-Only policy.

## Quick Start

1. Copy .env.example to .env:
   ```bash
   cp .env.example .env
   ```

2. Update Neo4j credentials in `.env`:
   ```bash
   NEO4J_AUTH=neo4j/your-secure-password
   NEO4J_URI=bolt://localhost:7687
   ```

3. Start Neo4j:
   ```bash
   docker compose up -d neo4j
   ```

4. Register the Neo4j Memory MCP server in Codex and VS Code workspace config:
   ```bash
   uv run python -m scripts.dev setup-mcp
   ```

5. Verify MCP registration:
   ```bash
   codex mcp get neo4j-memory
   ```

6. Access Neo4j Browser:
   - URL: http://localhost:7474/browser/
   - Username: neo4j
   - Password: (from NEO4J-AUTH)

7. Build and sync the deterministic repo graph:
   ```bash
   python -m scripts.ops sync-neo4j-memory --apply
   ```
   This snapshot now covers repo-derived docs, configs, layers/modules, tests,
   dashboards, execution paths, curated policy surfaces, and a semantic
   impact-analysis layer for ports, adapters, pipelines, contracts, and alert
   rules. The current sync also includes protocol/class-level domain ports,
   fine-grained `adapter_impl_surface` nodes for concrete adapter modules,
   `class_surface` / `function_surface` / `method_surface` code surfaces,
   `duplication_cluster` promotion candidates for high-signal families,
   richer contract-to-schema/config/control-plane/lineage links, direct pipeline
   runtime / validation / observability / test-coverage edges, and config-driven
   alert mapping from `configs/quality/neo4j_memory_mapping.yaml`, including
   `alert_surface -> OBSERVED_BY -> dashboard_surface` links derived from metric
   overlap and fallback tables. Shared/provider regression suites from
   `configs/quality/test_matrix.yaml` are also projected into direct
   `pipeline_surface -> TESTED_BY` links.

8. When you intentionally want to remove stale repo-derived graph nodes from the
   current ingest wave, run the explicit prune mode:
   ```bash
   python -m scripts.ops sync-neo4j-memory --apply --prune-stale
   ```
   This mode is destructive for stale repo-derived nodes and resets managed
   relations between repo-managed nodes before recreating them.

9. When you want an audit snapshot without manual Neo4j inspection, run:
   ```bash
   python -m scripts.ops sync-neo4j-memory --report /tmp/neo4j-memory-audit.json
   ```
   The report includes snapshot stats, live managed/unmanaged summaries,
   orphan counts, and label/relation diffs against the current managed wave.

10. When you need a full rebuild of the current managed repo graph wave, use:
   ```bash
   python -m scripts.ops sync-neo4j-memory --apply --full-reset-managed-wave
   ```
   This mode is more destructive than `--prune-stale`: it deletes the entire
   current managed wave before recreating it from the repository snapshot.

11. When you intentionally want repo-derived labels to converge to
    managed-only state, including cleanup of older unmanaged nodes from earlier
    manual/legacy ingestion waves, run:
    ```bash
    python -m scripts.ops sync-neo4j-memory --apply --full-reset-managed-wave --prune-legacy-unmanaged
    ```
    This mode keeps unrelated labels such as `MemoryEntity` intact, but it
    deletes unmanaged legacy nodes for the repo-derived label families now owned
    by deterministic sync.

12. To gate ontology drift in CI or locally without a live Neo4j backend, run:
    ```bash
    python -m scripts.ci neo4j-memory
    ```
    This checks snapshot invariants for the managed ontology layer and fails on
    missing required labels/relations, missing protocol-level port surfaces,
    missing rich contract metadata, missing pipeline-to-test or alert-to-contract
    links, leaked ignored paths, or snapshot orphans.

13. To run a full live gate against a real local Neo4j backend, apply the
    deterministic sync, and fail on managed drift, use:
    ```bash
    python -m scripts.ci neo4j-memory-live
    ```

14. For operator-facing ownership lookups on the deterministic file-structure
    layer, use:
    ```bash
    python -m scripts.ops query-neo4j-memory owner-contract chembl.activity
    python -m scripts.ops query-neo4j-memory owner-pipeline chembl_activity
    python -m scripts.ops query-neo4j-memory owner-alert BioETLPipelineRunFailed
    python -m scripts.ops query-neo4j-memory owner-doc "architecture diagrams hub"
    python -m scripts.ops query-neo4j-memory neighbors-pipeline chembl_activity
    python -m scripts.ops query-neo4j-memory neighbors-alert BioETLPipelineRunFailed
    python -m scripts.ops query-neo4j-memory duplication-cluster adapter_layer:method_surface:de487f71c608
    python -m scripts.ops query-neo4j-memory promotion-candidates adapter_layer
    python -m scripts.ops query-neo4j-memory promotion-candidates all
    python -m scripts.ops query-neo4j-memory dead-code-candidates adapter_layer
    python -m scripts.ops query-neo4j-memory current-cycle-code adapter_layer
    python -m scripts.ops query-neo4j-memory overengineered-candidates composite_layer
    python -m scripts.ops query-neo4j-memory removable-complexity composite_layer
    python -m scripts.ops query-neo4j-memory simplification-blockers adapter_layer
    ```

## Memory Configuration Profiles

### Development (Local, 4GB host RAM)
```
NEO4J-HEAP-INITIAL=512m
NEO4J-HEAP-MAX=2g
NEO4J-PAGECACHE=1g
NEO4J-TX-MAX-SIZE=2g
```

### Staging (8GB host RAM)
```
NEO4J-HEAP-INITIAL=1g
NEO4J-HEAP-MAX=4g
NEO4J-PAGECACHE=2g
NEO4J-TX-MAX-SIZE=4g
```

### Production (16GB+ host RAM)
```
NEO4J-HEAP-INITIAL=2g
NEO4J-HEAP-MAX=8g
NEO4J-PAGECACHE=6g
NEO4J-TX-MAX-SIZE=8g
NEO4J-GLOBAL-TX-MAX=50g
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
| `NEO4J-HEAP-INITIAL` | Starting JVM heap size | 512m |
| `NEO4J-HEAP-MAX` | Maximum JVM heap size | 2g |
| `NEO4J-PAGECACHE` | Graph store page cache | 1g |
| `NEO4J-TX-MAX-SIZE` | Single transaction memory limit | 2g |
| `NEO4J-GLOBAL-TX-MAX` | All active transactions combined | 20g |
| `NEO4J-JVM-OPTS` | JVM garbage collector settings | G1GC |

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
   - Increase `NEO4J-HEAP-MAX`
   - Reduce `NEO4J-PAGECACHE`
   - Optimize query patterns

4. **For High Transaction Volume**:
   - Increase `NEO4J-GLOBAL-TX-MAX`
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
