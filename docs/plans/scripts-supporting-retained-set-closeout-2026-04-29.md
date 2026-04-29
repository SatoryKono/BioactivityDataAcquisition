# Scripts Supporting Retained Set Closeout 2026-04-29

## Scope

This note closes the April 2026 `supporting` classification wave for the
remaining non-active scripts in `configs/quality/scripts_inventory_manifest.json`.

## Current State

The current inventory snapshot contains `26` scripts with status
`supporting`. This is no longer treated as a cleanup backlog. It is an
intentional retained set with bounded reasons per cluster.

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
- `scripts/docs/checks/_bootstrap.py`
- `scripts/docs/matrix/_bootstrap.py`

Trigger for future deletion:

- only if the remaining docs routers stop consuming the helper/bootstrap layer

### 3. Engineering support modules (`4`)

These remain retained as shared helper surfaces:

- `scripts/engineering/common/cli_dispatch.py`
- `scripts/engineering/common/repo_paths.py`
- `scripts/engineering/qa/py_review_orchestrator.py`
- `scripts/engineering/repo/_root_governance.py`

Trigger for future redesign:

- only if router dispatch, repo path loading, or root-governance helpers are
  consolidated into a different canonical shared module layout

### 4. Windows Codex launchers (`2`)

These batch files remain retained as Windows-side compatibility launchers for
mixed WSL/Codex workflows:

- `scripts/ops/launchers/codex/codex-wsl.bat`
- `scripts/ops/launchers/codex/start-codex.bat`

Trigger for future deletion:

- only after caller evidence drops to zero and a separate launcher parity wave
  confirms no remaining documented Windows workflow depends on them

### 5. Direct Vibe module compatibility entry (`1`)

- `scripts/ai/vibe/__main__.py`

This remains retained only as a module-level compatibility surface while the
canonical public Python path is `python -m scripts.ai vibe`.

Trigger for future deletion:

- caller audit proving no direct `python -m scripts.ai.vibe` usage remains, plus
  one compatibility window

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

What remains is either:

- explicit retained support surface, or
- TTL-governed diagnostic surface

and must be handled accordingly.
