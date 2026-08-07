# Scripts Supporting Retained Set Closeout 2026-04-29

## Scope

This note closes the April 2026 `supporting` classification wave for the
remaining non-active scripts in `configs/quality/scripts_inventory_manifest.json`.

## Current State

The current inventory snapshot contains `27` scripts with status
`supporting`. This is no longer treated as a cleanup backlog. It is an
intentional retained set with bounded reasons per cluster.

The subtype of each retained script is governed by the `decision` field in
`configs/quality/scripts_lifecycle_registry.json`. See
`docs/99-archive/plans/scripts-supporting-taxonomy-2026-04-29.md` for the retained
subtype taxonomy.

## Retained Buckets

### 1. Windows MCP companion wrappers (`16`)

These PowerShell wrappers remain retained because the named MCP wrapper stems
and platform suffixes are part of the runtime/config contract. They are
Windows-side companions for the canonical `.sh` wrappers and are governed by
the MCP wrapper contract and deep-audit notes.

Examples:

- `scripts/ai/mcp/mcp_brave_search_wrapper.ps1`
- `scripts/ai/mcp/mcp_neo4j_memory_wrapper.ps1`
- `scripts/ai/mcp/mcp_sonarqube_wrapper.ps1`

Trigger for future redesign:

- only a coordinated `setup_mcp.py` metadata redesign with generated-config and
  test updates

### 2. Docs support modules (`3`)

These remain retained as internal docs-support helpers rather than public CLI
surfaces:

- `scripts/docs/_compat_shim.py`
- `scripts/docs/common/bootstrap.py`
- `scripts/docs/common/bootstrap.py`

Trigger for future deletion:

- only if the remaining docs routers stop consuming the helper/bootstrap layer

### 3. Engineering support modules (`6`)

These remain retained as shared helper surfaces:

- `scripts/engineering/common/cli_dispatch.py`
- `scripts/engineering/common/repo_paths.py`
- `scripts/engineering/qa/py_review_orchestrator.py`
- `scripts/engineering/repo/_root_governance.py`
- `scripts/engineering/qa/hotspot_family_metrics.py`
- `src/tools/neo4j_audit.py`

Trigger for future redesign:

- only if router dispatch, repo path loading, or root-governance helpers are
  consolidated into a different canonical shared module layout

### 4. Direct compatibility entries (`1 active, 1 retired`)

- `scripts/memory/mcp_smoke.py`

`scripts/memory/mcp_smoke.py` remains retained only as a compatibility surface
while canonical runtime behavior lives elsewhere.

Retired on 2026-05-21:

- `scripts/ai/vibe/__main__.py`

The Vibe direct module shim was removed after the in-repository caller audit
found no active `python -m scripts.ai.vibe` callers. The canonical public
surface is `python -m scripts.ai vibe`; `scripts/ai/__main__.py` now dispatches
that surface directly to the Vibe launchers/helpers.

Trigger for future deletion:

- removal of historical import/test references to `scripts.memory.mcp_smoke`

## Caller-Audit Refresh

The earlier conservative audit that treated `scripts/ops/data/__main__.py` as
`unknown / compatibility-oriented` is now stale for the live workspace
snapshot.

Current state:

- `scripts/ops/data/__main__.py` is classified `active`
- it is explicitly included in `ACTIVE_EXPLICIT_SCRIPTS`
- the inventory manifest currently records `reference_count=11`

Therefore `scripts.ops.data` is outside the retained `supporting` bucket and
should not be targeted by supporting-surface cleanup.

## Result

The scripts cleanup program is past the low-risk delete phase:

- `orphan=0`
- `unknown=0`
- `legacy=0`

What remains is explicit retained support surface governed by lifecycle
subtypes, not a residual delete queue.
