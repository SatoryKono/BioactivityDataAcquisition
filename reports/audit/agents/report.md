# Agents + memory cycle report

- run_id: `20260820T071500Z-agents-memory-cycle-c22e7b01`
- pin sequence: `origin/main@d297d3d14b` (audit base `origin/main@c22e7b01b3`)
- branch: `fix/audit-seq-d297d3d14b-agents-memory`
- N: 5
- CONTOURS: runtime, scripts, memory
- surface_score: **2** (acceptable). Mapping: no P0; three PROVEN P1/P2 remediated in iteration 1; residual vendor memory stays policy `NOT_PROVEN`; related SNR #9065 remains open outside this finding set.
- ALLOW_MERGE: false

## Preflight

- Foreign dirty work in primary checkout → worktree from `origin/main`.
- SCOPE paths exist.
- `bash scripts/ai/junie/check_junie_mirror.sh --check` → Junie mirror parity OK.
- `python -m memory.tooling.workflow smoke --json` → `ok: true`.
- `python -m scripts.docs check-drift --runtime-mirrors` → 0 errors.
- `python -m scripts.ai.prompts check` → OK, 0 errors.

## Contour evidence

| Contour | Result |
| --- | --- |
| runtime | Codex↔Junie parity green. `.junie/guidelines.md` was missing AGENTS.md Environment Configuration (#9120, fixed). |
| scripts | No `curl\|bash`. `check_junie_mirror` requires `--check`/`--sync`. `runtime_skills.py` defaults check. `governance.py`/`cursor.py`/`windsurf.py` defaulted to write (#9119, fixed). |
| memory | Catalog architecture tests green. Actor provenance required. Vendor registry correctly `NOT_PROVEN`. `run_workflow.sh` missed `.venv-win` (#9121, fixed). Smoke green. |

## Iterations

1. Audit + issues #9119 #9120 #9121 + fixes + tests.
2. Re-verify sync CLI default is check-only.
3. Re-verify guidelines Environment Configuration + mirror check.
4. Re-verify run_workflow.sh `.venv-win` order.
5. Memory smoke + catalog tests; no new P0/P1.

## Residual (not issues)

- Vendor-hosted memory remains `BLOCKED_EXTERNAL` / `NOT_PROVEN` by policy.
- SNR RF-006 #9065 (48 Sonar findings in scripts/ai and workflows) — do not duplicate.
- `docs/reports/evidence/project-test-health/SUMMARY.md` freshness 8d>7d is outside SCOPE.

## Issues

| Issue | Finding | Status |
| --- | --- | --- |
| #9119 | AGENT-SYNC-001 | fixed this PR |
| #9120 | AGENT-JUNIE-001 | fixed this PR |
| #9121 | AGENT-MEM-001 | fixed this PR |
