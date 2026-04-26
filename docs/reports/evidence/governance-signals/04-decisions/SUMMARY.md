# Decisions Complete: governance-signals

**Decisions Made:** 4
**Статус:** 4 accepted, 0 provisional
**Risks Identified:** 5

## Решения Summary

| ID                                                               | Decision                                                                                                   | Status     | Evidence Count |
| ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- | ---------- | -------------: |
| `DEC-governance-c901-zero-new-debt-baseline`                     | Keep `C901` as zero-new-debt blocking baseline                                                             | `accepted` |              2 |
| `DEC-governance-duplication-expand-report-only-baseline`         | Expand duplication governance to `composition` and `application` in report-only mode first                 | `accepted` |              3 |
| `DEC-governance-file-size-report-dual-track`                     | Keep zero-exemption ratchet and add separate raw hotspot tail reporting                                    | `accepted` |              3 |
| `DEC-governance-expand-named-hotspot-programs-after-calibration` | Keep current `application/core` hotspot program and run one calibration wave for additional named hotspots | `accepted` |              4 |

## Риски Created

| ID                                           | Risk                                                                | Severity | Linked Decision                                                  |
| -------------------------------------------- | ------------------------------------------------------------------- | -------- | ---------------------------------------------------------------- |
| `RISK-governance-c901-refactor-friction`     | Strict zero-new-debt baseline can slow large refactors              | `medium` | `DEC-governance-c901-zero-new-debt-baseline`                     |
| `RISK-governance-duplication-noise-overload` | New duplication reports may be noisy and reduce trust in the signal | `medium` | `DEC-governance-duplication-expand-report-only-baseline`         |
| `RISK-governance-duplication-check-runtime`  | Expanded duplication scans may increase check time                  | `low`    | `DEC-governance-duplication-expand-report-only-baseline`         |
| `RISK-governance-metric-semantics-confusion` | Readers may confuse exemption debt with raw hotspot inventory       | `medium` | `DEC-governance-file-size-report-dual-track`                     |
| `RISK-governance-misprioritized-hotspots`    | New hotspot programs may target visible but low-leverage seams      | `medium` | `DEC-governance-expand-named-hotspot-programs-after-calibration` |

## Quality Gate Status

- Decision gate: pass, all 4 decisions cite at least 2 evidence IDs
- Decision gate: pass, all 4 decisions list alternatives and document wins and loses
- Risk gate: pass, all 5 risks link to a creating decision and include severity, likelihood, and mitigations

## Next Step

These decisions are now accepted and can be used as the active governance roadmap baseline for follow-up implementation and review work.
