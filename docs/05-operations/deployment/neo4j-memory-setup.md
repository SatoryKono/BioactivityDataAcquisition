---
Version: 1.0.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-04-12'
---

# Neo4j Memory Configuration Guide

> Scope note: This guide is for auxiliary Neo4j/MCP tooling only. It is not BioETL runtime deployment guidance and does not change ADR-010 Local-Only policy.

## Related Neo4j Operator Docs

- [Neo4j Audit Instance Guide](neo4j-audit-instance-guide.md)
- [Neo4j Audit Instance Quick Start](neo4j-audit-instance-quick-start.md)
- [Neo4j Audit Instance Implementation](neo4j-audit-instance-implementation.md)
- [Neo4j Complete Recovery Guide](../runbooks/neo4j-complete-recovery-guide.md)
- [Neo4j Memory Windows Verification](../verification/neo4j-memory-windows-verification.md)
- [Neo4j Memory QA Examples](../verification/neo4j-memory-qa-examples.md)

Root-level Neo4j recovery/status notes from the 2026-04 cleanup wave were moved
out of the repository root and archived under
`docs/99-archive/operations/neo4j-root-status-2026-04/`.

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
   `docker-compose.yml` now reads these optional env vars for memory tuning:
   `NEO4J_HEAP_INITIAL`, `NEO4J_HEAP_MAX`, `NEO4J_PAGECACHE_SIZE`,
   `NEO4J_TX_MAX_SIZE`, `NEO4J_GLOBAL_TX_MAX`.

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
   python -m scripts.memory sync --apply
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
   `pipeline_surface -> TESTED_BY` links. The current graph also includes
   `storage_surface` nodes for Bronze/Silver/Gold/composite/control-plane
   artifacts, `runtime_evidence_surface` anchors for
   `run_manifest` / `run_ledger` / `effective_config_artifact` / `lineage`,
   `control_plane_artifact_surface` nodes for artifact-level manifest / ledger /
   effective-config / lineage templates and indexes,
   `workflow_surface` / `workflow_job_surface` /
   `workflow_call_surface` / `workflow_matrix_variant_surface` /
   `workflow_output_surface` from `.github/workflows/*.yml`,
   `cli_command_surface` / `cli_option_surface` for command/option semantics,
   `doc_claim_surface` for claim-level documentation traceability,
   and docs-to-code `DESCRIBES` / `ASSERTS_ABOUT` drift edges from published
   docs/policies to repo code/config/workflow targets.

8. When you intentionally want to remove stale repo-derived graph nodes from the
   current ingest wave, run the explicit prune mode:
   ```bash
   python -m scripts.memory sync --apply --prune-stale
   ```
   This mode is destructive for stale repo-derived nodes and resets managed
   relations between repo-managed nodes before recreating them.

8a. For selective rebuild/debug of one graph shard without exporting the full
   repo snapshot, use one of the shard filters:
   ```bash
   python -m scripts.memory sync --export /tmp/storage-memory.json --only-storage-layer
   python -m scripts.memory sync --export /tmp/runtime-memory.json --only-runtime-evidence-layer
   python -m scripts.memory sync --export /tmp/workflow-memory.json --only-workflow-graph
   python -m scripts.memory sync --export /tmp/docs-drift-memory.json --only-docs-drift
   ```
   These filters reuse the normal deterministic builder but keep only the
   requested shard plus the minimal relation-linked context needed to inspect
   or sync it safely.

9. When you want an audit snapshot without manual Neo4j inspection, run:
   ```bash
   python -m scripts.memory sync --report /tmp/neo4j-memory-audit.json
   ```
   The report includes snapshot stats, live managed/unmanaged summaries,
   orphan counts, and label/relation diffs against the current managed wave.
   On Windows-host HTTP sync, prefer the lighter health-check mode:
   ```bash
   python -m scripts.memory sync --report-fast --report /tmp/neo4j-memory-audit.json
   ```
   This focuses on critical analysis labels/relations and is less likely to hit
   transport instability on large live-count scans.

10. When you need a full rebuild of the current managed repo graph wave, use:
   ```bash
   python -m scripts.memory sync --apply --full-reset-managed-wave
   ```
   This mode is more destructive than `--prune-stale`: it deletes the entire
   current managed wave before recreating it from the repository snapshot.

