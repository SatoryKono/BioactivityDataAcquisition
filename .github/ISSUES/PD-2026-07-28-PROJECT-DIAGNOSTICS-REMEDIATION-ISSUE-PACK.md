# Project Diagnostics remediation issue pack

**Status:** closed (2026-07-28)  
**Wave code:** PD  
**Implementation epic:** #6838  
**Audit date:** 2026-07-28  
**Closeout date:** 2026-07-28  
**Evidence:**
- `reports/bp60.json` / `reports/bp_current.txt` — basedpyright scoped **60 errors**
- `reports/_diag_r3.txt` — architecture diagnostics **5 FAIL**

## Snapshot

| Source | Count | Notes |
|--------|------:|-------|
| basedpyright scoped (`src/bioetl`) | **60** | CI-aligned diagnostics baseline |
| Architecture closeout/governance tests | **5** | debt/inventory/routing drift |
| Full basedpyright (unscoped) | ~1633 | noise; **out of scope** for this wave |

### basedpyright by rule

| Rule | n |
|------|--:|
| `reportReturnType` | 33 |
| `reportGeneralTypeIssues` | 22 |
| `reportAssignmentType` | 4 |
| `reportMissingModuleSource` | 1 |

### Architecture FAIL list

1. `#6032` — `files_ge_250_loc=5/5` at budget (no headroom)
2. `#5748` — hotspot `files_ge_250_loc` 5 ≠ 4
3. `#6169` — zero-reference scripts 17 ≠ 32 (closeout stale high)
4. Observability HTTP targets 16 ≠ 19
5. route-gap `docs/00-project/governance/root-local-clutter-cleanup.md`

## Constraints

- Hex / DDD / Composition Root / Medallion intact
- **Debt budgets MUST NOT grow** (LOC cut / closeout sync down only)
- Prefer real typing fixes over `# type: ignore`
- No secret `.env*` edits without explicit approval
- Open docs backlog #6535–#6562 is **orthogonal** (not this wave)

## Issue matrix (published)

| Code | Issue | Pri | Title |
|------|-------|-----|-------|
| PD-00 | #6838 | P1 | meta: Project Diagnostics remediation (basedpyright 60 + arch diags) |
| PD-01 | #6841 | P1 | Protocol parameter name mismatches (Wave A) |
| PD-02 | #6839 | P1 | `object` not awaitable/iterable typing (Wave B) |
| PD-03 | #6843 | P2 | Incomplete returns / dataclass overrides / empty-tuple index (Wave C) |
| PD-04 | #6840 | P2 | Observability metric protocols + optional openpyxl (Wave D) |
| PD-05 | #6842 | P1 | Architecture diagnostics closeouts + routing + inventory (Wave E) |

## PR sequencing (suggested)

1. PR-1: #6841 + #6839 → basedpyright ≪ 60  
2. PR-2: #6843 + #6840 → basedpyright **0** scoped  
3. PR-3: #6842 → architecture diags green  

## Exit criteria (epic)

- [ ] Children closed or deferred with dated rationale
- [ ] Scoped basedpyright errors on `src/bioetl` = **0** (or residual allowlisted with issue)
- [ ] Architecture diagnostics 5 FAIL → 0
- [ ] No debt budget growth
- [ ] Evidence: refreshed `reports/bp_live.json` + pytest subset green
