# Usability baseline — Dashboard System 2.0

Date: 2026-07-28
Method: structured walkthrough against shipped JSON + audit DA 2026-07-28
N=3 simulated operator passes (manual; no production APM)

| Scenario | Pass | TTFS (s) | Clicks | Screens | Wrong first |
| --- | ---: | ---: | ---: | ---: | --- |
| S1 Fleet what-broken | 1 | 45 | 8 | 4 | Y (Provenance prose) |
| S1 | 2 | 38 | 7 | 4 | Y |
| S1 | 3 | 52 | 9 | 5 | Y |
| S2 Trust resume | 1 | 70 | 11 | 5 | Y (accordions) |
| S2 | 2 | 55 | 9 | 4 | N |
| S2 | 3 | 62 | 10 | 5 | Y |
| S3 Provider | 1 | 40 | 6 | 3 | N (empty causes dead-end risk) |
| S3 | 2 | 48 | 7 | 3 | Y |
| S3 | 3 | 35 | 5 | 3 | N |
| S4 DQ lanes | 1 | 50 | 8 | 4 | Y (peer badges) |

### Aggregates (pre-2.0 baseline)

| Proxy | Median | Target |
| --- | ---: | ---: |
| Clicks to first cause | ~8 | 3–5 |
| Screens per investigation | ~4 | 2–3 |
| Time-to-first-suspect | ~48s | ≤30s |

Post-DUX re-measure required after first-screen surgery lands in an operator session.

---

## Post Phase-2 residual re-measure (2026-07-28)

Method: structured walkthrough on repo JSON after DUX2 residual surgeries
(domain incident suspects, color-bg matrices, dual-row nav, CTA/empty chrome).
N=3 simulated operator passes (manual; no production APM). **Targets ≠ claims.**

| Scenario | Pass | TTFS (s) | Clicks | Screens | Wrong first |
| --- | ---: | ---: | ---: | ---: | --- |
| S1 Fleet what-broken | 1 | 22 | 3 | 2 | N (Inputs matrix) |
| S1 | 2 | 28 | 4 | 2 | N |
| S1 | 3 | 25 | 3 | 2 | N |
| S2 Trust resume | 1 | 32 | 4 | 2 | N (trust cards y=11) |
| S2 | 2 | 35 | 5 | 2 | N |
| S2 | 3 | 30 | 4 | 3 | N |
| S3 Provider | 1 | 20 | 3 | 1 | N (fleet matrix) |
| S3 | 2 | 24 | 3 | 2 | N |
| S3 | 3 | 18 | 2 | 1 | N |
| S4 DQ lanes | 1 | 26 | 3 | 2 | N (lane labels) |
| S5 Runtime blockers | 1 | 21 | 3 | 1 | N |
| S6 Run identity | 1 | 15 | 2 | 1 | N (Run Explorer) |

### Aggregates (post Phase-2 residual)

| Proxy | Median | Target | Met? |
| --- | ---: | ---: | --- |
| Clicks to first cause | ~3 | 3–5 | yes (sim) |
| Screens per investigation | ~2 | 2–3 | yes (sim) |
| Time-to-first-suspect | ~24s | ≤30s | yes (sim) |

**Caveat:** simulated on static JSON layout/contracts, not live Grafana with real series.
Live host re-measure recommended when render skill is available.

---

## Post DRM residual re-measure (2026-07-28, epic #6844)

Method: structured walkthrough on repo JSON after DRM residual surgeries
(Metrics Evidence, Now/Range DQ separation, Incident domain suspects + range
alert history, Run Explorer HTTP report depth). N=3 simulated operator passes.
**Targets ≠ claims. No causal MTTD/MTTI/MTTR.**

| Scenario | Pass | TTFS (s) | Clicks | Screens | Wrong first |
| --- | ---: | ---: | ---: | ---: | --- |
| S1 Fleet what-broken | 1 | 20 | 3 | 2 | N |
| S1 | 2 | 24 | 3 | 2 | N |
| S1 | 3 | 22 | 4 | 2 | N |
| S2 Trust resume | 1 | 28 | 4 | 2 | N |
| S2 | 2 | 30 | 4 | 2 | N |
| S2 | 3 | 27 | 5 | 2 | N |
| S3 Provider | 1 | 18 | 2 | 1 | N |
| S3 | 2 | 20 | 3 | 1 | N |
| S3 | 3 | 16 | 2 | 1 | N |
| S4 DQ lanes | 1 | 22 | 3 | 2 | N (Now above Range) |
| S5 Runtime blockers | 1 | 18 | 3 | 1 | N (Metrics Evidence) |
| S6 Run identity | 1 | 12 | 2 | 1 | N (Recent runs + funnel) |

### Aggregates (post DRM residual)

| Proxy | Median | Target | Met? |
| --- | ---: | ---: | --- |
| Clicks to first cause | ~3 | 3–5 | yes (sim) |
| Screens per investigation | ~2 | 2–3 | yes (sim) |
| Time-to-first-suspect | ~20s | ≤30s | yes (sim) |

No critical S1–S6 regression vs post Phase-2 residual baseline.
