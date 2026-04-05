# DEC-HOTSPOT Proposed Decision Draft

Date: 2026-03-21
Status: Proposed
Scope: `dependency-hotspots`

This draft converts the hotspot synthesis into a concrete decision package. It does not mark any option as accepted yet; it makes the next prioritization step explicit.

Note: the current hotspot snapshot has since changed to 82 files above 10 KB and 10 files above 350 LOC, with the repeat overlap tail centered on `src/bioetl/interfaces/cli/commands` rather than `src/bioetl/infrastructure/adapters`. Treat the wave ordering below as historical draft context, not a live baseline.

## Decision Package Summary

Recommended package:

1. Use the overlap set (`>10 KB` and `>350 LOC`) as the first refactoring-wave shortlist.
1. Treat size-only hotspots as phase-two backlog items rather than ignoring them.
1. Start the first decomposition wave in `src/bioetl/infrastructure/adapters`.
1. Use a two-track prioritization model: dense-file hotspots and dependency-pressure seams stay visible as separate signals.

Taken together, these decisions preserve the strongest parts of the current architecture discipline while making the maintainability program operational.

## DEC-HOTSPOT-001

**Decision**
Choose the first refactoring-wave boundary.

**Recommended option**
Start with the overlap set (`>10 KB` and `>350 LOC`) as the highest-density shortlist, then allow seam-pressure exceptions only where the dependency map shows concentrated architectural pressure.

**Alternatives considered**

- Start with dependency-pressure seams first, even when files are below hotspot thresholds.
- Start with the full `>10 KB` set immediately.

**Why this option**

- The overlap set is small enough to be operational (`17` files) and already captures the densest large modules.
- The full `>10 KB` set (`95` files) is too broad for the first execution wave.
- The dependency map still matters, but current evidence does not yet provide per-file fan-in/fan-out strong enough to replace the overlap set as the initial shortlist.

**Evidence**

- `EV-dependency-hotspots-17-files-exceed-350-loc`
- `EV-dependency-hotspots-loc-tail-is-contained-in-size-tail`
- `EV-dependency-hotspots-cross-layer-pressure-centers-on-composite-factories-cli`

**Wins**

- Gives the program a bounded first wave.
- Focuses on the densest maintainability surface first.
- Leaves room to escalate architecturally sensitive seams such as CLI/service boundaries.

**Loses**

- Some high-pressure but sub-threshold files move to later waves.
- The overlap set alone does not explain package coupling.
- The shortlist still spans multiple layers and cannot be treated as one single batch edit.

**Implications**

- The first hotspot backlog should be overlap-first, not full-inventory-first.
- Dependency-pressure seams should be used as escalation signals, not as the only priority model.

**Primary risks**

- `RISK-hotspot-wave-scatter`
- `RISK-hotspot-pressure-underweighting`

## DEC-HOTSPOT-002

**Decision**
Decide whether size-only hotspots are first-class backlog items.

**Recommended option**
Treat `>10 KB` files below `350 LOC` as phase-two hotspots, not as ignorable noise.

**Alternatives considered**

- Ignore size-only hotspots and focus only on `>350 LOC`.
- Merge size-only files into the first wave alongside the overlap set.

**Why this option**

- The largest current file is below the LOC cutoff.
- Size-only hotspots include dense schemas, core runners, composition configs, and pipeline modules that still contribute to maintenance drag.
- Pulling the whole size-only tail into the first wave would make the program too large.

**Evidence**

- `EV-dependency-hotspots-95-files-exceed-10kb`
- `EV-dependency-hotspots-largest-size-files-extend-beyond-loc-tail`
- `EV-dependency-hotspots-loc-tail-is-contained-in-size-tail`

**Wins**

- Preserves visibility of dense modules missed by LOC-only screening.
- Keeps first-wave scope bounded.
- Creates a clear second-wave inventory rather than an undefined “later maybe.”

**Loses**

- Requires maintaining two hotspot inventories at once.
- Some size-only files may remain untouched for longer.
- The phase boundary introduces judgment calls for near-threshold files.

**Implications**