11. When you intentionally want repo-derived labels to converge to
    managed-only state, including cleanup of older unmanaged nodes from earlier
    manual/legacy ingestion waves, run:
    ```bash
    python -m scripts.memory sync --apply --full-reset-managed-wave --prune-legacy-unmanaged
    ```
    This mode keeps unrelated labels such as `MemoryEntity` intact, but it
    deletes unmanaged legacy nodes for the repo-derived label families now owned
    by deterministic sync.
    Current-cycle semantics are now projected directly onto code surfaces and
    candidate nodes as properties rather than a separate cycle label. This
    keeps Windows-host live sync stable while preserving
    `current-cycle-code`, `dead-code-candidates`, and
    removable-complexity query semantics.

12. To gate ontology drift in CI or locally without a live Neo4j backend, run:
    ```bash
    python -m scripts.ci neo4j-memory
    ```
    This checks snapshot invariants for the managed ontology layer and fails on
    missing required labels/relations, missing protocol-level port surfaces,
    missing rich contract metadata, missing pipeline-to-test or alert-to-contract
    links, missing storage/runtime/workflow/drift coverage, leaked ignored
    paths, or snapshot orphans.

13. To run a full live gate against a real local Neo4j backend, apply the
    deterministic sync, and fail on managed drift, use:
    ```bash
    python -m scripts.ci neo4j-memory-live
    ```

14. For operator-facing ownership lookups on the deterministic file-structure
    layer, use:
    ```bash
    python -m scripts.memory query owner-contract chembl.activity
    python -m scripts.memory query owner-pipeline chembl_activity
    python -m scripts.memory query owner-alert BioETLPipelineRunFailed
    python -m scripts.memory query owner-doc "architecture diagrams hub"
    python -m scripts.memory query owner-storage silver/chembl/activity
    python -m scripts.memory query owner-runtime-evidence run_manifest
    python -m scripts.memory query owner-workflow tests
    python -m scripts.memory query owner-workflow-job tests::governance-preflight
    python -m scripts.memory query owner-cli-command "scripts.memory sync"
    python -m scripts.memory query neighbors-pipeline chembl_activity
    python -m scripts.memory query neighbors-alert BioETLPipelineRunFailed
    python -m scripts.memory query neighbors-storage silver/chembl/activity
    python -m scripts.memory query neighbors-runtime-evidence run_manifest
    python -m scripts.memory query neighbors-run-instance manifest-chain-smoke
    python -m scripts.memory query neighbors-workflow tests
    python -m scripts.memory query neighbors-workflow-job tests::governance-preflight
    python -m scripts.memory query neighbors-cli-command "bioetl run"
    python -m scripts.memory query docs-drift all
    python -m scripts.memory query workflow-gates tests
    python -m scripts.memory query workflow-artifacts tests
    python -m scripts.memory query storage-lineage silver/chembl/activity
    python -m scripts.memory query field-lineage silver/chembl/activity
    python -m scripts.memory query schema-drift silver/chembl/assay
    python -m scripts.memory query run-artifacts manifest-chain-smoke
    python -m scripts.memory query runtime-state all
    python -m scripts.memory query runtime-locks all
    python -m scripts.memory query workflow-execution all
    python -m scripts.memory query claim-trace all
    python -m scripts.memory query cli-semantics "bioetl run"
    python -m scripts.memory query duplication-cluster adapter_layer:method_surface:de487f71c608
    python -m scripts.memory query promotion-candidates adapter_layer
    python -m scripts.memory query promotion-candidates all
    python -m scripts.memory query dead-code-candidates adapter_layer
    python -m scripts.memory query current-cycle-code adapter_layer
    python -m scripts.memory query overengineered-candidates composite_layer
    python -m scripts.memory query removable-complexity composite_layer
    python -m scripts.memory query simplification-blockers adapter_layer
    python -m scripts.memory query normalization-pipeline chembl_activity
    python -m scripts.memory query fallback-pipelines all
    ```

