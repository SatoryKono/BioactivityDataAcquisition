# [AI runtime][P2] Eliminate tracked workstation paths from the Devin MCP projection

## Summary

Resolve the explicit portability exception for tracked `.devin/config.json` so
the repository no longer commits one contributor's absolute workspace path as
part of the active Devin MCP configuration.

## Current Evidence

Verified on tracked `main`:

- `.mcp.json` and `scripts/ai/.mcp.json` contain repo-relative paths and expose
  the canonical 17-server MCP set.
- `.devin/config.json` exposes the same 17 servers, so server-set drift from the
  supplied audit is already remediated.
- `.devin/config.json` still embeds `/mnt/e/g-drive/05_AI/github/` absolute paths
  in filesystem scope, wrapper arguments, memory paths, and cache paths.
- `scripts/ai/codex/setup_mcp.py` intentionally generates `.devin/config.json`
  from the non-portable runtime projection used by local Codex settings.
- `MCP_LOCAL_RUNTIME_CONFIG.md` explicitly classifies this as a temporary
  tracked Devin exception and requires a separate owner review before making it
  portable or local-only.
- The same file also contains Devin-specific non-MCP settings that must not be
  lost by a mechanical replacement.

## Problem

The checked-in Devin config is valid only for the workstation path that last
generated it. Other clones can receive a formally valid 17-server manifest that
points to nonexistent wrappers, memory files, caches, and filesystem roots.
Regeneration then creates noisy machine-specific diffs in a tracked active
runtime file.

This is a known policy exception, not an MCP server-set or secret-management
defect. The issue should close the exception without weakening local-only
runtime guardrails.

## Owner Decision Required

Choose and document one supported strategy after verifying Devin path
semantics:

1. **Portable tracked projection** — keep `.devin/config.json` tracked but use
   repo-relative paths or supported workspace variables.
2. **Generated local config** — untrack/ignore `.devin/config.json` and generate
   it locally from the portable canonical MCP source while preserving a tracked
   sanitized template or schema.
3. **Split template and overlay** — track portable project-owned MCP intent and
   materialize machine-local paths into a separate ignored Devin overlay.

The implementation must not assume that Devin resolves relative paths the same
way as Codex, Cursor, or VS Code; that behavior must be verified or represented
as an explicit precondition.

## Proposed Scope

- Record the chosen disposition and ownership in
  `MCP_LOCAL_RUNTIME_CONFIG.md` and affected contributor guidance.
- Update `scripts/ai/codex/setup_mcp.py` so Devin generation follows the chosen
  strategy without changing the canonical 17-server set.
- Preserve existing Devin-owned top-level settings unless the owner explicitly
  reclassifies them.
- Add a regression check that rejects known workstation path prefixes in any
  tracked portable/template MCP surface.
- Keep token values in local environment inputs and wrapper scripts; do not add
  tokens to tracked JSON.
- Update focused setup tests and tracked/local classification tests.

## Non-Goals

- Do not reintroduce retired MCP servers.
- Do not broaden MCP permissions or filesystem scope beyond the repository.
- Do not make external services mandatory for BioETL runtime.
- Do not edit, create, rename, or delete any `.env` file.
- Do not increase technical-debt budgets or create a new exemption for the
  absolute paths.

## Acceptance Criteria

- No tracked MCP config or tracked Devin template contains a contributor-specific
  absolute workspace path.
- `.devin/config.json` has one explicit classification: portable tracked,
  generated local-only, or generated from a tracked template plus local overlay.
- Fresh materialization in two different temporary workspace roots does not
  create a machine-specific tracked diff.
- The generated/active Devin projection still contains exactly the sanctioned
  17 MCP servers and keeps filesystem access scoped to the repository.
- Devin-specific non-MCP settings have a documented preservation/migration
  rule.
- JSON syntax, setup tests, architecture checks, and runtime/mirror docs checks
  pass.
- Debt outcome for tracked AI runtime config is `improved`; no budget or
  exemption is raised.

## Validation

```bash
python -m json.tool .mcp.json >/dev/null
python -m json.tool scripts/ai/.mcp.json >/dev/null
python -m json.tool .devin/config.json >/dev/null  # if retained as tracked
rg -n "/mnt/e/g-drive|/mnt/wsl/docker-desktop-bind-mounts|[A-Za-z]:\\\\" \
  .mcp.json scripts/ai/.mcp.json .devin/config.json
uv run python -m pytest -q \
  tests/unit/scripts/test_setup_copilot_codex_mcp.py \
  tests/architecture/test_dev_setup_copilot_codex_mcp_consolidation.py
uv run python -m scripts.docs check-drift --runtime-mirrors --freshness
git diff --check
```

If `.devin/config.json` becomes local-only, adjust the JSON command and tests to
validate the tracked template plus a generated temporary materialization.

## Related Work

- #3427 — documented MCP local path strategy (closed)
- #3526 — runtime config inventory classification (closed)
- #5767 — `.devin/` governance decision (closed)
- #5770 — `.devin/config.json` policy classification (closed)
- #6017 — tracked-vs-local MCP policy alignment (closed)
- #6026 — canonical MCP setup convergence (closed)
- #6050 — root `.mcp.json` retention/portability (closed)

## Metadata

- Priority: P2
- Suggested labels: `ai-runtime`, `governance`, `config`, `technical-debt`
- Suggested assignee: `@SatoryKono`
- Assignee confidence: high (CODEOWNERS plus recent file history)
