# scripts/memory

`scripts/memory/` contains compatibility entrypoints and operator helpers for
the Neo4j project-memory tooling.

The canonical graph implementation now lives under `src/memory/graph/`.
Canonical graph-owned YAML surfaces now also live there:

- `src/memory/graph/mappings.yaml`
- `src/memory/graph/ontology.yaml`

## Stable entrypoints

- `bash scripts/memory/run_workflow.sh …` — preferred agent entry for
  `python -m memory.tooling.workflow` (`pre-task` / `post-task` / `smoke` /
  `review-curated`). Selects repo `.venv` and sets `PYTHONPATH=src:<repo>`.
- `python -m memory.tooling.workflow …` — canonical module entry (see
  `src/memory/DAILY_WORKFLOW.md`).
- `python -m scripts.memory sync`
- `python -m scripts.memory query`
- `python -m scripts.ai.mcp smoke-neo4j-memory`
- `bash scripts/ai/mcp/check_neo4j_memory.sh`
- `bash scripts/memory/setup/wsl_startup.sh`
- `bash scripts/memory/prompts/print_seed.sh`

## Layout

- `sync.py` is now a compatibility module alias to `memory.graph.sync`.
- `query.py` is now a compatibility module alias to `memory.graph.query`.
- `scripts/ai/mcp/neo4j_memory_mcp_smoke.py` validates framed stdio behavior for the `neo4j-memory` MCP server.
- `scripts/ai/mcp/neo4j_memory_mcp_adapter.py` bridges Codex framed stdio to the upstream line-delimited server.
- `scripts/ai/mcp/` contains the MCP wrappers and verification scripts.
- `setup/` contains WSL/bootstrap tooling for the Neo4j backend.
- `prompts/` contains ready-to-paste seeding prompts for manual memory enrichment.
