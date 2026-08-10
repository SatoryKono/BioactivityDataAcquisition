# scripts/memory

`scripts/memory/` contains thin compatibility entrypoints and operator helpers
for the canonical project-memory implementation under `src/memory/`.

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
- `python -m scripts.memory sync` — compatibility command delegated to
  `memory.graph.sync`
- `python -m scripts.memory query` — compatibility command delegated to
  `memory.graph.query`
- `python -m scripts.ai.mcp smoke-neo4j-memory`
- `bash scripts/ai/mcp/check_neo4j_memory.sh`
- `bash scripts/memory/setup/wsl_startup.sh`
- `bash scripts/memory/prompts/print_seed.sh`

## Layout

- `__main__.py` routes the retained `sync` and `query` command names directly
  to `memory.graph.sync` and `memory.graph.query`; no duplicate implementation
  lives below `scripts/memory/`.
- `scripts/ai/mcp/neo4j_memory_mcp_smoke.py` validates framed stdio behavior for the `neo4j-memory` MCP server.
- `scripts/ai/mcp/neo4j_memory_mcp_adapter.py` bridges Codex framed stdio to the upstream line-delimited server.
- `scripts/ai/mcp/` contains the MCP wrappers and verification scripts.
- `setup/` contains WSL/bootstrap tooling for the Neo4j backend.
- `prompts/` contains ready-to-paste seeding prompts for manual memory enrichment.
