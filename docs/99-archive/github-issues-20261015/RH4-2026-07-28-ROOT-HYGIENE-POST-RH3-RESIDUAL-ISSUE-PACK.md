# Root hygiene residual issue pack (post-RH3 re-audit)

**Status:** implemented / closeout 2026-07-28  
**Wave code:** RH4  
**Predecessors:** #6700 (RH), #6765 (RH2), #6795 (RH3) — closed  
**Implementation epic:** #6812  
**Audit date:** 2026-07-28 (read-only residual map after RH3 closeout)  
**Closeout date:** 2026-07-28

## Snapshot

| Surface | Status |
|--------|--------|
| Tracked root files | **37** |
| Allowlist entries | **37** (exact match; drift **0**) |
| Live root files | **42** |
| Live root dirs | **38** |
| Tracked residual | **none** |
| Primary residual | **recreated local sinks** + **root-cause writer** (`docker-watchdog` → `logs/`) |

### Live untracked files of interest

| Path | Class | Notes |
|------|-------|-------|
| `_tmp_check_helper_ratio.py` | agent scratch | gitignored `_tmp_*.py`; fails `--strict-untracked` |
| `_tmp_issue_6787_closeout.py` | agent scratch | same |
| `.env`, `.env.local` | secret lane | non-automated; no touch without approval |
| `.mcp-server-context.md` | generated MCP | retain while client uses |
| `nul` / `NUL` | Windows pseudo | ignored; often non-unlinkable |

### Live dirs of interest

| Path | Notes |
|------|-------|
| `logs/docker-watchdog/` | **Writer found:** `scripts/ops/runtime/docker/watchdog-docker-stable.ps1` default `$StateDir = Join-Path $Root 'logs\docker-watchdog'` |
| caches/venvs/editor trees | expected local (`.pytest_cache`, `.venv*`, `.idea`, …) |

### Explicit non-goals (do not re-open)

- Docker exact-root compose/Dockerfile shrink — closed **not_planned** as #6797 with consumer map
- Allowlist growth
- Secret-bearing `.env*` automation
- Root script shim restoration

## Issue matrix (published)

| Code | Issue | Pri | Title |
|------|-------|-----|-------|
| RH4-00 | #6812 | P2 | meta: residual root hygiene after RH3 closeout |
| RH4-01 | #6814 | P1 | Purge recreated agent `_tmp_*.py` and root `logs/` |
| RH4-02 | #6816 | P1 | Relocate docker-watchdog default state out of root `logs/` |
| RH4-03 | #6813 | P2 | Agent scratch placement: ban root `_tmp_*.py` in guidance |
| RH4-04 | #6815 | P3 | Tip root-hygiene regression smoke (37≡37) |

## Constraints

- Hex / DDD / Composition Root / Medallion intact
- Agent runtimes stay out of `src/bioetl`
- No debt budget growth
- No `.env*` create/edit/delete without explicit per-task user approval
- Allowlist shrink-only
- Long-lived logs belong under `reports/logs/`, not root `logs/` (`03-file-policy.md` §0)

## Normative sources

- `docs/00-project/governance/03-file-policy.md` §0
- `.github/root-allowlist.txt`
- `configs/quality/root_hygiene_review_registry.yaml`
- `docs/00-project/governance/root-local-clutter-cleanup.md`
- `.github/workflows/root-hygiene.yml`
- `scripts/ops/runtime/docker/watchdog-docker-stable.ps1`
