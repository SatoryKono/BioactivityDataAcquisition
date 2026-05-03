______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-03'

______________________________________________________________________

# Variables Guide (Grafana Dashboards)

Дата сверки: **2026-05-03**  
Источник истины: `grafana/dashboards/*.json`

## Unified Variable Contract

### Scope groups

- **Core scope**: `pipeline`, `run_type`, `stage` (где есть stage-level панели).
- **Provider scope**: `provider`, `adapter` (только provider health dashboards).
- **Forensic-only**: `run_id`, `payload_hash` (только `bioetl-silver-reject-explorer`).

### Dashboard → scope contract

| Dashboard UID | Contract |
| --- | --- |
| `bioetl-overview-v2` | Core: `pipeline`, `run_type` |
| `bioetl-control-plane-v1` | Core: `pipeline`, `run_type` |
| `bioetl-runtime` | Core: `pipeline`, `run_type`, `stage` |
| `bioetl-dq-v2` | Core: `pipeline`, `run_type`, `stage` |
| `bioetl-provider-health-v2` | Provider: `provider`, `adapter` |
| `bioetl-silver-reject-explorer` | Core: `pipeline`, `run_type` + explorer fields `reason_code`, `field` + Forensic-only `run_id`, `payload_hash` |
| `bioetl-workflow-overview` | Workflow-local: `workflow`, `status` |

## Variable meanings and fallback semantics

| Variable | Scope | Meaning | Fallback when source dashboard does not pass it |
| --- | --- | --- | --- |
| `pipeline` | Core | Pipeline selection baseline | Target dashboard uses default **All pipelines** |
| `run_type` | Core | Run mode within selected pipeline | Target dashboard uses **All run types** |
| `stage` | Core | Stage breakdown filter (`bronze/silver/gold`) | Target uses **All stages** |
| `provider` | Provider | Provider selection for provider health panels | Target uses **All providers** |
| `adapter` | Provider | Adapter selection for provider health panels | Target uses **All adapters** |
| `run_id` | Forensic-only | Exact run narrowing in reject explorer | No run_id filter (all runs in selected pipeline/run_type scope) |
| `payload_hash` | Forensic-only | Exact record lookup in reject explorer textbox | Empty textbox disables payload filter |

## Cross-dashboard handoff rules (explicit)

1. Передавать только `var-*`, которые входят в target contract.
1. `includeVars=true` не используется для dashboard-to-dashboard ссылок.
1. **Core → Core**: передавать `pipeline`, `run_type`; `stage` передаётся только если target поддерживает `stage`.
1. **Core ↔ Provider**: provider dashboards не получают core variables; fallback через default provider/adapter selection.
1. **Any → Forensic (Reject Explorer)**: допускаются только `pipeline`, `run_type`; forensic filters (`run_id`, `payload_hash`) всегда вводятся оператором вручную в explorer.
1. **Forensic → Core**: передавать обратно только `pipeline`, `run_type`; не передавать `run_id`, `payload_hash`, `reason_code`, `field`.
1. **Workflow dashboards** (`workflow`, `status`) изолированы; при переходах в runtime/control-plane действует fallback на defaults target dashboards.


## Navigation time-range policy

- Для всех `links[].url` с dashboard route (`/d/...`) используем единый time handoff: `${__url_time_range}`.
- Для всех `links[].url` с Explore route (`/explore`, `/a/grafana-lokiexplore-app/explore`, `/a/grafana-exploretraces-app/`) используем `from=${__from}&to=${__to}`.
- Смешанные/legacy варианты (`from=$__from`, отсутствие time-range, `includeVars=true`) не допускаются.

## Test coverage expectations

- Links contract: `tests/integration/test_grafana_dashboard_links.py`
- Variable contract checks: `tests/integration/test_grafana_config.py` + `tests/integration/_grafana_test_support.py`
- Forensic isolation checks: `run_id`/`payload_hash` запрещены вне reject explorer.
