# Tech-Debt Residual Issue Pack — 2026-07-27

**Audit basis:** Principal architecture tech-debt audit (local evidence, 2026-07-27)  
**Prior closed wave:** #6618–#6628 (TD-01..TD-10)  
**Policy:** debt budgets may only stay flat or decrease (Agents.md)

## Snapshot (evidence)

| Metric | Value | Source |
|---|---|---|
| Scorecard integral | 9.11 | `reports/quality/architecture-quality-scorecard.json` |
| Debt gates | 45 pass / 0 fail | `reports/quality/debt-governance-gates.json` |
| Exemptions | 0 | `configs/quality/architecture_metric_exemptions.yaml` |
| Transition/sunset/expired compat | 0/0/0 | scorecard + `debt_scorecard.yaml` |
| Partial modules | 816 | `module-coverage-inventory.json` |
| Constructor waivers | 10 (post TD-07) | `constructor_waivers.yaml` |
| Closeout inventory | 75 (~60 fold_into_generic) | `architecture_closeout_inventory.yaml` |
| Public entrypoints / export facades | 12 / 4 | compatibility census |
| Scripts zero-ref supporting | 21/21 | debt gates |
| Registry pin vs HEAD | `d0f60b1045` pin vs local `104a32026e` | registry + git |

## Issue codes (this wave) — published

| Code | Pri | Issue | URL |
|---|---|---:|---|
| TD-R-00 | meta | #6676 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6676 |
| TD-R-01 | P0 | #6677 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6677 |
| TD-R-02 | P1 | #6678 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6678 |
| TD-R-03 | P1 | #6679 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6679 |
| TD-R-04 | P1 | #6680 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6680 |
| TD-R-05 | P2 | #6681 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6681 |
| TD-R-06 | P2 | #6682 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6682 |
| TD-R-07 | P2 | #6683 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6683 |
| TD-R-08 | P3 | #6684 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6684 |
| TD-R-09 | P3 | #6685 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6685 |

Publish record: `reports/quality/tech-debt-residual-2026-07-27-issue-publish.json`

## Constraints (all issues)

1. No debt budget growth (exemptions, transition_compat, uncovered, etc.).
2. Domain remains I/O-free; DI only in Composition Root.
3. Permanent public CLI/composition seams are not dead code.
4. Prefer ratchet-down after evidence; never weaken gates to close issues.
