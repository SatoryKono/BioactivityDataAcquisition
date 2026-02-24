# Plan: Consolidation of 7 Codex Branches (12:45–13:20 MSK) into main

*Date: 2026-02-24 | Author: Claude Code*

---

## Branches

| # | Branch | Commit | Category |
|---|--------|--------|----------|
| 1 | `codex/update-version-in-documentation-and-add-ci-check` | `799a588dc` | CI/CD |
| 2 | `codex/update-documentation-for-current-version` | `cf49c8e80` | CI/CD |
| 3 | `codex/add-preflight-cleanup-script-with-dry-run` | `2adee9a96` | Cleanup |
| 4 | `codex/document-file-categories-for-data-directory` | `2ffb5d917` | Data Gov |
| 5 | `codex/update-adr-baseline-and-checklists` | `054682c04` | Arch Tests |
| 6 | `codex/update-documentation-with-latest-values-and-paths` | `a2300aadd` | Docs |
| 7 | `codex/update-git-setup-and-pre-flight-script` | `5efcec7b9` | Docs |

All branches: +1 commit ahead, -8 behind `origin/main`. Common ancestor exists.

---

## Conflict Analysis

### Trial merges against `origin/main`

| # | Branch | Result | Conflict files |
|---|--------|--------|----------------|
| 1 | `update-version-in-documentation-and-add-ci-check` | **CONFLICT** | `docs/00-project/index.md` |
| 2 | `update-documentation-for-current-version` | **CONFLICT** | `docs/00-project/index.md`, `docs/00-project/00-map.md` |
| 3 | `add-preflight-cleanup-script-with-dry-run` | CLEAN | — |
| 4 | `document-file-categories-for-data-directory` | CLEAN | — |
| 5 | `update-adr-baseline-and-checklists` | CLEAN | — |
| 6 | `update-documentation-with-latest-values-and-paths` | CLEAN | — |
| 7 | `update-git-setup-and-pre-flight-script` | CLEAN | — |

### Conflict root cause

`main` changed `docs/00-project/index.md` line 57 (CHANGELOG link), while branches 1 & 2
both reformatted the same file (markdown table alignment + version bump `v5.9.0` → `v6.0.0`).

### Cross-branch overlap

Branches 1 and 2 touch the same file (`index.md`) with nearly identical formatting changes.
Branch 1 is a superset of branch 2 (4 version sources vs 2). **Recommendation: take branch 1, skip branch 2.**

### Sequential merge test (5 clean branches)

Branches 3→4→5→6→7 merge sequentially into `main` **without any conflicts**.

---

## Recommended Merge Strategy

### Step 1: Merge 5 clean branches via PRs (no conflicts)

Order chosen by independence and risk (lowest first):

```
1. codex/add-preflight-cleanup-script-with-dry-run       — independent tooling
2. codex/update-git-setup-and-pre-flight-script           — independent docs
3. codex/update-documentation-with-latest-values-and-paths — independent docs
4. codex/document-file-categories-for-data-directory      — removes 45MB binaries
5. codex/update-adr-baseline-and-checklists               — adds arch test
```

Each is a single commit, zero conflicts. Can be merged as individual PRs or
squash-merged. No rebase needed.

### Step 2: Resolve conflict for branch 1, skip branch 2

**Branch 1** (`update-version-in-documentation-and-add-ci-check`):
- Rebase onto `main` (after Step 1 merges)
- Resolve `index.md` conflict: accept branch 1's version bump (`v6.0.0`) + `main`'s CHANGELOG URL fix
- Merge via PR

**Branch 2** (`update-documentation-for-current-version`):
- **SKIP** — it's a subset of branch 1:
  - `check_docs_version_sync.py` checks 2 sources (pyproject + index.md)
  - `check_version_consistency.py` from branch 1 checks 4 sources (pyproject + init.py + index.md + CHANGELOG)
- Delete branch after branch 1 is merged

### Step 3: Post-merge cleanup

```bash
# Delete merged remote branches
git push origin --delete codex/add-preflight-cleanup-script-with-dry-run
git push origin --delete codex/update-git-setup-and-pre-flight-script
git push origin --delete codex/update-documentation-with-latest-values-and-paths
git push origin --delete codex/document-file-categories-for-data-directory
git push origin --delete codex/update-adr-baseline-and-checklists
git push origin --delete codex/update-version-in-documentation-and-add-ci-check
git push origin --delete codex/update-documentation-for-current-version
```

---

## Summary

| Action | Branches | PRs |
|--------|----------|-----|
| Merge clean (as-is) | #3, #4, #5, #6, #7 | 5 PRs |
| Rebase + resolve conflict | #1 | 1 PR |
| Skip (duplicate) | #2 | — |
| Delete after merge | All 7 | — |
| **Total** | **6 merged, 1 skipped** | **6 PRs** |

### Value delivered

| Branch | What it adds |
|--------|-------------|
| #1 | `scripts/check_version_consistency.py` + CI steps in 2 workflows |
| #3 | `scripts/preflight_cleanup.sh` + `make clean-preflight` |
| #4 | `scripts/validate_data_dir.py` + removes 45MB .xlsx from repo |
| #5 | ADR status validation test in architecture test suite |
| #6 | AGENT.md, CLAUDE.md, ORCHESTRATION.md synced to v6.0.0 |
| #7 | Git preflight guard doc + cleanup assistant prompt |
