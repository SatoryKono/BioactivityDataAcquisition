## Baseline Failure & Null Values in Artifacts
When executing the full suite of ARTIFACT_REFRESH tools, such as `uv run python -m scripts.engineering.ci.update_test_telemetry_baseline`, the tool generated output `source_tree_sha256=e0ba3e4faf9470eb1edfebc2d9ab641180f55ce79777b5f971f6746c28988af4`. However, `reports/test-telemetry/coverage-summary.json` and `configs/quality/test_telemetry_baseline.yaml` had large chunks of telemetry details completely removed or replaced with `null`.

The exact missing inputs were the `.xml` and coverage files for each individual test lane (e.g. `reports/pr12231-local-coverage-8a4286d/junit/smoke.xml`, `reports/pr12231-local-coverage-8a4286d/junit/contract-confidence.xml`, etc.). Without running all these specific isolated lanes to generate their outputs, the `update_test_telemetry_baseline` producer output empty telemetry data. A full test execution could not complete because of the 400-second execution environment limit.

## Pending Verification Gap
The current implemented tests check that the internal collector stores `email` as `[REDACTED]`. However, there is no test verifying that the *constructed outbound request* leaving `httpx` (i.e. the real outgoing URL in the transport layer) is actually unredacted and behaves identically. This is an explicit gap compared to the acceptance criteria which requires proof of: "Real construction of the outbound request/query and the behavior of passing the attribution and key do not change."

## Handoff & Blocker
No commit or publication has been performed as the publication permission has been explicitly denied (`STOP`). All changes are halted.
