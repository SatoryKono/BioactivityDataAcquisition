______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-07-28'

______________________________________________________________________

# Metrics readiness matrix (first-screen)

**Rule:** do not invent series. Names below already exist in
`grafana/prometheus-rules/bioetl_observability.yml` or HTTP control-plane APIs.

`Ready? yes` means the **recording/HTTP contract exists**. Live scrape samples
for `bioetl_pipeline_runs_total` require health-server rehydrate from durable
run reports (OBS-FILL-01 / #8930). HELP/TYPE without samples is a trust gap,
not a ready first-screen.

| Panel / need | Metric / source | Ready? | Blocker |
| --- | --- | --- | --- |
| Overview Status | `bioetl_l0_status` | yes | live empty until trust-anchor samples exist |
| Overview First Action route | `bioetl_l0_next_action_route` | yes | — |
| Overview Inputs matrix | `bioetl_l0_input_status_selected` | yes | — |
| Runtime Status | `bioetl_runtime_current_status_trusted` | yes | — |
| Runtime Blockers | `bioetl_runtime_current_blocker_reason` | yes | empty when healthy is VALID EMPTY |
| Metrics Evidence | scrape/rule trust series on board | yes | operator wording only |
| Provider severity matrix | `bioetl_provider_current_status` | yes | empty without provider traffic |
| Provider top causes | `bioetl_provider_current_cause` | yes (rules) | needs failure events to populate |
| DQ Status | `bioetl_dq_current_status` | yes | — |
| DQ reasons | `bioetl_dq_current_reason` | yes | — |
| Trust replay safety | control-plane recording + HTTP | yes | INCOMPLETE when evidence gap |
| Incident suspects | reuses provider/runtime/dq current rules | yes | thin board |
| Run identity / records | `/ops/control-plane/*` HTTP | yes | needs health server |

## Instrumentation backlog (not invented here)

None required for Dashboard 2.0 first-screen ship. DUX-09 hardens cause projection
using existing raw provider health metrics → `bioetl_provider_current_cause` records.
