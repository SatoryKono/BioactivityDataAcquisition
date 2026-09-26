# FINAL — CR-FULL residual campaign 20260816

Parent: [#8859](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8859)

## Verdict

**PARTIAL COMPLETE** with documented CodeRabbit service residual.

The campaign froze an exact-cover matrix of **88** leaves over **10954** tracked
paths (`coverage_ok=True`) at `BASE_SHA=6a2c8abe8ac5501bae3fef69667c3ff09280e46c`.
CodeRabbit CLI returned usable finding streams for **43** leaves. **5** timed
out, **1** hit `rate_limit`, and **39** never started. Those leaves are **not**
treated as clean reviews.

All independently confirmed product defects from successful leaves were filed
into exclusive streams and those streams are **closed** on
`origin/main@6ddd5185552cd98a29ff33ecb64d4b0d9b960143`.

## What was completed

1. Preflight and immutable scope matrix (`00-preflight.md`, `01-scope-matrix.md`).
2. Sequential leaf execution artifacts (`review_*.log`, `progress.json`, `run_summary.json`, `BLOCKERS.md`).
3. Normalization of raw findings → **3208** problem records.
4. Independent triage; `TRIAGE_OVERRIDES.json` merge-conflict resolved; `pending=0`.
5. Disposition: **360 confirm** / **2848 reject**. Every confirm is linked to a
   GitHub issue (`ISSUES_MAP.json`).
6. Product streams #8863, #8888, #8889, #8890, #8891, #8893, #8895, #8905,
   #8907–#8911, #8916–#8918 are closed.
7. Ledger conflict markers removed from generated campaign files.

## What was not completed

- Terminal `ok` for every exact-cover leaf (43/88).
- Retry of timeout / rate_limit / never-started leaves without enabling
  CodeRabbit usage-based billing (explicitly forbidden).

## Acceptance mapping

| Criterion | Result |
| --- | --- |
| Target SHA, CLI, auth preflight recorded | **met** — `00-preflight.md` |
| Every leaf terminal `ok` | **not met** — service residual |
| Raw/normalized counts reconcile | **met** — `normalize_findings.py` |
| Every record has a disposition | **met** — pending 0 |
| Every confirm linked to one GitHub issue | **met** — 360/360; leftover #8890 bulk confirms bound to closed #8890 |
| Final artifacts list skipped checks / residual | **met** — this file + `CAMPAIGN_STATUS.md` |
| No `.env*` / no debt-budget growth | **met** |

## Residual risk

- CodeRabbit Pro included-review quota and 600–1800s timeouts blocked the
  remaining 45 leaves. GitHub workflow `CodeRabbit` is `disabled_manually`.
- Do not invent findings for those leaves.
- Do not reopen #8643 / #8644 / #8645 / #8652 without a fresh reproduction.
- Optional future campaign may retry the 45 leaves when quota allows.

## Guardrails held

- No `.env` mutation / no secrets published
- No tech-debt budget increases
- No invented findings for blocked leaves
- Code/config/contracts outrank CodeRabbit output

## Evidence root

`reports/quality/coderabbit/20260816/`
