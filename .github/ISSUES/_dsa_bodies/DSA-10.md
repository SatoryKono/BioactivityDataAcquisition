## Parent

_TBD_ (DSA-00)

## Problem

Deep audit recommends advanced visualizations (status matrix, state timeline, waterfall, curated node graph, conditional Sankey). DS2-12 / DSS-08 tracked this as **not_planned** without data contracts. This issue **re-tracks** the gate — not a license to invent metrics or topology.

## Tracking only until gates

- [ ] Metric readiness matrix row per viz
- [ ] Frame contracts (no continuous series on state-timeline without time field)
- [ ] Node graph: curated ≤30 nodes; directed dependencies only
- [ ] Sankey/accounting flow only with reconcileable counts
- [ ] Explicit **reject**: chord, sunburst, decorative treemap, flame graph without profiling question

## Supersedes / related

- #6913 DS2-12 (closed not_planned)
- #6923 DSS-08 (closed not_planned)

## Acceptance (to start implementation PR)

- [ ] Written data contract + ADR note if topology/Sankey
- [ ] No Prom `run_id`
- [ ] Tech-debt budgets not increased
- [ ] JSON SOT remains fallback

## Priority

P3 tracking — do not implement unsolicited.
