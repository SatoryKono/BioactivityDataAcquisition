# External Resource Inventory

Status: active
Owner: BioETL Team
Scope: Issue #12478 (COMP-004) / #12552

This inventory lists external resources created, managed, or accessed by BioETL.
The bounds of this inventory strictly target resources directly instantiated and managed by the current `main` codebase.

| Identity/Type | Production Entrypoint / Call Path | Scope | Creator | Owner | Closer | Shutdown Contract |
| --- | --- | --- | --- | --- | --- | --- |
| `httpx.AsyncClient` | `bioetl.infrastructure.adapters.http.client.UnifiedHTTPClient` (`_client` member) | HTTP API Client requests | `UnifiedHTTPClient.__aenter__` (via `HTTPClientContextMixin`) | `UnifiedHTTPClient` (composition root / factories inject `rate_limiter`, etc.) | `UnifiedHTTPClient.__aexit__` (via `HTTPClientContextMixin`) | Native `await self._client.aclose()` invoked safely. Circuit breakers / Rate limiters reset/flushed independently. |
| `DeltaTable` (Read) | `bioetl.infrastructure.quarantine.unified.UnifiedQuarantine` and `bioetl.infrastructure.storage.delta.table_ops` | Quarantine / Silver Delta Lake Reads | Instantiated inline (e.g. `DeltaTable(self.base_path)`). | Local Scope (Method-bound) | N/A (Rust/Native GC) | No explicit `.close()` required by `deltalake.DeltaTable`. |
| `write_deltalake` | `bioetl.infrastructure.quarantine.unified.UnifiedQuarantine` | Quarantine / Silver Delta Lake Writes | Invoked inline (e.g. `write_deltalake(...)`). | Local Scope (Method-bound) | N/A (Rust/Native GC) | Blocking/Synchronous write. No long-lived connections. |

*Note on Missing/Excluded Items:*
- **Memory monitor:** `BatchMemoryManagerService` and the executor builders accept
  an optional `MemoryMonitorPort` through dependency injection, and
  `bioetl.infrastructure.system.memory_monitor.MemoryMonitor` is the concrete
  implementation. No production instantiation of that implementation is present
  under `src/bioetl`; the creator and lifecycle owner are therefore
  `NOT_VERIFIABLE` in the current production tree, so it is excluded from the
  confirmed-resource rows above.
- **Neo4j:** No active production Neo4j drivers or external writers are implemented in the `src/bioetl` scope (except for docker-compose mock targets, which are non-code external resources).
- **Postgres/Databases:** No persistent databases configured or instantiated directly within the code (state/persistence relies exclusively on DeltaLake/Parquet via `deltalake`).
