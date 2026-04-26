# Synthesis: governance-signals

## Executive Summary

- The enforceable `C901` baseline is currently clean, so function-complexity governance is not adding background noise to near-term refactor work. (`EV-governance-signals-c901-enforceable-baseline-is-green`)
- File-size governance and raw hotspot inventory are currently different views of the system: the ratchet is green because the `file_size_limits` exemption registry is empty, while the source tree still carries a broad large-file tail. (`EV-governance-signals-file-size-ratchet-tracks-exemptions-not-raw-hotspots`, `EV-governance-signals-file-size-ratchet-tightened-from-six-to-zero`)
- The scorecard does show intentional hotspot prioritization, but it is selective and centered on `src/bioetl/application/core/`, not on the full repo-wide hotspot set. (`EV-governance-signals-hotspot-budgets-prioritize-application-core`)
- Duplication pressure is measurable right now in both `composition` and `application`, especially in `application`, but that pressure is not part of an enforceable trend gate today. (`EV-governance-signals-composition-duplication-snapshot-has-28-r0801-occurrences`, `EV-governance-signals-application-duplication-snapshot-has-88-r0801-occurrences`, `EV-governance-signals-duplication-governance-excludes-composition-and-application`)

## Key Insights

### Insight 1: Complexity governance is stable enough to serve as a clean baseline

**Observation:** The current `check-c901` run reports `0` current violations, `0` new violations, and `7` resolved baseline violations.
**Implication:** We can interpret any newly introduced `C901` failures during upcoming architecture work as fresh regressions rather than inherited baseline noise. This lowers diagnostic cost for the next refactor wave.
**Confidence:** 0.97
**Evidence:** `EV-governance-signals-c901-enforceable-baseline-is-green`

### Insight 2: Green file-size governance does not mean the large-file problem is gone

**Observation:** The enforceable file-size ratchet is tied to the `file_size_limits` exemption registry, which is currently empty, while the raw hotspot inventory still shows `82` files above `10 KB` and `10` above `350 LOC`.
**Implication:** Current green-state reporting can be misread if people assume it describes the whole source-tree size profile. Operationally, this means the repo has successfully ratcheted exemptions down, but has not yet converted the broad hotspot tail into a directly enforced budget.
**Confidence:** 0.95
**Evidence:** `EV-governance-signals-file-size-ratchet-tracks-exemptions-not-raw-hotspots`, `EV-governance-signals-file-size-ratchet-tightened-from-six-to-zero`

### Insight 3: Size governance has become stricter, but only through narrow controls

**Observation:** The scorecard moved from a historical `file_size_limits` baseline of `6` to an enforceable baseline of `0`, and registry sync is explicitly anchored to the enforceable `baseline`. At the same time, the only named hotspot budget discovered is `core_orchestration` under `src/bioetl/application/core/`.
**Implication:** Governance has tightened in principle, but that tightening currently acts through selective registry control and one named hotspot program rather than a repo-wide ratchet on all large files. This is a disciplined but partial form of size governance.
**Confidence:** 0.92
**Evidence:** `EV-governance-signals-file-size-ratchet-tightened-from-six-to-zero`, `EV-governance-signals-hotspot-budgets-prioritize-application-core`

### Insight 4: Duplication in `application` and `composition` is visible enough to prioritize, but not yet governable as a trend

**Observation:** Ad hoc scans found `31` `R0801` occurrences in `composition` and `88` in `application`, but the default duplication workflow only checks `src/bioetl/infrastructure/adapters`.
**Implication:** We can say there is current duplication pressure, especially in `application`, but we cannot yet claim a controlled improvement or regression trend for those layers. Until there is a ratcheted baseline, duplication in these areas remains visible debt rather than enforceable debt.
**Confidence:** 0.93
**Evidence:** `EV-governance-signals-composition-duplication-snapshot-has-28-r0801-occurrences`, `EV-governance-signals-application-duplication-snapshot-has-88-r0801-occurrences`, `EV-governance-signals-duplication-governance-excludes-composition-and-application`

## Contradictions and Resolutions

### Tension 1: Green size governance vs large hotspot tail

**Evidence in tension**

- `EV-governance-signals-file-size-ratchet-tracks-exemptions-not-raw-hotspots`
- `EV-governance-signals-file-size-ratchet-tightened-from-six-to-zero`

**Resolution:** Resolved conceptually. These are not contradictory measurements. The ratchet describes enforceable exemption-state; the hotspot inventory describes raw structural tail. Both can be true at the same time.

### Tension 2: Duplication is measurable, but not governed

**Evidence in tension**

- `EV-governance-signals-composition-duplication-snapshot-has-28-r0801-occurrences`
- `EV-governance-signals-application-duplication-snapshot-has-88-r0801-occurrences`
- `EV-governance-signals-duplication-governance-excludes-composition-and-application`

**Resolution:** Resolved as a governance gap, not a data conflict. The scans tell us current duplication pressure exists; the Makefile and discovered workflow tell us that this pressure is not yet part of the normal ratcheted governance loop.

## Gaps and Uncertainties

- The duplication evidence is still a point-in-time snapshot. We do not yet have a historical baseline for `composition` or `application`, so trend language should be used carefully.
- `R0801` is noisy around facades, `__init__` export barrels, and compatibility seams. A future governance step would need a normalization rule or scoped target set before making this blocking.
- The size-hotspot evidence remains file-level. It does not yet connect large modules to churn, ownership concentration, review pain, or bug density.
- The named hotspot budget currently points to `application/core`, but we do not yet have evidence here for whether that choice still matches the largest day-to-day maintenance burden compared with other large-file clusters.

## Recommended Decisions

- **DEC-governance-duplication-scope:** Decide whether duplication governance should remain limited to `infrastructure/adapters` or expand to `composition` and `application` with a non-blocking baseline first.
- **DEC-governance-size-metrics-semantics:** Decide whether green file-size reporting should continue to mean “no exemptions” or whether a separate repo-wide hotspot tail metric should become an explicit first-class governance signal.
- **DEC-governance-hotspot-priorities:** Decide whether `application/core` should remain the only named hotspot budget or whether additional named hotspot programs are needed for high-pressure seams in `application` and `composition`.
- **DEC-governance-duplication-normalization:** Decide which duplication classes are intentionally tolerated facades/compat shims before setting any ratchet for `R0801` outside adapters.

## Top Insights

1. `C901` is currently a trustworthy clean baseline for future refactor work. (`EV-governance-signals-c901-enforceable-baseline-is-green`)
1. Zero file-size exemptions is not the same thing as zero large-file debt in the source tree. (`EV-governance-signals-file-size-ratchet-tracks-exemptions-not-raw-hotspots`, `EV-governance-signals-file-size-ratchet-tightened-from-six-to-zero`)
1. Duplication in `application` and `composition` is already measurable, but still sits outside the repo’s default enforceable governance trend. (`EV-governance-signals-composition-duplication-snapshot-has-28-r0801-occurrences`, `EV-governance-signals-application-duplication-snapshot-has-88-r0801-occurrences`, `EV-governance-signals-duplication-governance-excludes-composition-and-application`)
