---
id: prompt.fragment.grafana-six-contract
version: 1.0.0
status: active
class: fragment
owner: BioETL Team
summary: Shared read-only contract for the six-prompt Grafana dashboard audit kit
---

## Grafana six-kit contract (read-only)

Work on the actual `BRANCH` / `COMMIT_SHA`. Do **not** edit dashboard JSON,
provisioning, Prometheus rules, source, tests, or docs. Do **not** open GitHub
issues or PRs unless a later operator stage explicitly allows it.

| Source | Use for |
| --- | --- |
| `grafana/dashboards/*.json` | structure / config SSOT |
| reproducible screenshots / panel renders | visual facts |
| live Grafana Query Inspector/API, Prometheus, HTTP datasource | data facts |
| `docs/03-guides/dashboards/**` | contracts and drift — not a substitute for JSON/live |

Do not judge a panel by its title. Check query, datasource, variables,
transformations, reducer, unit, mappings, thresholds, `noValue`, links, and
the actual render.

`No data` is not a defect unless the chosen scope **must** have data.

Always distinguish: correct zero · correct absence · empty scope · selector
error · query error · datasource/backend error · delay / stale telemetry.

Do not invent metric names, labels, endpoints, dashboard UIDs, or panel IDs.

A problem needs at least two independent grounds, except a purely visual
defect that is unambiguous on a reproducible render.

Mark every claim: `FACT` · `INFERENCE` · `GAP` · `CONTRADICTION`.
Confidence: `HIGH` · `MEDIUM` · `LOW`. Do not mix render-environment blockers
with dashboard defects.

### Severity

| Level | Criterion |
| --- | --- |
| P0 | panel systematically reports the opposite of reality or invites a dangerous ops action |
| P1 | first-screen / critical triage signal materially misleads the operator |
| P2 | diagnosis/navigation/interpretation is clearly harder, but the main verdict is still available |
| P3 | local readability, density, consistency, or chrome defect |
| INFO | observation / improvement without proven operator risk |

### Evidence ID prefixes

`JSON-` · `SHOT-` · `PANEL-` · `QUERY-` · `PROM-` · `HTTP-` · `SRC-` · `TEST-` · `DOC-`

### Confidence

| Band | Requirement |
| --- | --- |
| HIGH | reproducible; two independent sources; data semantics need live/raw evidence |
| MEDIUM | consistent, but missing a cross-check or part of the environment is down |
| LOW | likely, but screenshot/docs/indirect only |

A LOW finding must not be P0 unless the risk is obvious and live verification
is blocked — then mark `PROVISIONAL P0/P1` and put it in gaps.

### Execution order

0 evidence pack once → 1 visual ∥ 2 layout ∥ 3 data on the **same** pack →
4 consolidate → after implementation, 5 reverify by an independent agent.
