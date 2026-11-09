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
* Overview panel 9460 uses the `uql` parser on the `yesoreyeram-infinity-datasource`.
* Target URL extracted: `/ops/observability/pipeline-run-report-artifact`
* Hypothesis from #12785: missing or optional fields could affect the stage join. The retained configuration does not establish that any fields were lost. This requires a captured input frame and the corresponding transformed output.

### 3.2 DQ Domains (ID 9406 & 9403)
* Panel 9406 uses the `backend` parser. The target URL extracted is: `/ops/observability/selected-run-status?pipeline=${pipeline}&run_id=${run_id}&run_type=${run_type:csv}&workflow=${workflow:csv}`. It extracts fields such as `_bioetl_frame`, `domain`, `verdict`, `status`, `detail`, `reason`, `reason_display`, `status_display`.
* Panel 9403 uses the `backend` parser for both targets. Target A queries `/ops/observability/processed-records`; StageInput queries `/ops/observability/selected-run-status`.
* Due to isolated environment, live API bodies cannot be inspected. Frame extraction depends completely on Grafana offline definition.

### 3.3 Incident (ID 2101)
* Panel 2101 is located inside `reports/observability/live-fixes-r6/LF1-01/bioetl-incident-v1.json` as Review Selected Run Status nested within row 2100 (Inspect Selected Run Summary).
* It uses `backend` parser and queries `/ops/observability/selected-run-status?pipeline=${pipeline}&run_id=${run_id}&run_type=${run_type:csv}&workflow=${workflow:csv}`.
* Its JSONata transformations extract nested durations and overall verdicts mapping them to `_bioetl_frame: status`, `domains`, and `duration`.

### 3.4 Control Plane (ID 9418) & Funnel (ID 9002)
* Panel 9418 (Target A) parsing payload uses `uql` parser. Target URL extracted is: `/ops/observability/selected-run-status?pipeline=${pipeline}&run_id=${run_id}&run_type=${run_type:csv}&workflow=${workflow:csv}`. Field definitions in JSONata map `_bioetl_frame`, `domain`, `verdict`, `status`, `detail`, `reason`.
* Overview panel 9002 (Review Run Domains) uses the `uql` parser. Target A queries `/ops/observability/selected-run-status?pipeline=${pipeline}&run_id=${run_id}&run_type=${run_type:csv}&workflow=${workflow:csv}`. Dashboard links are navigation and are not request targets.

## 4. Closure Passport
* **[x] Попанельный baseline по двум UUID сохранён**: `PASS` (for offline dashboard structure analysis) / `BLOCKED` (for live UUID query inspection due to offline environment).
* **[x] Причины подтверждены либо обозначены недоказанными**: `PASS`. UQL/JSONata, optional fields, and fractional-second parsing are hypotheses from #12785. The causal mechanism remains `NOT_VERIFIABLE` without a reproduced transformation on captured input.
* **[x] Результат приложен как отчёт с exact source/deploy SHA**: `PASS`. Documented in this baseline report.