15. Normalization topology is now refreshed from current shipped evidence during
    deterministic sync. The sync derives current profile coverage from
    `NORMALIZATION_PROFILE_REGISTRY`, pulls current fallback debt from the
    generated normalization matrix/inventory pipeline, and projects that data
    onto `pipeline_surface` / `entity_config` nodes. Rebuild the graph after
    normalization changes so future audits query current evidence instead of a
    stale topology snapshot:
    ```bash
    python -m scripts.memory sync --apply
    python -m scripts.memory sync --apply-normalization-evidence-only
    python -m scripts.memory query normalization-pipeline chembl_activity
    python -m scripts.memory query fallback-pipelines all
    ```
    The normalization-only path now emits per-batch progress JSON to stderr and
    returns batch/timing telemetry in its final summary. When a live refresh
    stalls, capture the last emitted batch to see which pipeline span was in
    flight and whether the time is being spent in evidence build or Neo4j
    roundtrips.

16. For Windows-host / WSL live validation, use the fast audit as the default
    health check and treat targeted analysis-layer syncs as dependent on a
    current base graph:
    ```bash
    python -m scripts.memory sync --report-fast --report /tmp/neo4j-memory-audit.json
    python -m scripts.memory sync --apply --only-retirement-layer
    python -m scripts.memory sync --apply --only-complexity-layer
    ```
    `--report-fast` is the recommended operator path for quick local validation.
    Targeted retirement/complexity syncs assume the live graph already contains
    the required repo anchor nodes from a recent base sync. If the repository
    changed and those anchors are stale or missing, targeted sync now fails fast
    with the exact missing anchor nodes and a
    `python -m scripts.memory sync --apply --prune-stale` remediation hint instead of
    drifting into a late relation-count mismatch. After repeated targeted runs,
    prefer `--apply --prune-stale` over a plain `--apply` so stale managed rows
    from older `sync_run` values do not pollute the next base verification pass.

17. For a quick local smoke after memory-surface extensions, verify at least
    one path from each high-value coverage block:
    ```bash
    python -m scripts.memory sync --report-fast --report /tmp/neo4j-memory-audit.json
    python -m scripts.memory query owner-pipeline chembl_activity
    python -m scripts.memory query owner-contract chembl.activity
    ```
    Then inspect the exported audit JSON or Neo4j Browser for:
    - `storage_surface` such as `silver/chembl/activity`
    - `runtime_evidence_surface` such as `run_manifest`
    - `control_plane_artifact_surface` such as `run_manifest::json`
    - `workflow_surface` / `workflow_job_surface` / `workflow_call_surface`
      such as `tests`, `tests::governance-preflight`, and reusable workflow
      projections
    - `cli_command_surface` / `cli_option_surface` such as `bioetl run`
      and `--pipeline`
    - `doc_claim_surface` and `ASSERTS_ABOUT` links from high-signal policy
      lines to repo targets

## Memory Configuration Profiles

### Development (Local, 4GB host RAM)
```
NEO4J_HEAP_INITIAL=512m
NEO4J_HEAP_MAX=2g
NEO4J_PAGECACHE_SIZE=1g
NEO4J_TX_MAX_SIZE=2g
NEO4J_GLOBAL_TX_MAX=4g
```
For the lightweight standalone `docker-compose.neo4j.yml` profile on Docker Desktop,
use dedicated `NEO4J_LIGHT_*` variables so the heavier global `.env` settings do not
override the lightweight profile:
```bash
NEO4J_LIGHT_HEAP_INITIAL=256m
NEO4J_LIGHT_HEAP_MAX=1g
NEO4J_LIGHT_PAGECACHE_SIZE=256m
NEO4J_LIGHT_TX_MAX_SIZE=1g
NEO4J_LIGHT_GLOBAL_TX_MAX=2g
NEO4J_LIGHT_CONTAINER_MEMORY_LIMIT=2g
```

### Staging (8GB host RAM)
```
NEO4J_HEAP_INITIAL=1g
NEO4J_HEAP_MAX=4g
NEO4J_PAGECACHE_SIZE=2g
NEO4J_TX_MAX_SIZE=4g
NEO4J_GLOBAL_TX_MAX=8g
```

### Production (16GB+ host RAM)
```
NEO4J_HEAP_INITIAL=2g
NEO4J_HEAP_MAX=8g
NEO4J_PAGECACHE_SIZE=6g
NEO4J_TX_MAX_SIZE=8g
NEO4J_GLOBAL_TX_MAX=16g
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
| `NEO4J_PAGECACHE_SIZE` | Graph store page cache | 1g |
| `NEO4J_TX_MAX_SIZE` | Single transaction memory limit | 2g |
| `NEO4J_GLOBAL_TX_MAX` | All active transactions combined | 4g |

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
