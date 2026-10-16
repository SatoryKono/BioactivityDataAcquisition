# Root hygiene minimization issue pack (re-audit 2026-07-28)

**Status:** implemented 2026-07-28 (closeout pending GH comments)  
**Wave code:** RH2  
**Predecessor epic:** #6700 (closed 2026-07-27)  
**Implementation epic:** #6765  

**Normative sources:**
- `docs/00-project/governance/03-file-policy.md` §0
- `.github/root-allowlist.txt`
- `configs/quality/root_hygiene_review_registry.yaml`
- `configs/quality/repo_structure_catalog.yaml`
- `.github/workflows/root-hygiene.yml`
- `docs/00-project/governance/root-local-clutter-cleanup.md`

## Audit snapshot (working tree)

| Surface | Status |
|--------|--------|
| Tracked root files (`git ls-files` root) | **37** |
| Allowlist entries | **37** (exact match) |
| Live root names (files+dirs) | **~92** (mostly untracked local caches/tools) |
| Tracked root hygiene residual | **none** (allowlist-clean) |
| Primary reduction opportunity | **local untracked clutter**, not tracked allowlist shrink |

## Constraints

- Hexagonal / DDD / Composition Root / Medallion unchanged
- Agent runtimes (`.codex`, `.devin`, curated `.vibe`/`.zed`) stay independent of `src/bioetl`
- No debt budget growth
- No secret-bearing `.env*` edits without explicit per-task user approval
- Do not move exact-root tool contracts without owner-approved repoint (`pyproject.toml`, `uv.lock`, `AGENTS.md`, `GEMINI.md`, `.mcp.json`, Docker compose/Dockerfile, vendor configs)
- Root `.sh`/`.ps1`/`.py`/`.bat` compatibility shims must not be restored

## Issue matrix (published)

| Code | Issue | Pri | Title |
|------|-------|-----|-------|
| RH2-00 | #6765 | P1 | meta epic: root hygiene minimization after 2026-07-28 re-audit |
| RH2-01 | #6766 | P1 | Local untracked root clutter cleanup (operator / machine-local) |
| RH2-02 | #6767 | P2 | Optional gitignore hardening for Windows root oddities |
| RH2-03 | #6768 | P2 | Docker exact-root disposition re-evaluation (shim-first future shrink) |
| RH2-04 | #6769 | P3 | Root hygiene CI/allowlist regression smoke on tip |
| RH2-05 | #6770 | P3 | Secret-bearing root env lane remains non-automated |

Predecessor closed epic: #6700.
## Exit criteria (epic)

- [ ] Children closed or deferred with dated rationale
- [ ] Tracked root remains allowlist-clean (37 or shrink-only)
- [ ] Local clutter reduced on developer machines per operator doc
- [ ] `root-hygiene` workflow still green
- [ ] No layer violations / no budget growth
