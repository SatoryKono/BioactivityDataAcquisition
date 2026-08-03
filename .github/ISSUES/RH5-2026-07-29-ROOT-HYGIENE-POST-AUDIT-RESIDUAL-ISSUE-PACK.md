# Root hygiene residual issue pack (post deep audit 2026-07-29)

**Status:** closed (2026-07-29)  
**Wave code:** RH5  
**Date:** 2026-07-29  
**Baseline SHA:** `0d39eda063` (local checkout at pack authoring)  
**Closeout:** tracked root 37≡allowlist; local clutter purged; registry/docs/guidance updated; RH5-05/06 deferred tracking.  
**Implementation epic:** [#7015](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7015)

**Predecessors (closed):**
- [#6874](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6874) RH post-audit meta
- [#6700](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6700) / [#6765](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6765) / [#6795](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6795) / [#6812](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6812) RH…RH4
- Docker adjunct rehome owner-gated: [#6881](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6881) / [#6797](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6797) (not_planned without new owner record)

## Snapshot (2026-07-29 read-only audit)

| Surface | Status |
|--------|--------|
| Allowlist entries | **37** (`.github/root-allowlist.txt`) |
| Tracked root files | **40** |
| Allowlist drift | **+3 unauthorized** |
| Unauthorized tracked | `_cr_one_scope.py`, `_cr_write_final.py`, `_publish_arch_cr2_issues.py` |
| Local WT | those three show as `D` (deleted working tree, still in index) |
| Governance | allowlist + `03-file-policy.md` §0 + structure catalog + `root-hygiene.yml` intact |
| Realistic tracked floor | **~32–37** (tool contracts); not a 10-file root |

### Explicit non-goals

- Allowlist **growth**
- Docker exact-root compose/Dockerfile shrink without owner audit + shim (already deferred)
- Secret-bearing `.env*` create/edit/delete without per-task user approval
- Restoring root launcher `.sh`/`.ps1`/`.py` compatibility exceptions
- Moving agent runtimes (`.codex/**`, MCP, memory) into `src/bioetl`

## Issue matrix

| Code | Issue | Pri | Title |
|------|-------|-----|-------|
| RH5-00 | [#7015](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7015) | meta | Residual root hygiene after 2026-07-29 deep audit |
| RH5-01 | [#7016](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7016) | P0 | Untrack unauthorized root scratch scripts; restore 37≡allowlist |
| RH5-02 | [#7017](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7017) | P1 | Local root clutter purge + strict-untracked green |
| RH5-03 | [#7018](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7018) | P1 | Registry/docs baseline resync after allowlist parity restore |
| RH5-04 | [#7019](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7019) | P2 | Harden guidance: ban root `_cr_*` / agent scratch `.py` reintroduction |
| RH5-05 | [#7021](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7021) | P3 | Tracking — further root shrink only after exact-root contracts drop |
| RH5-06 | [#7023](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7023) | P3 | REVIEW — `skills-lock.json` placement vs skill-installer contract |

## Delivery order

1. **PR-1** RH5-01 (P0 allowlist parity)  
2. **PR-2** RH5-02 + RH5-03 (local clutter + registry note)  
3. **PR-3** RH5-04 (guidance)  
4. **Track** RH5-05 / RH5-06 — no unsolicited shrink/move  

## Exit (epic)

- [ ] Tracked root files == allowlist (37)  
- [ ] `check-cleanliness --strict-untracked` green on clean tree  
- [ ] `root-hygiene.yml` unit/architecture tests green  
- [ ] No new root `.py` scratch without allowlist + policy + registry sync  
- [ ] Docker/agent shrink items remain owner-gated or deferred  

## Normative sources

- `docs/00-project/governance/03-file-policy.md` §0  
- `.github/root-allowlist.txt`  
- `configs/quality/repo_structure_catalog.yaml`  
- `configs/quality/root_hygiene_review_registry.yaml`  
- `.github/workflows/root-hygiene.yml`  
- `scripts/engineering/repo/audit_root_cleanliness.py`  
- Prior packs: `RH4-2026-07-28-*.md`, `RH-2026-07-28-*.md`  

## Publish record

- `reports/quality/rh5-2026-07-29-issue-publish.json`
