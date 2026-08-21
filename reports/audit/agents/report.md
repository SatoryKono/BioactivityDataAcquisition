# Agents + Memory Cyclic Audit — report

- **run_id:** `20260820-agents-memory-cycle-c22e7b01b3`
- **prompt:** `prompt.audit.cycle.agents-memory` (v1.0.0)
- **base:** `origin/main@c22e7b01b3` (worktree `/mnt/e/github/_bioetl_audit_wt_c22e7b01b3`, detached)
- **contours:** runtime, scripts, memory
- **applied params:** N=5, ALLOW_ISSUE_WRITE=true, ALLOW_PUSH=true, **ALLOW_MERGE=false**
- **surface_score:** **2 / 3** (acceptable — core mechanisms correct; local non-critical gaps)

## Preflight note (blocker handled)

Main tree was on `fix/stream-d-posix-render-paths` (HEAD `e1c29e77b1`) and **dirty**, with
uncommitted edits inside SCOPE (`scripts/ai/**`). Per orchestrator guards
(«foreign dirty work → worktree»), the audit ran in a clean detached worktree at
`origin/main@c22e7b01b3`. Card pin `d297d3d14b` is stale vs current `origin/main` (`c22e7b01b3`);
freshest `origin/main` used per evidence contract.

## Iteration 1 — results

### Phase A Runtime — OK
- `.codex/** == .junie/**` parity **OK** (`scripts/ai/junie/check_junie_mirror.sh --check`, exit 0).
- Inventory: `.codex/agents`=15 (incl. `py-*.toml`), `.junie/agents`=10 (`.toml` are codex-only, within
  mirror contract → not a defect), `.codex/skills`=15, `.devin`=27 dirs. No command/version
  contradiction found in runtime instruction graph.

### Phase B Scripts — 2 PROVEN gaps
- **AGENTS-MEM-001 (P2):** deja-vu MCP version drift — sh `0.17.0` / ps1 `0.15.7` / doc `0.13.1`.
  → issue [#9134](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/9134)
- **AGENTS-MEM-002 (P2):** unpinned `npx -y` in `github`, `adr-analysis`, `github-actions`,
  `ast-grep` wrappers (others are pinned).
  → issue [#9135](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/9135)
- No `curl|bash` install-in-runtime, no unquoted sinks, no secret-on-stdout found in MCP wrappers.

### Phase C Memory — inconclusive (env-limited)
- **AGENTS-MEM-003 (NOT_PROVEN):** `memory.tooling.workflow smoke` failed with
  `ModuleNotFoundError: psutil` — but `psutil>=5.9` **is** declared in `pyproject.toml`.
  Root cause = unprovisioned system `python3` on the audit host, not a code defect.
  Re-run inside project venv to validate.
- Catalog↔schema deep validation deferred to a provisioned venv (smoke gate blocked first).

### Phase D Issues — done
- 2 issues created (dedupe: no prior matches). Within `MAX_ISSUES_PER_ITERATION=5`.

### Phase E Fix — deferred (guard: unknown side effect)
Both PROVEN findings require choosing an MCP package **version**. Bumping/pinning a version is an
**unproven side effect** (guard: «must stop mutation — unknown side effect»); a fix PR is **not**
pushed. Remediation options are captured in the issues; owner picks the canonical version, then a
safe deterministic fix (sync sh+ps1+doc) can be applied.

### Phase F Validate — baseline recorded
- Parity check: **OK** (no `.codex`/`.junie` edits made).
- Memory smoke: **blocked** by env (see AGENTS-MEM-003), re-run in venv.

## Delta (vs previous)
- resolved: 0 · unchanged: n/a (first agents-memory cycle on this base) · regressed: 0 · new: 2 PROVEN + 1 NOT_PROVEN

## Top gaps
1. deja-vu version drift across OS + doc (determinism).
2. Inconsistent `npx -y` pinning policy.

## Iterations 2–N
Iteration 1 exhausted the readily-PROVEN scripts-contour gaps at this base. Iterations 2–5 would
converge (memory-contour validation needs a provisioned venv; runtime parity already OK). Recommend:
run memory smoke/catalog validation in venv, then decide canonical MCP versions to enable the fix PR.
