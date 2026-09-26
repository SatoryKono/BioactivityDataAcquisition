# Pipeline selector workflow catalog latency

Historical Grafana request: 2026-09-24 10:09:50.406 UTC, downstream 504 at
10:10:24.158 UTC, elapsed 33.705132354 seconds. The selector uses a 20-second
bounded forensic deadline in the currently running container.

Retained Prometheus histogram deltas show one successful workflow_manifest
list_all observation of 43.243 seconds, first visible at 10:10:45 UTC.
This is temporal association, not request-level correlation. A host/storage
stall remains possible; the original 504 has not been deterministically reproduced.

The running store reads 122 workflow JSON files sequentially. The patch uses
four workers, matching the existing run-manifest read strategy. It preserves
fresh reads, validation, deterministic order and propagation of invalid JSON;
no timeout, semaphore, query, dashboard or empty-state contract is changed.

Read-only comparison inside the existing container (same 122 real manifests):

| Trial | Sequential seconds | Four workers seconds | Equal parsed results |
| --- | ---: | ---: | --- |
| 1 | 0.520844 | 0.130226 | true |
| 2 | 0.537198 | 0.205445 | true |
| 3 | 0.535566 | 0.153295 | true |

This warm-read comparison proves reduced cumulative per-file overhead, not
resolution of the historical timeout or cold-host performance. The probe did
not replace the running application or start monitoring compose.

Acceptance remains pending deployment from a clean source, exact runtime
identity, repeated browser reloads and failure-path evidence. #10981 and
#10982 must remain open until those conditions are met. #10961's historical
manifest and independent data/UI gaps are unaffected.

Validation: 820 control-plane/HTTP tests passed, 3 skipped (Windows symlink
privilege); 11 dashboard no-scroll tests passed; targeted Ruff passed.
An older routing-helper test was updated to assert exact_run_only and fallback
through RunIdOptionPolicy, matching the already merged API refactor.
Runtime AI files and dashboard JSON are unchanged; mirror synchronization is
not applicable. Memory pre-task ran read-only with missing RAG/timeline artifacts.
