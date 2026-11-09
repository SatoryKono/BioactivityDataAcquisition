# LF1-28 Live Fixes Receipt Matrix

## Environment & Context
- **Pass ID:** LF1-28
- **Source SHA (exact):** 3f2808e6eeeb6570fdac3e125e7be16d6cc9d2f9
- **Deploy SHA:** NOT_VERIFIABLE (compose stack unavailable)
- **Environment:** compose (NOT production)
- **Time (UTC):** 2026-11-09T12:35:00Z
- **Status:** BLOCKED / NOT_VERIFIABLE
- **Reason:** `docker compose` execution is not permitted in the environment; backend is `blocked_backend_unavailable`.

## Separation of Verification States
- **Local Tests:** N/A
- **CI:** N/A
- **Deployment:** NOT_VERIFIABLE
- **Live:** NOT_VERIFIABLE

## L-01…L-09 Mapping
All live verification scenarios for L-01 through L-09 are `NOT_VERIFIABLE` because the live compose stack is unavailable. No actual evidence links exist.
- L-01: NOT_VERIFIABLE (blocked_backend_unavailable)
- L-02: NOT_VERIFIABLE (blocked_backend_unavailable)
- L-03: NOT_VERIFIABLE (blocked_backend_unavailable)
- L-04: NOT_VERIFIABLE (blocked_backend_unavailable)
- L-05: NOT_VERIFIABLE (blocked_backend_unavailable)
- L-06: NOT_VERIFIABLE (blocked_backend_unavailable)
- L-07: NOT_VERIFIABLE (blocked_backend_unavailable)
- L-08: NOT_VERIFIABLE (blocked_backend_unavailable)
- L-09: NOT_VERIFIABLE (blocked_backend_unavailable)

## Reopened F-findings Mapping
All live F-findings are `NOT_VERIFIABLE` due to the backend being unavailable.
- F-findings: NOT_VERIFIABLE (blocked_backend_unavailable)

## UUID and Timestamp Coverages (B/C Pipeline)
While local unit tests verify the UUID resolution and timestamp handling (as shown in LF1-13), live coverage verification for two saved UUIDs, manifest/stages, UUID-branch timestamp, missing UUID, and historical UUID without manifest is `NOT_VERIFIABLE` due to the unavailability of the live stack.

## Required Matrix from Receipts

Поля ниже заполнены из **сохранённых** receipt-артефактов. Отсутствие compose
не блокирует чтение уже записанных UID/панелей/UUID/сценариев; live-повтор
остаётся `NOT_VERIFIABLE` / `NOT_RUN`, где так помечено в источнике.

- **Source:** [LF1-22/machine_readable_receipt.json](../LF1-22/machine_readable_receipt.json)
  - UID: `bioetl-overview-v2`
  - Panel ID: `9604`, `9603`, `9481`, `9482`
  - UUID: N/A
  - Expected: сохранённые HTTP/сценарии из receipt
  - Actual (по сценариям, не сводный N/A):
    - `valid_empty`: http=200, reason=`no_runs_in_scope`, verdict=`НЕТ ЗАПУСКОВ`
    - `not_found`: http=200, reason=`run_not_found`, verdict=`UNKNOWN`
    - `missing_pipeline`: http=400
    - `unknown_path`: http=404
    - `closed_port`: http=null, error=`connection_refused`
    - `saved_success`: status=`NOT_RUN`, index_state=`tree_missing`
  - Live/Grafana/Prometheus: `NOT_VERIFIABLE` (deploy_sha=`NOT_VERIFIABLE`)
  - Evidence: [machine_readable_receipt.json](../LF1-22/machine_readable_receipt.json)
- **Source:** [LF1-04/machine-readable-receipt.json](../LF1-04/machine-readable-receipt.json)
  - UID: `bioetl-incident-v1`
  - Dashboard path (reference only): `grafana/dashboards/bioetl-incident-v1.json`
  - Panel ID: `9701`
  - UUID: N/A
  - Expected: static GLOBAL scope contract (`$workflow`/`$pipeline`/`$run_type`; `$run_id` ignored)
  - Actual (static): `PASS` **только** `status_scope=static_analysis`
  - Live/runtime: `BLOCKED` (`runtime_validation.status=BLOCKED`; planned
    `empty_run_id`/`original_uuid`/`different_uuid`/`timestamp_variation`,
    `scenarios_executed=[]`) — отдельно от static PASS
  - Evidence: [machine-readable-receipt.json](../LF1-04/machine-readable-receipt.json)
- **Source:** [LF1-13/machine_readable_receipt.json](../LF1-13/machine_readable_receipt.json)
  - UID: N/A
  - Panel ID: N/A
  - UUID: N/A
  - Expected: live UUID/timestamp coverage
  - Actual: `NOT_VERIFIABLE` (live stack unavailable)
  - Evidence: [machine_readable_receipt.json](../LF1-13/machine_readable_receipt.json)