- Backlog tracking must distinguish overlap hotspots from size-only hotspots.
- Reviews should not dismiss a file as “fine” only because it stays below the LOC threshold.

**Primary risks**

- `RISK-hotspot-size-only-neglect`
- `RISK-hotspot-threshold-gaming`

## DEC-HOTSPOT-003

**Decision**
Choose the first package decomposition target.

**Recommended option**
Prioritize `src/bioetl/infrastructure/adapters` first.

**Alternatives considered**

- Prioritize CLI/application pressure seams first because they are closer to user-facing orchestration.
- Start with storage/schema/config hotspots before adapters.

**Why this option**

- `src/bioetl/infrastructure/adapters` contains `7` of the `17` overlap hotspots.
- It is the single most concentrated package in the densest hotspot tail.
- This area also contains several mixin-heavy modules where cohesion risk is already visible from filenames and hotspot concentration.

**Evidence**

- `EV-dependency-hotspots-infrastructure-adapters-dominates-overlap-tail`
- `EV-dependency-hotspots-17-files-exceed-350-loc`
- `EV-dependency-hotspots-95-files-exceed-10kb`

**Wins**

- Attacks the most concentrated hotspot cluster first.
- Creates a clear package-scoped first wave.
- Likely reduces the largest share of overlap-hotspot debt with one package family.

**Loses**

- CLI and application pressure seams remain active until the next wave.
- Adapters can be behaviorally risky because they sit on external-provider logic.
- Package concentration does not automatically imply easiest decomposition order.

**Implications**

- The first execution wave should be package-oriented, not file-random.
- Adapter refactors need strong regression verification because they sit on provider behavior.

**Primary risks**

- `RISK-hotspot-adapter-regression`
- `RISK-hotspot-package-monoculture`

## DEC-HOTSPOT-004

**Decision**
Define how dependency pressure and file-size pressure should be merged into one prioritization model.

**Recommended option**
Use two parallel prioritization tracks: dense-file hotspots for execution order, dependency-pressure seams as escalation and tie-break rules.

**Alternatives considered**

- Collapse both signals into one numeric score.
- Ignore dependency pressure and run a file-size-only program.

**Why this option**

- Current evidence is strong enough for package/file hotspot prioritization, but not yet rich enough for precise per-file graph scoring.
- Dependency pressure clearly matters, especially around composite/composition/CLI seams.
- A forced single score would create false precision from incomplete graph attribution.

**Evidence**

- `EV-dependency-hotspots-module-map-zero-layer-violations`
- `EV-dependency-hotspots-cross-layer-pressure-centers-on-composite-factories-cli`
- `EV-dependency-hotspots-95-files-exceed-10kb`
- `EV-dependency-hotspots-17-files-exceed-350-loc`

**Wins**

- Preserves visibility of both structural and file-level pressure.
- Avoids fake precision from under-specified scoring.
- Makes it easier to justify seam-based exceptions to raw hotspot order.

**Loses**

- Requires more human judgment in prioritization.
- Produces a backlog model that is less mechanically simple than one score.
- Can drift if reviewers do not apply the escalation rule consistently.

**Implications**

- Backlog entries should carry both hotspot density and dependency-pressure notes.
- A later iteration can still add file-level graph metrics if the team wants a combined score.

**Primary risks**

- `RISK-hotspot-priority-inconsistency`
- `RISK-hotspot-false-precision-return`

## Recommended Adoption Order

1. Accept `DEC-HOTSPOT-001` and `DEC-HOTSPOT-004` together so the prioritization model is explicit.
1. Accept `DEC-HOTSPOT-003` next to define the first package execution wave.
1. Accept `DEC-HOTSPOT-002` so the phase-two inventory is not silently dropped.

## Implementation Consequences If Accepted

1. Build the first execution wave around `src/bioetl/infrastructure/adapters` overlap hotspots.
1. Keep a separate phase-two ledger for size-only hotspots such as `silver_publications.py`, `runner.py`, and `composition/factories/pipeline/configs.py`.
1. Annotate backlog items with dependency-pressure context, especially where CLI/composite seams are involved.
1. Keep hotspot refactors wave-based and package-aware instead of treating the 17 overlap files as one undifferentiated queue.
