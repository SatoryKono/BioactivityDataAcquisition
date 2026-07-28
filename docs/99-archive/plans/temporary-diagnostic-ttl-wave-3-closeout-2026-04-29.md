# Temporary Diagnostic TTL Wave 3 Closeout 2026-04-29

## Scope

This note records the third bounded execution wave against the
`temporary_diagnostic` bucket, focused on remaining cheap smoke and duplicate
helper surfaces outside the Neo4j/operator troubleshooting cluster.

## Deleted

- `scripts/engineering/dev/bash/.setup_wsl_codex.sh`
- `scripts/ops/observability/grafana/live_tracing_mode_smoke.py`

Reason:

- both files had zero live references in the current inventory snapshot
- the WSL setup flow already has a documented active helper surface at
  `scripts/engineering/dev/.setup_wsl_codex.sh`
- the Grafana tracing-mode smoke script had no maintained docs, tests, or
  router callers keeping it alive

## Reclassified

- `scripts/memory/mcp_smoke.py`
  - from `temporary_diagnostic`
  - to `supporting`

Reason:

- it is a backward-compatible import shim, not a disposable troubleshooting
  script
- tests still import `scripts.memory.mcp_smoke`
- the canonical implementation already lives in
  `scripts.ai.mcp.neo4j_memory_mcp_smoke`

## Explicit Non-Changes

- `scripts/ai/codex/helper/test-basic.sh` remains `temporary_diagnostic`
  because it is still referenced in live setup/install docs as a manual
  verification step
- `scripts/engineering/dev/.setup_wsl_codex.sh` remains `active`
  because it is the documented WSL/Codex setup helper in active docs

## Updated Inventory Baseline

After this wave:

- `scripts=355`
- `active=319`
- `supporting=28`
- `temporary_diagnostic=8`
- `orphan=0`
- `unknown=0`
- `legacy=0`

## Remaining TTL Focus

The remaining `temporary_diagnostic` bucket is now mostly the heavier operator
and Neo4j troubleshooting cluster, plus the documented Codex quick-test helper.
