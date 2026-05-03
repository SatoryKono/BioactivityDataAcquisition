# Grafana Navigation Contract

Канонический контракт навигации для shipped dashboard UIDs в `grafana/dashboards/*.json`.

## Общие правила

- Каждый dashboard (кроме overview-hub) **MUST** иметь top-level ссылку `Back to Overview` на UID `bioetl-overview-v2`.
- Cross-dashboard handoff передаёт только target-scoped `var-*` параметры и **MUST** включать `${__url_time_range}` во всех dashboard URL (`/d/...`).
- `includeVars=true` и другие универсальные handoff-паттерны запрещены; используем только явные `var-*` и time-range по единому стандарту:
  - dashboard links (`/d/<uid>/<slug>?...`): `${__url_time_range}`
  - Explore links (`/explore` и `/a/grafana-*-explore-app/...`): `from=${__from}&to=${__to}`
- Explore handoff для Loki/Tempo ведёт только через drilldown-приложения:
  - Logs: `/a/grafana-lokiexplore-app/explore?...`
  - Traces: `/a/grafana-exploretraces-app/?...`


## Примеры URL (нормализованный формат)

- Dashboard: `/d/bioetl-runtime/bioetl-runtime?var-pipeline=$pipeline&var-run_type=$run_type&${__url_time_range}`
- Dashboard: `/d/bioetl-dq-v2/bioetl-dq-v2?var-pipeline=$pipeline&var-run_type=$run_type&var-stage=$stage&${__url_time_range}`
- Dashboard: `/d/bioetl-overview-v2/bioetl-overview-v2?var-pipeline=All&var-run_type=All&${__url_time_range}`

## Обязательные блоки по UID

| Dashboard UID | Обязательные top-level links | Обязательные `var-*` в cross-links |
|---|---|---|
| `bioetl-overview-v2` | `2. Runtime`, `Control Plane v1`, `3. Provider Health`, `4. Data Quality`, `6. Workflow Overview`, `Explore Logs (Loki, tracing profile)`, `Explore Traces (Tempo, tracing profile)` | Runtime/ControlPlane/DQ: `var-pipeline`, `var-run_type`; Provider/Workflow: без `var-*` |
| `bioetl-runtime` | `Back to Overview`, `Control Plane v1`, `3. Provider Health`, `4. Data Quality`, `Explore Logs (Loki, tracing profile)`, `Explore Traces (Tempo, tracing profile)` | Overview/ControlPlane: `var-pipeline`, `var-run_type`; DQ: `var-pipeline`, `var-run_type`, `var-stage`; Provider: без `var-*` |
| `bioetl-control-plane-v1` | `Back to Overview`, `2. Runtime`, `4. Data Quality`, `Explore Logs (Loki, tracing profile)`, `Explore Traces (Tempo, tracing profile)` | Overview/Runtime/DQ: `var-pipeline`, `var-run_type` |
| `bioetl-provider-health-v2` | `Back to Overview`, `2. Runtime`, `Explore Logs (Loki, tracing profile)`, `Explore Traces (Tempo, tracing profile)` | cross-dashboard `var-*` не передаются |
| `bioetl-dq-v2` | `Back to Overview`, `Control Plane v1`, `5. Silver Reject Explorer`, `Explore Logs (Loki, tracing profile)`, `Explore Traces (Tempo, tracing profile)` | Overview/ControlPlane/Explorer: `var-pipeline`, `var-run_type` |
| `bioetl-silver-reject-explorer` | `Back to Overview`, `Back to Data Quality`, `Explore Logs (Loki, tracing profile)`, `Explore Traces (Tempo, tracing profile)` | Overview/DQ: `var-pipeline`, `var-run_type` |
| `bioetl-workflow-overview` | `Back to Overview`, `2. Runtime`, `Control Plane v1` | cross-dashboard `var-*` не передаются |

## Запрещённые handoff-паттерны

- `includeVars=true`
- legacy Explore payload route: `/explore?left=`
- перенос Explorer-only forensic scope (`var-run_id`, `var-payload_hash`) в non-explorer dashboards
