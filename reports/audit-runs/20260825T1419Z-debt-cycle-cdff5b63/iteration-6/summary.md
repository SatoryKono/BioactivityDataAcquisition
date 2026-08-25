# Iteration 6 — Residual re-check

No new PROVEN P0/P1 in SCOPE beyond #9646/#9647.

Already tracked / intentional:

- Constructor waiver 1: `QuarantineEntry` ADR-051 (`configs/quality/constructor_waivers.yaml`).
- Import-cycle allowlist 30, review_by 2026-10-28 (#6958).
- `application_services_control_plane` at_budget fan-in 2/2 — #9618.
- `entrypoints.py` wrapper_contract_drift (missing `load_pipeline_config`/`start_metrics_server`; unexpected `register`/`resolve`/`registered_ports`) — #9643.
- Scorecard retirement KPI 4 vs inventory 8 — REJECTED_POLICY raise `max_count`.
