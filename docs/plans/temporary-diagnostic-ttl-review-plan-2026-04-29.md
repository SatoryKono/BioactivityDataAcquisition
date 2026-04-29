# Temporary Diagnostic TTL Review Plan

*Status: supporting_context*
*Date: 2026-04-29*

Freshness note: the bounded TTL execution waves on `2026-04-29` fully closed
the `temporary_diagnostic` bucket. This document now remains as historical
policy context; the live closeout state is recorded in
`docs/plans/temporary-diagnostic-program-closeout-2026-04-29.md`.

## Purpose

This note closes the scripts inventory cleanup wave by defining a bounded review
policy for the remaining `temporary_diagnostic` scripts. These files are not
treated as orphaned debris, but they are also not stable public workflow
surface. Each item must converge to exactly one end state:

- promote to `active`
- retain as `temporary_diagnostic` with renewed review date
- delete after the bounded troubleshooting need expires

## Current Baseline

Historical baseline at the time this plan was created:

- `scripts=367`
- `active=322`
- `supporting=25`
- `temporary_diagnostic=20`
- `orphan=0`
- `unknown=0`
- `legacy=0`

## Review Buckets

### Bucket A: AI / MCP local smoke helpers

Files:

- `scripts/ai/codex/helper/test-basic.sh`
- `scripts/memory/mcp_smoke.py`
- `scripts/ops/observability/grafana/live_tracing_mode_smoke.py`

Intent:

- retained only while there is no governed automated validation lane covering
  the same manual smoke path

Exit criteria:

- promote to `active` only if a documented workflow or test lane adopts them
- otherwise remove after equivalent automated validation exists

Recommended next review:

- `2026-07-15`

### Bucket B: Windows / WSL interactive convenience launchers

Files:

- `scripts/engineering/dev/bash/.setup_wsl_codex.sh`

Intent:

- retained only as bounded environment bootstrap or operator convenience
  surface during mixed Windows/WSL setup stabilization

Exit criteria:

- delete once the canonical setup path is reduced to governed `scripts.engineering.dev`
  and retained Codex launchers, with no live operator dependency on these
  helpers

Recommended next review:

- `2026-06-30`

### Bucket C: Local test / cache repair helpers

Files:

Bucket C was closed by the 2026-04-29 TTL execution waves after the remaining
local repair helpers were either removed or reclassified.

### Bucket D: Neo4j audit / recovery troubleshooting

Files:

- `scripts/ops/runtime/docker/restart-docker.ps1`
- `scripts/ops/runtime/health/start_health_server.ps1`
- `scripts/ops/runtime/neo4j/neo4j-recovery-checklist.ps1`
- `scripts/ops/runtime/neo4j/neo4j_quick_start.sh`
- `scripts/ops/runtime/neo4j/start-neo4j-audit.ps1`
- `scripts/ops/runtime/neo4j/start-neo4j-audit.sh`
- `src/tools/neo4j_audit.py`

Intent:

- retained only as bounded operator-side troubleshooting surface around local
  Neo4j / memory / health workflows

Exit criteria:

- promote to `active` only if these become documented stable operator commands
- otherwise delete or fold into canonical `scripts/ops` / package APIs after the
  graph-memory audit flow is consolidated

Recommended next review:

- `2026-07-15`

### Bucket E: Historical analysis helper

Files:

- `scripts/engineering/qa/hotspot_family_metrics.py`

Intent:

- retained only while the newer hotspot baseline and report flow is still being
  validated against the older analysis helper

Exit criteria:

- promote to `active` if the project decides to keep hotspot-family metrics as a
  governed report surface
- otherwise delete when the replacement baseline/report flow is accepted

Recommended next review:

- `2026-06-30`

### Bucket F: Legacy workstation bootstrap helper

Files:

- `scripts/ai/mistrall/helper/download-image.ps1`

Intent:

- retained only for bounded legacy workstation image/bootstrap recovery

Exit criteria:

- delete once no documented operator path still depends on manual image download

Recommended next review:

- `2026-06-30`

## Review Protocol

At each review point:

1. Re-run `python3 scripts/engineering/repo/check_scripts_inventory.py --update --forbid-evaluate-active --lifecycle-registry configs/quality/scripts_lifecycle_registry.json`
2. Confirm whether each bucket still has a live troubleshooting need.
3. For any file still retained, either:
   - keep `temporary_diagnostic` and refresh `review_by`
   - promote to `active`
   - delete and remove its lifecycle entry

## Non-Goals

- This note does not reopen the `supporting` wrapper cleanup wave.
- This note does not change the retained MCP wrapper decision.
- This note does not classify retained `supporting` modules as diagnostics.
