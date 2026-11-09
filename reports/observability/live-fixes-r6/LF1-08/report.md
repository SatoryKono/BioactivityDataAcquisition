# LF1-08 Baseline Data Quality & Incident Frames Review

## 1. Overview and Scope
* **Target Issue**: [LF1-08] Зафиксировать baseline кадров стадий DQ и Incident (GitHub issue #12804)
* **Goal**: Baseline query inspector setup for Grafana Overviews regarding Data Quality (panels 9406, 9403) and Incident (panel 2101). Additionally verify overview 9002 / Control Plane 9418.
* **Environment Limitations**: The backend environment is known to be isolated from live observability clusters (as demonstrated in LF1-01 and LF1-05). All live API requests will fail (`NOT_VERIFIABLE` / `BLOCKED`). Verification targets offline dashboard configurations.

* **Retained dashboard snapshot source SHA:** `e54596f903e0b280e2b7e572a1c32ab831590b54`.
* **Deployment SHA:** `NOT_VERIFIABLE`. The LF1-01 identity receipt does not establish the running backend revision.

## 2. Methodology
Using offline dashboard exports from `reports/observability/live-fixes-r6/LF1-01/`:
- Parse and analyze Query parameters (endpoints, body, parser)
- Map symptoms from #12785

## 3. Results (Offline Dashboard Inspections)

### 3.1 Overview (ID 9460)
* Target A reads panel 9002 through the shared Dashboard datasource with `withTransforms: false`. It supplies `state`, `reason`, `records_in`, `records_out`, and `duration_seconds`.
* Target B uses the Infinity datasource with the `uql` parser and requests `/ops/observability/pipeline-run-report-artifact`.
* The `joinByField` transformation combines A and B by `stage_id` in `outerTabular` mode.
* Hypothesis from #12785: missing or optional fields could affect the stage join. The retained configuration does not establish that any fields were lost. This requires a captured input frame and the corresponding transformed output.

### 3.2 DQ Domains (ID 9406 & 9403)
* Panel 9406 uses the `backend` parser. The target URL extracted is: `/ops/observability/selected-run-status?pipeline=${pipeline}&run_id=${run_id}&run_type=${run_type:csv}&workflow=${workflow:csv}`. The panel selects `_bioetl_frame = status`, limits to one row and displays `execution_state`, `verdict`, `saved_trust` and `reason_display`.
* Panel 9403 uses the `backend` parser for both targets. Target A queries `/ops/observability/processed-records`; StageInput queries `/ops/observability/selected-run-status`. The outer join uses `parameter` and presents the input and output counts.
* Due to isolated environment, live API bodies cannot be inspected. Frame extraction depends completely on Grafana offline definition.

### 3.3 Incident (ID 2101)
* Panel 2101 is located inside `reports/observability/live-fixes-r6/LF1-01/bioetl-incident-v1.json` as Review Selected Run Status nested within row 2100 (Inspect Selected Run Summary).
* It uses `backend` parser and queries `/ops/observability/selected-run-status?pipeline=${pipeline}&run_id=${run_id}&run_type=${run_type:csv}&workflow=${workflow:csv}`.
* The panel selects `_bioetl_frame = status` from the JSONata output, limits to one row and displays `execution_state`, `verdict`, `saved_trust` and `reason_display`.

### 3.4 Control Plane (ID 9418) & Funnel (ID 9002)
* Panel 9418 (Target A) parsing payload uses `uql` parser. Target URL extracted is: `/ops/observability/selected-run-status?pipeline=${pipeline}&run_id=${run_id}&run_type=${run_type:csv}&workflow=${workflow:csv}`. JSONata emits `trust`, `replay_readiness` and `replay_checks` frames. The panel filters to `_bioetl_frame = trust`, converts `evidence_observed_at` to time and keeps `processing_status`, `trust_status`, `reasons_display`, `reasons_text`, `evidence_observed_at`, `reasons_count`, `evidence_freshness`, `trust_reasons_action` and `trust_action_note`. The final organize transform hides `reasons_display`, and the panel limits the result to one row.
* Overview panel 9002 (Review Run Domains) uses the `uql` parser. Target A queries `/ops/observability/selected-run-status?pipeline=${pipeline}&run_id=${run_id}&run_type=${run_type:csv}&workflow=${workflow:csv}`. Dashboard links are navigation and are not request targets.

## 4. Closure Passport
* **[x] Попанельный baseline по двум UUID сохранён**: `PASS` (for offline dashboard structure analysis) / `BLOCKED` (for live UUID query inspection due to offline environment).
* **[x] Причины подтверждены либо обозначены недоказанными**: `PASS`. UQL/JSONata, optional fields, and fractional-second parsing are hypotheses from #12785. The causal mechanism remains `NOT_VERIFIABLE` without a reproduced transformation on captured input.
* **[x] Офлайн-отчёт приложен**: `PASS`. The retained dashboard snapshot is identified by its source SHA above.
* **[ ] Идентичность развёртывания подтверждена**: `NOT_VERIFIABLE`. The deployed revision and live frames were not captured.
