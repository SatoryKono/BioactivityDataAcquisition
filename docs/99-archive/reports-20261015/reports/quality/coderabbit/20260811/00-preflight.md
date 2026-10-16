# CR-FULL residual preflight — 2026-08-11

## Frozen context

- Repository: `SatoryKono/BioactivityDataAcquisition`
- Meta-epic: [#8592](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8592)
- Working branch: `audit/coderabbit-full-residual-20260811`
- Default/base ref: `origin/main`
- BASE_SHA: `8f34de1cf14126908cba8326905b3ee224719537`
- Checkout started on protected `main`; a dedicated audit branch was created before campaign writes.
- Pre-existing user diff: none. The only pre-branch untracked path was the mandatory
  memory pre-task session note created by this campaign.

## Tool and authority preflight

| Tool/context | Result |
|---|---|
| CodeRabbit CLI | `0.7.2` |
| CodeRabbit auth | authenticated as `SatoryKono`, provider `github`, region `us` |
| Python | `3.13.15` (`.venv/bin/python`) |
| uv | `0.12.3` |
| Host | WSL2/Linux |
| GitHub auth | authenticated as `SatoryKono`; token scopes include `repo` |
| Repository permission | `ADMIN` |
| `.coderabbit.yaml` | assertive profile |

## Matrix contract

- Tracked paths at BASE_SHA: **10,525**
- Assigned paths: **10,525**
- Duplicate assignments: **0**
- Missing paths: **0**
- Leaves: **87**
- Maximum leaf size: **300**
- `under_cap=true`: **87/87**
- Full matrix: `01-scope-matrix.md` / `01-scope-matrix.json`

## Execution method and risks

- CLI leaves run strictly sequentially. Because `BASE_SHA == origin/main`, each leaf is
  materialized as an isolated synthetic two-commit repository containing exactly the
  manifest paths, with the empty commit retained as branch `main`, then reviewed with
  `--base main --dir . --agent`. This avoids
  the false no-diff/`All files ignored` result while preserving original repo-relative paths.
- Each review receives `AGENTS.md`, `.coderabbit.yaml`, and `02-review-prompt.md` as config context.
- Rate limits use bounded backoff and are recorded in `BLOCKERS.md`; no busy-loop.
- CodeRabbit output is advisory. Only findings confirmed against code/config/contracts,
  accepted ADRs/RULES, and executable gates become accepted problems and GitHub issues.
- Prior de-duplication source: `reports/quality/coderabbit/20260806/`.
- No `.env` mutation, no secret output, no root scratch, no debt-budget growth.
