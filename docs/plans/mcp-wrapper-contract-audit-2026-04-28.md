# MCP Wrapper Contract Audit 2026-04-28

*Status: Supporting operational context*
*Date: 2026-04-28*

## Purpose

This note records why the named `scripts/ai/mcp/*_wrapper.*` files are outside
the safe deletion wave for scripts cleanup.

## Scope

Reviewed evidence:

- `scripts/ai/codex/setup_mcp.py`
- `scripts/ai/mcp/__main__.py`
- representative wrappers such as:
  - `scripts/ai/mcp/github-mcp-wrapper.sh`
  - `scripts/ai/mcp/mcp_prometheus_wrapper.sh`
  - `scripts/ai/mcp/mcp_neo4j_memory_wrapper.sh`
- tests:
  - `tests/architecture/test_dev_setup_copilot_codex_mcp_consolidation.py`
  - `tests/unit/scripts/test_setup_copilot_codex_mcp.py`
  - `tests/unit/scripts/ops/test_neo4j_memory_mcp_adapter.py`

## Findings

1. The wrappers are part of the generated workspace config contract.
   `scripts/ai/codex/setup_mcp.py` writes `.mcp.json`, `.vscode/mcp.json`,
   Gemini settings, and Codex config entries that point directly at these
   wrapper file paths.

2. The wrappers are not interchangeable aliases.
   They encode server-specific behavior such as:
   - repo `.env` loading
   - Docker CLI resolution and container invocation
   - credential fallback policy
   - adapter bridging for non-standard upstream transport, especially
     `mcp_neo4j_memory_wrapper.sh`

3. The wrappers are architecture-tested as named files.
   `test_dev_setup_copilot_codex_mcp_consolidation.py` locks the exact wrapper
   stems expected per MCP server and asserts platform-specific `.sh`/`.ps1`
   targets in the generated config.

4. At least one wrapper is backed by a dedicated adapter contract.
   `mcp_neo4j_memory_wrapper.sh` is validated together with
   `neo4j_memory_mcp_adapter.py`, which bridges framed MCP traffic to the
   upstream line-delimited server.

## Decision

Current decision: retain all named `scripts/ai/mcp/*_wrapper.*` files.

They are classified as contract-bound runtime surfaces, not generic
compatibility wrappers.

## Safe Future Moves

- Improve docs and tests around individual wrappers.
- Audit server-specific behavior one wrapper family at a time.
- Redesign the generated MCP config surface only in a dedicated follow-up wave.

## Unsafe Moves

- Do not collapse the named wrappers into one generic wrapper.
- Do not delete wrapper pairs only because their bodies look similar.
- Do not change wrapper file names without changing
  `scripts/ai/codex/setup_mcp.py` and the architecture tests in the same wave.

