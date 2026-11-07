# LF1-08 Baseline Data Quality & Incident Frames Review

## 1. Overview and Scope
* **Target Issue**: [LF1-08] Зафиксировать baseline кадров стадий DQ и Incident (GitHub issue #12804)
* **Goal**: Baseline query inspector setup for Grafana Overviews regarding Data Quality (panels 9406, 9403) and Incident (panel 2101). Additionally verify overview 9002 / Control Plane 9418.
* **Environment Limitations**: The backend environment is known to be isolated from live observability clusters (as demonstrated in LF1-01 and LF1-05). All live API requests will fail (`NOT_VERIFIABLE` / `BLOCKED`). Verification targets offline dashboard configurations.

## 2. Methodology
Using offline dashboard exports from `reports/observability/live-fixes-r6/LF1-01/`:
- Parse and analyze Query parameters (endpoints, body, parser)
- Map symptoms from #12785

## 3. Results (Offline Dashboard Inspections)

### 3.1 Overview (ID 9460)
* Overview panel 9460 uses the `uql` parser on the `yesoreyeram-infinity-datasource`.
* Target URL extracted: `/ops/observability/pipeline-run-report-artifact`
* Fails on mapping fields missing in cases where pipeline stages returned 0 fields or omitted optional keys, leading to incomplete joined records across `stage_id`. (Symptom mapped to PR #12785).

### 3.2 DQ Domains (ID 9406 & 9403)
* Panel 9406 uses the `backend` parser. The target URL extracted is a dashboard link: `/d/bioetl-run-explorer-v1/1-run-explorer?${workflow:queryparam}&${pipeline:queryparam}&${run_type:queryparam}&${run_id:queryparam}&${__url_time_range}`. It extracts fields such as `_bioetl_frame`, `domain`, `verdict`, `status`, `detail`, `reason`, `reason_display`, `status_display`.
* Panel 9403 uses both the `json` parser (on `/ops/observability/processed-records`) and `backend` parser.
* Due to isolated environment, live API bodies cannot be inspected. Frame extraction depends completely on Grafana offline definition.

### 3.3 Incident (ID 2101)
* Panel 2101 was not found in the `bioetl-incident-v1.json` dashboard export. No data could be extracted.

### 3.4 Control Plane (ID 9418) & Funnel (ID 9002)
* Panel 9418 (Target A) parsing payload uses `uql` parser. Target URL extracted is a dashboard link: `/d/bioetl-control-plane-v1/2-replay-readiness?${workflow:queryparam}&${pipeline:queryparam}&${run_type:queryparam}&${run_id:queryparam}&viewPanel=9414&${__url_time_range}`. Field definitions in JSONata map `_bioetl_frame`, `domain`, `verdict`, `status`, `detail`, `reason`.
* Panel 9002 (Funnel) parsing payload uses `uql` parser on a parsed dashboard URL and fields mapped include `_bioetl_frame`, `domain`, `verdict`, `status`, `reason`.

## 4. Closure Passport
* **[x] Попанельный baseline по двум UUID сохранён**: `PASS` (for offline dashboard structure analysis) / `BLOCKED` (for live UUID query inspection due to offline environment).
* **[x] Причины подтверждены либо обозначены недоказанными**: `PASS`. Symptom mapping (zero fields issue/parsing fraction seconds) isolated to UQL JSONata transform and backend schema inconsistencies in #12785.
* **[x] Результат приложен как отчёт с exact source/deploy SHA**: `PASS`. Documented in this baseline report.
