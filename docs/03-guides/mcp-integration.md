______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-07-28'

______________________________________________________________________

# MCP Integration Guide

**Issue:** #6551
**SSOT policy:** [MCP_LOCAL_RUNTIME_CONFIG.md](../00-project/ai/agents/policy/MCP_LOCAL_RUNTIME_CONFIG.md),
AGENTS.md, machine-local `.mcp.json` surfaces

## What MCP is here

Model Context Protocol servers expose **tools** (memory, graph, filesystem,
GitHub, etc.) to AI runtimes. They are **not** part of the BioETL pipeline
runtime path and must not become a requirement for Local-Only ETL execution.

## Configuration surfaces

| Surface | Role |
| --- | --- |
| `.mcp.json` / `.zed/mcp.json` | Machine-local MCP wiring (often secret-bearing) |
| `docs/00-project/ai/agents/policy/MCP_*.md` | Policy / ownership |
| `src/memory/**` | Project memory subsystem used by workflows |

**Env guardrail:** do not create/edit `.env*` without explicit user approval.

## Typical tool classes

- Memory / daily workflow (`python -m memory.tooling.workflow …`)
- Repo filesystem / GitHub for issues and PRs
- Optional Neo4j memory MCP (ops docs under `docs/05-operations/deployment/`)

## Integration patterns

1. **Pre-task:** load memory / normative sources (AGENTS.md order).
2. **During task:** use MCP tools for search/evidence; write code via normal VCS.
3. **Post-task:** memory post-task workflow; do not store secrets in memory JSON.

## Security

- Treat MCP configs as workstation-local
- No tracked absolute home-directory secrets
- Least privilege on GitHub tokens (`CODEX_GITHUB_PERSONAL_ACCESS_TOKEN` etc.)
- Audit tool outputs before applying destructive ops

## Validation

- MCP server starts without path errors on this machine
- Tools list matches expected servers for the agent host
- Memory workflow commands succeed without touching production data paths

## Related

- [MCP local runtime policy](../00-project/ai/agents/policy/MCP_LOCAL_RUNTIME_CONFIG.md)
- Deployment notes: `docs/05-operations/deployment/NEO4J-MCP-INDEX.md`
