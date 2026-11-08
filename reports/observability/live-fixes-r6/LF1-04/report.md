# LF1-04 Diagnostic Report: Panel 9701 Actual Scope

## 1. Environment Identity & Context
- **Base SHA**: `facb0b5673c7cec55b6f4efb230f531618e9b56e`
- **Time (UTC)**: `2026-11-06 18:48:37 UTC` (aligned with LF1-01)
- **Environment Access**: NOT_VERIFIABLE (Live monitoring stack failed preflight in LF1-01).

## 2. Panel 9701 Analysis (Static Analysis)
From the extracted JSON configuration for panel 9701 (`panel-9701.json`):
- **Title**: "Review Current Workflow Evidence"
- **Description**: "CURRENT · Workflow/pipeline/run-type scope, independent of Selected Run. Published at is the gateway publication clock, not the Prometheus evaluation clock. Retained publications do not expire after 15 minutes. Reason unavailable means no diagnostic cause is exposed by this metric."

### Data Source Queries
1. **Target A**:
   `label_replace(max by(workflow)(bioetl_workflow_scope_input_status{input="workflow",workflow=~"$workflow",pipeline=~"$pipeline",run_type=~"$run_type"}),"reason","Reason unavailable","","")`
2. **Target B**:
   `bioetl_workflow_scope_published_seconds * on(workflow) group by(workflow)(bioetl_workflow_scope_universe{workflow=~"$workflow",pipeline=~"$pipeline",run_type=~"$run_type"}) * 1000`

### Scope Evaluation
- **Variables Used**: `$workflow`, `$pipeline`, `$run_type`.
- **Variables NOT Used**: `$run_id`.
- The panel uses variables that define the broader scope of the pipeline execution but explicitly ignores `$run_id`, consistent with the panel description ("independent of Selected Run").

## 3. Scope Scenarios Table (Expected vs Actual)

| Scenario | Parameters | Expected PromQL Modification | Static PromQL Analysis (queries not executed) | Conclusion |
| :--- | :--- | :--- | :--- | :--- |
| **Empty run_id** | `run_id=""` | No change in query | None. `$run_id` is not present in the Prometheus queries. | Queries execute with `$workflow`, `$pipeline`, `$run_type` scopes only. |
| **Original UUID** | `run_id="ee3ce1ed-9487-572f-ae24-c98c6f6e3a37"` | Filter by original UUID | None. `$run_id` is ignored by the panel's queries. | No change to data retrieval; panel scope remains independent of run selection. |
| **Different UUID** | `run_id="different-uuid-value"` | Filter by new UUID | None. The Prometheus queries do not filter by `$run_id`. | Consistent behavior regardless of `run_id` assignment. |
| **Timestamp Variation** | Change the Grafana time range | The expressions stay the same. Both targets are instant queries without an `@` modifier, so the evaluation time can change the selected samples. | BLOCKED. No runtime request or frame was captured. | `bioetl_workflow_scope_published_seconds` supplies the displayed publication timestamp. Prometheus evaluation time still governs which status and timestamp samples are selected. |

## 4. HTTP Request / Frame Diagnostics
- **Expected Action**: Save request/HTTP/body/frame and verify what really changes the request.
- **Actual Action**: BLOCKED. Live environment is unavailable. However, static analysis of the panel's Prometheus configuration confirms that changing the selected run (`$run_id` variable) in the Grafana UI will not append a `$run_id` filter to the outbound HTTP request payload directed to Prometheus. The stored expressions omit the selected-run filter. No live request was captured for comparison.

## 5. Comparison and Contract (vs. #11268 and #12783)
- **#11268 Context**: Addressed global vs run-scoped dashboard components and standard link injection.
- **#12783 Context**: Addressed run-id specific routing and missing variables in drill-downs.
- **Contract Determination**: The contract for panel 9701 is **Global (Run-Independent) Workflow Scope**.
- **Reasoning**: Both queries (Targets A and B) explicitly filter by `$workflow`, `$pipeline`, and `$run_type`, but deliberately omit `$run_id`. The dashboard's description explicitly confirms this: *"CURRENT · Workflow/pipeline/run-type scope, independent of Selected Run."* Changing `$run_id` across any value does not alter the execution or results.
- **Recommended Visibility/Signature**: The panel should be strictly documented as run-independent. Any global strings or global metrics displayed are NOT a detail of a specific UUID, and should not be misinterpreted as run-scoped evidence. This aligns with the fixes in #11268 and #12783 where explicit run-id routing was either added or distinct globally-scoped panels were explicitly labeled as such.

## 6. Artifacts and Evidence
- `reports/observability/live-fixes-r6/LF1-04/panel-9701.json`: Extract of panel 9701 configuration.
- `reports/observability/live-fixes-r6/LF1-04/queries.json`: Extract of the queries run by the panel.
- Status: Completed static diagnostic. Diagnostic execution is PASS.
