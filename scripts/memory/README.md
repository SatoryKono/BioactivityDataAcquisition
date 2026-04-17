# scripts/memory

`scripts/memory/` contains the canonical Neo4j project-memory tooling for BioETL.

## Stable entrypoints

- `python -m scripts.memory sync`
- `python -m scripts.memory query`
- `python -m scripts.ai.mcp smoke-neo4j-memory`
- `bash scripts/ai/mcp/check_neo4j_memory.sh`
- `bash scripts/memory/setup/wsl_startup.sh`
- `bash scripts/memory/prompts/print_seed.sh`

## Layout

- `sync.py` builds and optionally applies the deterministic repo graph.
- `query.py` exposes operator-facing query shortcuts.
- `scripts/ai/mcp/neo4j_memory_mcp_smoke.py` validates framed stdio behavior for the `neo4j-memory` MCP server.
- `scripts/ai/mcp/neo4j_memory_mcp_adapter.py` bridges Codex framed stdio to the upstream line-delimited server.
- `scripts/ai/mcp/` contains the MCP wrappers and verification scripts.
- `setup/` contains WSL/bootstrap tooling for the Neo4j backend.
- `prompts/` contains ready-to-paste seeding prompts for manual memory enrichment.
