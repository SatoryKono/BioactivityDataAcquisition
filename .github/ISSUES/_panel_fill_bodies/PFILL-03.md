## Summary

**ID** panel (`/ops/control-plane/identity-table`) fails open with `resolved_via=scope_resolve_timeout` and rows of `not available for current scope`, while **`identity-evidence`** resolves the same scope via `latest_manifest_for_scope`.

## Root cause

`handle_control_plane_identity_table` wraps `resolve_control_plane_identity_scope` in a **2.0s** timeout; evidence route does not. Slow control-plane trees hit timeout → empty identity UX.

## Fix

- Align scope resolve budget with evidence path (raise or remove timeout on resolve; keep bounded timeouts on heavy summary/checkpoint only)
- Prefer graceful partial payload over total placeholder wipe
- Do not present pipeline name as Provider.Entity when unresolved

## Acceptance

- For `chembl_activity` + run_type without exact run_id, identity-table resolves when evidence does (same resolved_via family)
- Timeout path clearly labels timeout (not generic “not available”) if still used
- Provider.Entity is null/unavailable text, not bare pipeline id, when entity unknown
