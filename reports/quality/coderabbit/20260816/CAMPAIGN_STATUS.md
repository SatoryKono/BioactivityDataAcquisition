# CAMPAIGN_STATUS — CR-FULL 20260816

| Field | Value |
| --- | --- |
| Campaign | `CR-FULL-20260816` |
| Parent issue | #8859 |
| BASE_SHA | `6a2c8abe8ac5501bae3fef69667c3ff09280e46c` |
| Closeout checkout | `origin/main@3809e140aa514d89d4e26eb69b637a83938b04b6` |
| Matrix leaves | 88 |
| Exact cover assignment | `coverage_ok=True` |
| Review terminal status | **partial** (55 ok / 3 too_many_files / 2 rate_limit / 1 connection_error / 27 never started) |
| Status UTC | `2026-08-18` |
| Campaign status | `retry_in_progress_service_residual` |
| CodeRabbit CLI | `0.7.3` |
| Auth | Pro seat assigned; no `.env*` mutation; usage-based billing **not** enabled |

## Leaf execution

| Status | Count |
| --- | ---: |
| ok | 55 |
| too_many_files | 3 |
| rate_limit | 2 |
| connection_error | 1 |
| never started | 27 |
| Total matrix leaves | 88 |

Retry 2026-08-18 landed `S-R-scripts-docs` as terminal `ok`. Live blocker is
CodeRabbit Pro included-review quota (`S15c-tests-residual-03` `waitTime=1620s`).
300-file leaves still need the runner `--committed` + omit-`-c` path; they were
not re-attempted after the quota stop.

Never-started leaves are listed in `progress.json` (absent keys) and `01-scope-matrix.md`.

## Findings triage

Normalized from leaf logs + `TRIAGE_OVERRIDES.json` via `scripts/ops/coderabbit/normalize_findings.py`.

| Triage status | Count |
| --- | ---: |
| confirm | 360 |
| reject | 2848 |
| pending | 0 |
| Normalized records | 3208 |
| Linked to a GitHub issue | 360 |

## Product streams

All implementation streams in `STREAMS.md` are **closed**. Residual exact-cover
gap is CodeRabbit service quota / timeout, not an open product defect stream.

## Guardrails

- No `.env*` mutation
- No tech-debt budget / exemption / threshold / hotspot-cap increase
- No invented findings for blocked leaves
- Code/tests/contracts outrank CodeRabbit wording
