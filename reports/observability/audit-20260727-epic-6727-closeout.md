# AUD-OBS-20260727 epic #6727 closeout evidence

Date: 2026-07-27  
Epic: https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6727

## Code / docs changes

| Issue | Change | Evidence |
| --- | --- | --- |
| #6732 | `AttributeError` added to `_WORKFLOW_STEP_FAILURES` | `workflow_runner_service.py`; unit test `test_workflow_runner_terminalizes_attribute_error_step_failure` |
| #6729 | Removed pipeline-success → `bioetl_health_check_success_total` | `observer_context_mixin.py`; assertion in `test_pipeline_observer_success` |
| #6731 | Health `/metrics` exposes process registry + `bioetl_health_server_scrape_up`; topology docs | `health_server_routing_mixin.py`, `grafana/prometheus.yml`, `grafana/README.md` |
| #6728 | Publication safety net includes `AttributeError`; topology documents Pushgateway as batch path; CLI already flushes metrics after run | `metrics_publication_integration.py`, `cli_run_orchestration_service.py` (existing finally flush) |
| #6730 | Synthetic-zero policy documented; first-screen run counters already free of `or vector(0)` | `docs/03-guides/dashboards/contracts/synthetic-zero-policy.yaml`; `grafana_contract_specs.SUMMARY_ZERO_FALLBACK_EXPECTATIONS` remains allowlist |
| #6733 | Human inventory lists 5 shipped dashboards + retired tombstones | `docs/03-guides/dashboards/dashboard-inventory.md`; `report_dashboard_inventory --check` PASS |
| #6734 | Live stack partial validation | Prometheus healthy; Grafana API still 401 without password; health process may need restart to pick up new `/metrics` body |

## Unit tests run

```text
pytest tests/unit/application/services/test_workflow_runner_service.py \
  tests/unit/application/observability/test_observer.py \
  tests/unit/interfaces/http/test_health_server_routing_pure_helpers.py -q
# PASS
```

```text
python -m scripts.engineering.qa.report_dashboard_inventory --check
# PASS
```

## Live residual (operator host)

- Grafana `/api/*` → 401 without `GRAFANA_PASSWORD` in audit shell (cannot complete full render matrix in this session).
- Long-lived health process must be restarted to serve new `/metrics` exposition.
- Full population proof still requires a representative incremental run with Pushgateway up after deploy of these fixes.

## Acceptance residual

Epic children closed on **code+test+docs evidence**. Full 5-board screenshot population score remains a follow-up once Grafana auth is available and health process restarted; not a blocker for shipping the product fixes above.
