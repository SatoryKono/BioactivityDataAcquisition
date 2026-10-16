# Root hygiene residual issue pack (post-RH2 re-audit)

**Status:** closed (2026-07-28)  
**Wave code:** RH3  
**Predecessors:** #6700 (RH), #6765 (RH2) — both closed  
**Audit date:** 2026-07-28 (read-only residual map after RH2)  
**Closeout date:** 2026-07-28

## Snapshot

| Surface | Status |
|--------|--------|
| Tracked root files | **37** |
| Allowlist entries | **37** (exact match) |
| Live root files | **41** |
| Live root dirs | **39** |
| Tracked residual | **none** |
| Primary residual | **recurring local untracked sinks** + deferred Docker exact-root shrink |

### Live untracked files (present)

- `.coverage` (generated)
- `.env`, `.env.local` (secret-bearing; non-automated)
- `.mcp-server-context.md` (generated MCP context)

### Live local dirs of interest (recreated after RH2)

- `logs/`, `test-output/` (ignored local sinks)
- caches/venvs/editor trees (expected local)

## Issue matrix (published)

| Code | Issue | Pri | Title |
|------|-------|-----|-------|
| RH3-00 | #6795 | P2 | meta: residual root hygiene after RH2 closeout |
| RH3-01 | #6799 | P1 | Recurring local root sinks: logs/, test-output/, .coverage, nul |
| RH3-02 | #6798 | P2 | Operator recurring-cleanup checklist (prevent re-clutter) |
| RH3-03 | #6797 | P2 | Docker exact-root shrink implementation gate (future multi-PR) |
| RH3-04 | #6796 | P3 | Tip root-hygiene regression smoke (allowlist 37≡37) |

Predecessors closed: #6700, #6765.
## Constraints

- No secret-bearing `.env*` edits without explicit per-task approval
- No allowlist growth; shrink-only when tool contracts change
- Agent runtimes stay out of `src/bioetl`
- No root script shim restoration