- **Source:** [LF1-31/machine_readable_receipt.json](../LF1-31/machine_readable_receipt.json)
  - UID: `bioetl-control-plane-v1`
  - Panel ID: `9422`, `9423`, `9408`, `9418`, `9414`, `9415`, `9416`, `9413`, `9406`
  - UUID:
    - negative zero: `00000000-0000-0000-0000-000000000000` (http=200,
      `resolved_via=selected_run_id_not_found`)
    - historical manifest run_id: `8ed593ce-3b75-56e0-a337-192953048582`
      (`exact_replay_ready=false`, verdict=`rebuild_only`)
  - Expected: positive object checks + live grafana/prometheus
  - Actual: `positive_object_checks=NOT_RUN`; grafana/prometheus=`NOT_VERIFIABLE`;
    deploy_sha=`NOT_VERIFIABLE`
  - Evidence: [machine_readable_receipt.json](../LF1-31/machine_readable_receipt.json)
- **Source:** [LF1-06/machine_readable_receipt.json](../LF1-06/machine_readable_receipt.json)
  - UID: N/A
  - Panel ID: N/A
  - UUID: N/A
  - Expected: live verification
  - Actual: `NOT_VERIFIABLE`
  - Evidence: [machine_readable_receipt.json](../LF1-06/machine_readable_receipt.json)
- **Source:** [LF1-25/machine_readable_receipt.json](../LF1-25/machine_readable_receipt.json)
  - UID: N/A
  - Panel ID: N/A
  - UUID: `new_uuid=NOT_RUN`
  - Expected: selector options cache freshness / stale isolation
  - Actual: isolated unit
    `tests/unit/interfaces/http/test_selector_options_cache.py::test_stale_is_immediate_under_saturation_and_expires`
    =`passed`; grafana/prometheus=`NOT_VERIFIABLE`; deploy_sha=`NOT_VERIFIABLE`
  - Evidence: [machine_readable_receipt.json](../LF1-25/machine_readable_receipt.json)
- **Source:** [LF1-26/machine_readable_receipt.json](../LF1-26/machine_readable_receipt.json)
  - UID: `bioetl-incident-v1`
  - Panel ID: `238`, `256`, `241`, `240`, `908`, `8806`, `209`, `210`, `131`,
    `107`, `8805`, `108`, `135`, `8807`, `112`
  - UUID: N/A
  - Expected: live promql / grafana
  - Actual: local sample counts recorded
    (`bioetl_control_plane_reads_total=4`); promql/grafana/prometheus=
    `NOT_VERIFIABLE`; deploy_sha=`NOT_VERIFIABLE`
  - Evidence: [machine_readable_receipt.json](../LF1-26/machine_readable_receipt.json)
- **Source:** [LF1-24/machine_readable_receipt.json](../LF1-24/machine_readable_receipt.json)
  - UID: `bioetl-incident-v1`
  - Panel ID: workflow_zero_display `9996`, `9997`
  - UUID: N/A
  - Expected: panels `9481`/`9604` mapped on UID; null→OK mapping
  - Actual: `panels_9481_9604_on_uid=false`; `null_mapped_to_ok=false`;
    grafana/prometheus/rendered_color=`NOT_VERIFIABLE`; deploy_sha=`NOT_VERIFIABLE`
  - Evidence: [machine_readable_receipt.json](../LF1-24/machine_readable_receipt.json)
- **Source:** [LF1-28/machine-readable-receipt.json](./machine-readable-receipt.json)
  - UID: N/A
  - Panel ID: N/A
  - UUID: N/A
  - Expected: live-fixes matrix closure
  - Actual: `NOT_VERIFIABLE` (`reason=blocked_backend_unavailable`)
  - Evidence: [machine-readable-receipt.json](./machine-readable-receipt.json)
- **Source:** [LF1-30/machine_readable_receipt.json](../LF1-30/machine_readable_receipt.json)
  - UID: `bioetl-run-explorer-v1`
  - Panel ID (data-backed): `3010`
  - UUID: `ee3ce1ed-9487-572f-ae24-c98c6f6e3a37`,
    `d7cdb35b-e37a-5767-b30e-aa8dfb60d775`
  - Expected: positive matrix + live grafana/prometheus
  - Actual: `positive_matrix=NOT_RUN`; `index_state=tree_missing`;
    grafana/prometheus=`NOT_VERIFIABLE`; deploy_sha=`NOT_VERIFIABLE`
  - Evidence: [machine_readable_receipt.json](../LF1-30/machine_readable_receipt.json)
- **Source:** [LF1-11/contract-evidence.json](../LF1-11/contract-evidence.json)
  - UID: N/A
  - Panel ID: N/A
  - UUID / manifest_id: `6da492a7-cc24-5adf-88f0-b9c2ad0e8df2`
  - Expected: contract comparison compatible
  - Actual: `compatible` (`contract_comparison_reason=manifest_contract_comparison_compatible`)
  - Evidence: [contract-evidence.json](../LF1-11/contract-evidence.json)
- **Source:** [LF1-21/live-panel-audit.json](../LF1-21/live-panel-audit.json)
  - UID (from panel_specs): includes `bioetl-control-plane-v1` (and related audit specs)
  - Panel ID: from audit `panel_specs` (example required: `9418`, `9422`, …)
  - UUID: N/A (`config.run_id="-"`)
  - Expected: live panel audit against compose stack
  - Actual: artifact saved; live stack for LF1-28 re-run remains unavailable
  - Evidence: [live-panel-audit.json](../LF1-21/live-panel-audit.json)
