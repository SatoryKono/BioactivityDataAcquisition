# Root hygiene minimization issue pack (post-audit)

**Status:** implemented / closeout 2026-07-28
**Wave code:** RH
**Date:** 2026-07-28
**Closeout date:** 2026-07-28
**Implementation epic:** [#6874](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6874)
**Publish record:** `reports/quality/root-hygiene-2026-07-28-issue-publish.json`
**Mode of source audit:** read-only inventory (no code moves in the audit itself)

**SSOT / enforcement already in place:**
- `.github/root-allowlist.txt`
- `docs/00-project/governance/03-file-policy.md` §0
- `scripts/engineering/repo/_root_governance.py`
- `configs/quality/repo_structure_catalog.yaml`
- `configs/quality/root_hygiene_review_registry.yaml`
- `.github/workflows/root-hygiene.yml`
- pre-commit `audit-root-cleanliness`

**This wave is not** a greenfield “empty the root” rewrite.
**This wave is** parity repair, local clutter discipline, optional dual-doc merge, and **owner-gated** Docker adjunct rehome — without breaking Hex/DDD, ADR-010, agent runtimes, or exact-root tool contracts.

## Audit findings (summary)

| Finding | Evidence |
|---------|----------|
| Tracked root files ≈ 38 | `git ls-files` root names |
| Allowlist = 37 names | `.github/root-allowlist.txt` |
| Unexpected tracked root file | `_a.txt` (not on allowlist) |
| Local secrets/generated present on some machines | `.env`, `.env.local`, `.coverage` (must stay untracked) |
| Docker exact-root still policy MUST | `03-file-policy.md` §0 table |
| Agent roots independent of `src/bioetl` | catalog `root_tooling_roots`; AGENTS.md |

**Realistic tracked-root floor:** ~30–35 files (tool contracts dominate). Do not target a 10-file toy root.

## Constraints (all children)

- Hex / Ports & Adapters / DDD / Medallion / Composition Root intact
- **Do not** embed agent/MCP/memory into `src/bioetl`
- **Do not** increase tech-debt budgets
- Root file add/remove requires **sync**: allowlist + `03-file-policy.md` + `root_hygiene_review_registry.yaml` (+ generated routing if generated)
- No secret `.env*` tracking (only `.env.example`)
- ADR-010: optional Docker; exact compose filenames are operator contracts until repointed
- Prefer delete/ignore over allowlist growth for scratch

## Issue matrix (published)

| Code | Issue | Pri | Phase | Title |
|------|-------|-----|-------|-------|
| RH-00 | [#6874](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6874) | P1 | meta | Root hygiene minimization (post-audit) |
| RH-01 | [#6876](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6876) | P0 | 1 | Remove unexpected tracked root scratch (`_a.txt`) + parity |
| RH-02 | [#6877](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6877) | P1 | 1 | Document/verify local forbidden root outputs (`.env`, caches) |
| RH-05 | [#6878](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6878) | P2 | 2 | REVIEW: `.secrets.baseline` / `.aiignore` retention evidence |
| RH-03 | [#6880](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6880) | P2 | 3 | CONTRIBUTING dual-surface consolidation (optional) |
| RH-04 | [#6881](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6881) | P2 | 4 | Docker adjunct rehome plan (monitoring/neo4j) — owner-gated |
| RH-06 | [#6882](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6882) | P1 | 5 | Root hygiene CI/docs green after RH-01..05 |
| RH-07 | [#6883](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6883) | P3 | deferred | Further root shrink only after tool contracts drop exact-root |

## Delivery order

1. **PR-A** #6876 RH-01 (must ship first)
2. **PR-B** #6877 RH-02
3. **PR-C** #6878 RH-05
4. **PR-D** #6880 RH-03 optional
5. **PR-E** #6881 RH-04 only with owner + ADR-010 review
6. **PR-F** #6882 RH-06 validation closeout

## Exit (epic)

- [x] Tracked root files ⊆ allowlist (zero unexpected) — RH-01 removed `_a.txt`; **37 ≡ allowlist**
- [x] Root hygiene validation gates green on tip (RH-06)
- [x] No new root files without allowlist/policy/registry sync
- [x] Agent/MCP/Docker contracts unbroken — RH-04 closed **not_planned** (no owner gate)
- [x] Debt budgets not increased

### Closeout dispositions

| Code | Issue | Disposition |
|------|------:|-------------|
| RH-01 | #6876 | **done** — `git rm _a.txt` + gitignore |
| RH-02 | #6877 | **done** — local-vs-CI operator guidance |
| RH-05 | #6878 | **done** — retain both with evidence |
| RH-03 | #6880 | **done** — dual surface already stub→SSOT |
| RH-04 | #6881 | **not_planned** — owner+ADR-010 gate absent |
| RH-06 | #6882 | **done** — validation closeout |
| RH-07 | #6883 | **deferred** — tracking only; contracts bind floor |

## Rejected in this wave

- Moving `AGENTS.md` / `.mcp.json` / `pyproject.toml` / `.importlinter` without tool proof
- Merging CodeRabbit + Qodo configs
- Restoring root `.sh/.ps1/.py` launchers
- Restoring root `DOCKER_QUICKSTART.md`
- Embedding `.codex`/`.gemini` into application layers
