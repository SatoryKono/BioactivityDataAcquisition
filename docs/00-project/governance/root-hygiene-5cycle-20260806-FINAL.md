# Root Hygiene 5-Cycle FINAL — 2026-08-06

**Branch:** `audit/root-hygiene-5cycle`  
**CYCLE_COUNT:** 5  
**Status:** SUCCESS  
**End tip:** `fdf589c75c` on `audit/root-hygiene-5cycle`

## Preflight

| Item | Value |
| --- | --- |
| Repo | SatoryKono/BioactivityDataAcquisition |
| Base `origin/main` at start | `2d1b60ecb4` |
| Work branch | `audit/root-hygiene-5cycle` (not protected main) |
| `gh` | available (SatoryKono, repo scope) |

## Before / after metrics

| Metric | Before (C1 Stage 1) | After (C5) |
| --- | ---: | ---: |
| Tracked root files (allowlist surface) | 37 | 37 |
| Allowlist entries | 37 | 37 |
| Structure MUST | 2 (`reports/**/*.py`) | 0 |
| Structure SHOULD | 0 | 0 |
| Root cleanliness layout | OK | OK |
| Root local `mcp-shell.log` / `NUL` | present | absent |
| Root local `logs/` / `test-output/` | present | purged |

## Issue ledger

| Cycle | Issue | Title | Disposition |
| ---: | ---: | --- | --- |
| 1 | #8060 | PYTHON_LOCATION under reports (CR residual py) | CLOSED — moved to `scripts/ops/coderabbit/` |
| 1 | #8067 | Root local clutter mcp-shell.log / NUL | CLOSED — deleted |
| 2 | #8081 | Sync scripts inventory after relocation | CLOSED — manifest sync |
| 2 | #8082 | Document skills-lock.json exact-root retain | CLOSED — 03-file-policy |
| 3 | #8086 | Purge local logs/ and test-output | CLOSED — cleanup tooling |
| 3 | #8087 | audit_structure Windows encoding | CLOSED — UTF-8/ASCII-safe logs |
| 4 | #8089 | Refresh root-local-clutter-cleanup.md | CLOSED — re-verify 2026-08-06 |
| 4 | #8090 | Document scripts/ops/coderabbit in TOOLS.md | CLOSED |
| 5 | #8092 | FINAL report + no-op verification | CLOSED — this document |

## Cycle summaries

### Cycle 1
- Stage 1: structure MUST on `reports/quality/coderabbit/20260806-full/{build_matrix,run_leaves}.py`; local clutter.
- Stage 2: #8060 (existing) + #8067.
- Stage 3: git mv to `scripts/ops/coderabbit/`; purge clutter; structure 0 MUST.

### Cycle 2
- Stage 1: inventory residual; skills-lock retention undocumented in policy table.
- Stage 2: #8081, #8082.
- Stage 3: sync-inventory; file-policy row for skills-lock.

### Cycle 3
- Stage 1: empty local logs/test-output; audit_structure UnicodeEncodeError on Windows.
- Stage 2: #8086, #8087.
- Stage 3: cleanup-root-local-clutter --apply --include-logs; encoding-safe CLI logging.

### Cycle 4
- Stage 1: tracked root stable 37≡allowlist; docs stale.
- Stage 2: #8089, #8090.
- Stage 3: governance + TOOLS docs refresh.

### Cycle 5
- Stage 1: no new confirmed root defects; gates green.
- Stage 2: no open RH-5C issues; created #8092 for FINAL.
- Stage 3: no-op verification + this FINAL report.

## Validation gates (C5)

```text
python -m scripts.engineering.repo check-cleanliness
python -m scripts.engineering.diagnostics audit-structure --path .
python -m scripts.engineering.repo check-inventory
python -m scripts.engineering.repo check-root-review-registry
python -m scripts.engineering.repo check-root-governance-docs
```

All green at C5 (inventory informational orphan=5 pre-existing helpers; not root allowlist defects).

## Non-goals / retained at root

- Docker compose/Dockerfile exact-root entrypoints (MUST stay; policy table).
- `skills-lock.json`, `best_practices.md`, `AGENTS.md`, `GEMINI.md`, dual `.mcp.json` sync surface.
- Agent runtime roots (`.codex`, `.junie`, `.devin`, …) — not moved into `src/bioetl`.
- Secret `.env` — never touched.

## Technical debt budgets

Not increased.

## Remaining open blockers

None for RH-5C scope.

## Final status

**SUCCESS** — five full cycles executed; confirmed issues fixed and closed; root inventory stable at 37; structure MUST zero.
