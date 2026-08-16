# CR-FULL residual preflight — 2026-08-16

Parent issue: [#8859](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8859)

## Frozen context

- Repository: `SatoryKono/BioactivityDataAcquisition`
- Intended working branch: `fix/issue-8859-coderabbit-exact-cover`
- Default/base ref: `origin/main`
- BASE_SHA: `6a2c8abe8ac5501bae3fef69667c3ff09280e46c`
- Checkout at preflight: `main` at the same SHA (`HEAD == origin/main`)
- Source-bound contract: #8849 — all leaf reviews materialize from this SHA via
  `git archive`, not from a moving working tree
- Pre-existing unrelated dirty path (excluded, not committed):
  `src/memory/episodic/tasks/bioactivitydataacquisition/b5393af69d37a674/main/d82b5aab6e4483f0/`
- Campaign writes stay under `reports/quality/coderabbit/20260816/` plus the
  sequential runner helpers in `scripts/ops/coderabbit/run_leaves.py`

## Tool and authority preflight

| Tool/context | Result |
|---|---|
| CodeRabbit CLI | `0.7.2` (`/home/fedor/.local/bin/coderabbit`) |
| CodeRabbit auth | authenticated as `SatoryKono`, provider `GitHub`, region `US`, Plan `Pro`, seat assigned |
| Python (WSL runner) | `3.14.4` |
| Python (Windows tests) | `.venv-win` |
| Host | Windows + WSL2/Linux |
| Git LFS | `git-lfs/3.7.1` available; tracked LFS files listed (167), checkout=true |
| `.coderabbit.yaml` | assertive profile |
| Credentials | WSL `coderabbit auth` cache; no `.env*` mutation; no key material in artifacts |

## Matrix contract

- Tracked paths at BASE_SHA: **10954**
- Assigned paths: **10954**
- Duplicate assignments: **0**
- Missing paths: **0**
- Leaves: **88**
- Maximum leaf size: **300**
- `under_cap=true`: **88/88**
- `coverage_ok=True`
- Full matrix: `01-scope-matrix.md` / `01-scope-matrix.json`

## Execution method and risks

- CLI leaves run strictly sequentially on one API identity. Do not parallelize.
- Because `BASE_SHA == origin/main`, each leaf is materialized as an isolated
  synthetic two-commit repository containing exactly the manifest paths, with
  the empty commit retained as branch `main`, then reviewed with
  `--base main --dir . --agent`.
- Each review receives `AGENTS.md`, `.coderabbit.yaml`, and `02-review-prompt.md`.
- Rate-limit events honor CodeRabbit `waitTime` (observed 30 minutes on
  2026-08-13). Default backoff is `1800,1800,1800` seconds. Persistent
  `rate_limit` / connection errors / missing `review_completed` remain blocking.
- CodeRabbit output is advisory. Only findings confirmed against
  code/config/contracts, accepted ADRs/RULES, and executable gates become
  accepted problems and GitHub issues.
- Do not reopen already fixed #8643/#8644/#8645/#8652 findings unless a fresh
  reproduction proves regression on this BASE_SHA.
- No `.env` mutation, no secret output, no root scratch, no debt-budget growth.
