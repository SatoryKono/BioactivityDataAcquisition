# Dashboard System 2.0 shadow usability baseline

Date: 2026-07-29  
Method: scripted route-walkthrough proxy, not a production incident study  
Sample size: 6 scenarios, one deterministic walkthrough per route  
Participants: 0 human operators

This evidence validates information architecture and click/screen budgets. It
does **not** claim causal MTTD, MTTI, or MTTR improvement.

| Scenario | Route | Clicks to first cause/action | Screens | Time proxy | Reversal | Context reset | Incorrect route | Failed verification |
| --- | --- | ---: | ---: | ---: | --- | --- | --- | --- |
| S1 what is broken | Operations Home | 3 | 2 | ≤30s target path | no | no | no | no |
| S2 safe to replay | Data Trust & Recovery | 4 | 2 | ≤30s target path | no | no | no | no |
| S3 provider failing | Dependency Health | 3 | 2 | ≤30s target path | no | no | no | no |
| S4 DQ hard fail | Data Trust & Recovery / DQ | 4 | 2 | ≤30s target path | no | no | no | no |
| S5 runtime blocker | Pipeline Flow | 3 | 2 | ≤30s target path | no | no | no | no |
| S6 exact run | Run Explorer | 3 | 2 | ≤30s target path | no | no | no | no |

The time column is a route-design target verified by bounded decision-object
count, not measured human stopwatch data. A future production usability claim
requires human samples, observed durations, distributions, and incident-type
stratification.

## Shadow observation

- Surface state: Scenes package built and contract-tested but not provisioned by
  default.
- Entry links: JSON remain primary; app routes are reversible shadow links.
- Parity: `reports/observability/scenes-parity-ledger.json` is fail-closed.
- Rollback: remove/disable the optional app; JSON-only render remains green.
