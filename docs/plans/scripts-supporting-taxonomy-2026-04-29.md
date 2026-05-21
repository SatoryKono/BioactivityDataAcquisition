# Scripts Supporting Taxonomy 2026-04-29

## Purpose

This note defines how the retained `supporting` bucket should be read after the
April 2026 scripts normalization wave.

`supporting` is no longer a cleanup backlog. It is a retained non-active
surface whose subtypes are encoded directly in
`configs/quality/scripts_lifecycle_registry.json` via `decision`.

## Taxonomy

| Decision | Meaning | Typical examples |
| --- | --- | --- |
| `compatibility_wrapper` | compatibility-only entrypoint retained for historical direct callers | `scripts/memory/mcp_smoke.py`; historical example retired on 2026-05-21: `scripts/ai/vibe/__main__.py` |
| `internal_compatibility_launcher` | convenience launcher retained for mixed OS or bootstrap workflows, but not a canonical public route | historical example: retained Codex Windows facades before their promotion back to `active` during the 2026-04-29 parity refresh |
| `windows_compatibility_wrapper` | Windows-side companion retained because platform-specific filenames are part of the runtime/config contract | `scripts/ai/mcp/*_wrapper.ps1` |
| `shared_helper_module` | shared internal helper with multiple in-repo consumers, but not itself a primary command surface | `scripts/engineering/common/cli_dispatch.py`, `src/tools/neo4j_audit.py` |
| `internal_helper_orphan` | bounded internal helper retained for module/bootstrap structure, not for direct user invocation | `scripts/docs/_compat_shim.py`, `scripts/docs/checks/_bootstrap.py`, `scripts/engineering/common/repo_paths.py` |
| `legacy_manual_utility` | retained historical/manual utility kept for bounded compatibility or operator context, but not for extension | `scripts/engineering/qa/py_review_orchestrator.py` |

## Governance Rule

When a script is classified as `supporting`, the lifecycle `decision` is the
authoritative subtype. New retained non-active scripts should not introduce a
generic `supporting` rationale without one of these explicit decision classes
or an intentionally added successor class.

## Current Reading Order

Use the following order when interpreting retained non-active scripts:

1. `scripts_inventory_manifest.json` tells you the script is `supporting`
2. `scripts_lifecycle_registry.json` tells you which retained subtype it is
3. supporting closeout and parity notes explain why that subtype is retained

This keeps inventory status stable while allowing finer-grained governance
without reopening the cleanup program.
