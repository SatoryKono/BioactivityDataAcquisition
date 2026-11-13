______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-11-13'

______________________________________________________________________

# MCP Integration Guide

Platform detection and dynamic wrapper generation are documented in
[`development/platform-tooling.md`](development/platform-tooling.md). The
shared server-to-wrapper mapping is owned by
`scripts/ops/runtime/mcp/shared-servers.json` and validated with
`python -m scripts.ai.mcp wrappers check`.

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
3. **Post-task:** run the memory workflow only in explicitly authorized
   `read-write` mode; never store secrets in memory JSON. Apply the root
   contract's no-write pre-task flags when the task forbids file changes.

## Security

- Treat MCP configs as workstation-local
- No tracked absolute home-directory secrets
- Least privilege on GitHub tokens (`CODEX_GITHUB_PERSONAL_ACCESS_TOKEN` etc.)
- Audit tool outputs before applying destructive ops

## Validation

- Record the expected profile separately from the effective configuration of
  the ordinary user session.
- Match doctor and client route selection, then independently verify the
  expected backend, authorization and resource scope.
- Run a bounded content control through each required tool in that session;
  configuration, an open port or a tool listing does not establish readiness.
- Record failures, expected policy denials, disabled routes and untested
  controls separately; material input drift makes affected evidence STALE.
- Distinguish diagnostic reads from a server-enforced write prohibition.
  Memory and RAG checks must preserve the agreed data, response-size and
  temporary-output boundaries.

## Related

- [MCP local runtime policy](../00-project/ai/agents/policy/MCP_LOCAL_RUNTIME_CONFIG.md)
- Deployment notes: `docs/05-operations/deployment/NEO4J-MCP-INDEX.md`

- [Ordinary-session MCP evidence, 2026-11-13](../../reports/docs-evidence/mcp-ordinary-session-20261113.md)
