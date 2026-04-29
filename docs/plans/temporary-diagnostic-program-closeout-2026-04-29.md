# Temporary Diagnostic Program Closeout 2026-04-29

## Scope

This note closes the `temporary_diagnostic` scripts program that was introduced
to prevent the scripts inventory cleanup wave from stalling on mixed operator,
smoke, and convenience tails.

## Final Outcome

The `temporary_diagnostic` bucket is now empty.

Final inventory baseline after the April 29 execution waves:

- `scripts=354`
- `active=325`
- `supporting=29`
- `temporary_diagnostic=0`
- `orphan=0`
- `unknown=0`
- `legacy=0`

## What Happened

Across the bounded TTL waves:

- zero-reference one-shot helpers were removed
- dead Windows/WSL convenience helpers were removed
- duplicate helper copies were removed where a documented canonical path already
  existed
- bounded diagnostics that turned out to be shared helpers or compatibility
  shims were reclassified into `supporting`
- documented operator/runbook commands were promoted into `active`

## Final Classifications For The Last Remaining Items

Promoted to `active`:

- `scripts/ai/codex/helper/test-basic.sh`
- `scripts/ops/runtime/docker/restart-docker.ps1`
- `scripts/ops/runtime/neo4j/neo4j-recovery-checklist.ps1`
- `scripts/ops/runtime/neo4j/neo4j_quick_start.sh`
- `scripts/ops/runtime/neo4j/start-neo4j-audit.ps1`
- `scripts/ops/runtime/neo4j/start-neo4j-audit.sh`

Retained as `supporting`:

- `src/tools/neo4j_audit.py`
- `scripts/memory/mcp_smoke.py`

Deleted in the final phase:

- `scripts/ops/runtime/health/start_health_server.ps1`

## Result

The scripts inventory no longer has any unresolved cleanup-class backlog:

- no `orphan`
- no `unknown`
- no `legacy`
- no `temporary_diagnostic`

What remains is an explicit split between:

- `active` maintained workflow surface
- `supporting` retained helper / compatibility surface

## Follow-Up

Future scripts work should no longer reopen a generic cleanup queue. It should
instead operate through:

- caller-audit-driven deprecation
- explicit retained-surface redesign
- policy/governance updates when a helper changes classification
