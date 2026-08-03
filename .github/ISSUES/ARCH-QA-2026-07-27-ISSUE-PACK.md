# Architecture Quality Follow-up Issue Pack — 2026-07-27

**Audit basis:** Independent architecture quality review (live tree after merge
`fix/ci-main-gates-green` into `main`, commit context `17670ed68d`).

**Independent integral score:** **8.81** (committed scorecard artifact: **9.11**).

**Prior residual wave:** TD-R-00..TD-R-09 (#6676–#6685) — closed; several findings
still observable on live tree and require a fresh owner wave.

**Policy:** debt budgets may only stay flat or decrease (`AGENTS.md`).

## Snapshot (evidence)

| Metric | Value | Source |
|---|---|---|
| Independent integral | 8.81 | live audit 2026-07-27 |
| Scorecard integral (artifact) | 9.11 | `reports/quality/architecture-quality-scorecard.json` |
| Layer violations (live map) | **1** | `docs/02-architecture/generated/module-dependency-map.json` |
| Debt gates | 43 pass / **2 fail** | `reports/quality/debt-governance-gates.json` |
| Hotspot budget_warnings | 0 | `reports/quality/hotspot-family-baseline.json` |
| Hotspot at-budget families | core 5/5; factories 2/2 + fan-in 3/3 | same |
| Constructor waivers | 5 | `configs/quality/constructor_waivers.yaml` |
| Partial modules | 816 | `reports/quality/module-coverage-inventory.json` |
| Uncovered / unmeasured | 0 / 0 | same |

## Issue codes (this wave) — published

| Code | Pri | Issue | URL |
|---|---|---:|---|
| ARCH-QA-00 | meta | #6740 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6740 |
| ARCH-QA-01 | P0 | #6744 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6744 |
| ARCH-QA-02 | P0 | #6743 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6743 |
| ARCH-QA-03 | P1 | #6741 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6741 |
| ARCH-QA-04 | P1 | #6742 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6742 |
| ARCH-QA-05 | P2 | #6748 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6748 |
| ARCH-QA-06 | P2 | #6745 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6745 |
| ARCH-QA-07 | P2 | #6746 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6746 |
| ARCH-QA-08 | P3 | #6747 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6747 |

Publish record: `reports/quality/architecture-quality-2026-07-27-issue-publish.json`

## Constraints (all issues)

1. No debt budget growth.
2. Domain remains I/O-free (except explicit temporary allowlists being removed).
3. DI only in Composition Root.
4. Prefer ports + composition inject over layer-rule exceptions.
5. Do not weaken architecture tests to close issues.

## Related closed issues (do not re-open blindly)

- #6676 TD-R-00 epic (closed)
- #6677 re-pin audit (closed) — ARCH-QA-02 is a **new live fail** after later merges
- #6679 constructor 10→5 (closed) — ARCH-QA-04 is the **next shrink tranche**
- #6681 hotspot burn-down (closed) — ARCH-QA-03 re-opens residual at-cap evidence
