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
## S01-domain-control_plane — rate_limit

- UTC: `2026-08-11T09:40:42.031056+00:00`
- Wave: `A`
- Files: `32`
- Detail: CodeRabbit rate limit
- GitHub issue: [#8603](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8603)
## S01-domain-control_plane — error

- UTC: `2026-08-11T09:51:48.084492+00:00`
- Wave: `A`
- Files: `32`
- Detail: CodeRabbit exit code 1
- GitHub issue: pending reconciliation

## S01-domain-entities — error

- UTC: `2026-08-11T09:52:00.867947+00:00`
- Wave: `A`
- Files: `28`
- Detail: CodeRabbit exit code 1
- GitHub issue: pending reconciliation

## S01-domain-exceptions — error

- UTC: `2026-08-11T09:52:12.646466+00:00`
- Wave: `A`
- Files: `24`
- Detail: CodeRabbit exit code 1
- GitHub issue: pending reconciliation

## S01-domain-filtering — error

- UTC: `2026-08-11T09:52:24.539011+00:00`
- Wave: `A`
- Files: `13`
- Detail: CodeRabbit exit code 1
- GitHub issue: pending reconciliation

