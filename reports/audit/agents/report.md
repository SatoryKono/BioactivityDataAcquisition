# Agents + memory cycle — 20260826T181707Z-agents-memory-cycle-8a79ac6e4d

| Поле | Значение |
| --- | --- |
| prompt | `prompt.audit.cycle.agents-memory` v1.1.0 |
| SHA audited | `origin/main@8a79ac6e4d` (later `813553cafc` session.md on main) |
| work branch requested | `fix/audit-cycle-agents-memory` (occupied dirty worktree; not used) |
| work branch used | `fix/audit-cycle-agents-memory-9712` @ `7d7b7f7738` |
| N / MODE | 10 / full |
| CONTOURS | runtime, scripts, memory |
| LANGUAGE | ru |
| surface_score (origin/main) | **2** |
| surface_score (after remediations on branch) | **3** (pending merge; `ALLOW_MERGE=false`) |
| P0 | 0 |
| PROVEN | 2 (1 P1, 1 P3) |
| NOT_PROVEN | 1 (vendor memory, policy-compliant) |

## Executive summary

На `origin/main@8a79ac6e4d` зеркало Codex↔Junie зелёное, memory smoke/validate зелёные, прошлые #9691/#9697/#9121 не регрессировали. Новый PROVEN P1: `.mcp.json` запускает `mcp_memory_wrapper.sh`, который не видел `.venv-win`; на native Windows Git Bash probe дал `PICK=NONE` при существующем `.venv-win`. P3: Devin py-audit-bot ссылался на memory sheet как на владельца import matrix.

Фиксы на `fix/audit-cycle-agents-memory-9712`, issues #9712 #9713, PR #9724. Merge не выполнялся.

## Contour evidence

| Contour | Evidence |
| --- | --- |
| runtime | `bash scripts/ai/junie/check_junie_mirror.sh --check` PASS; doctor static OK; Devin AGENT.md Memory section |
| scripts | Git Bash interpreter probe; `.mcp.json` → `.sh`; `.ps1` already had `.venv-win` |
| memory | `python -m memory.tooling.workflow smoke --json` ok; `memory.tooling.validate --json` issues=[]; vendor NOT_PROVEN as required |

## Issues

| Issue | Finding | Pri | Delta |
| --- | --- | --- | --- |
| #9712 | AGENTS-MEM-SCR-001 mcp_memory_wrapper.sh `.venv-win` | P1 | resolved_on_branch (PR #9724) |
| #9713 | AGENTS-MEM-RT-001 Devin memory sheet claim | P3 | resolved_on_branch (PR #9724) |

Close vs origin/main deferred (`ALLOW_MERGE=false`).

## Checks

- junie mirror PASS (exit 0)
- memory smoke PASS (not degraded)
- catalog validate PASS (`issues=[]`, including `--include-all-episodic-notes`)
- focused pytest PASS (10 passed)
- ruff touched test PASS
- doctor static PASS
- skills mirror PASS
- `python -m scripts.docs check-drift --runtime-mirrors --freshness` PASS
- `docker-compose.monitoring.yml` **not started** (not dashboard SCOPE; MONITORING=true unused)

## Debt outcome

`unchanged` (no scorecard/budget edits).

## Skipped

- Iterations 3–10: no new PROVEN findings after re-audit; empty form cycles not run.
- Dirty worktree `E:/github/wt-audit-cycle-agents-memory` not modified.
- Untracked `reports/review/nda2-findings-compact.txt` not staged.
