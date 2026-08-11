# CodeRabbit campaign blockers

Each entry requires GitHub reconciliation before closeout.

## S01-domain-aggregates — launcher preflight error — RESOLVED

- UTC: `2026-08-11T09:04:19.221669+00:00`
- Wave: `A`
- Files: `19`
- Detail: initial synthetic repository did not expose an explicit base branch;
  CodeRabbit failed before review with `Unable to determine base branch`.
- Resolution: retain the empty commit as local branch `main`, persist
  `coderabbit.baseBranch=main`, and invoke `--base main`.
- GitHub issue: N/A — resolved launcher setup error; no product scope was reviewed.
