# Selected Run status

The endpoint `GET /ops/observability/selected-run-status?pipeline=...&run_id=...`
assesses the saved evidence of exactly one run. `run_type` and `workflow`, when
concrete, must match that run. `from` and `to` never enter the assessment.

New assessments use `selected-run-v2`; saved `selected-run-v1` assessments remain verifiable. The persisted envelope is
`selected_run_snapshot_v1`; its SHA-256 revision binds the rules, assessment and
complete input evidence. These hashes detect accidental corruption; they are
not signatures or an authorization mechanism.

| Domain | Saved source | Meaning and missing evidence |
| --- | --- | --- |
| Runtime | Report identity and execution result | Success is OK; failed is ERROR; shutdown/cancelled is WARN. This does not establish evidence completeness. |
| Control Plane | Completion-time manifest, lineage and retention checks | The existing aggregate Trust validators run at completion. A saved manifest alone is INCOMPLETE. Archive or retention gaps remain visible. |
| Workflow | Final workflow result and exact child step | Standalone pipelines are N/A. A child awaiting workflow finalization is INCOMPLETE. Workflow finalization publishes a new child revision. |
| Data Quality | Postrun threshold evaluation, including measured zero | Passed is OK, warning is WARN, failed is ERROR. A check that never executed is INCOMPLETE. |
| Provider | This execution's preflight observation and observation time | Current health is never substituted. Cached Bronze is N/A for remote-provider observation. Missing observation is INCOMPLETE. |
| Data Validation | This execution's Gold schema validation | An executed successful check is OK; a failed check is ERROR. Explicit skip_gold is N/A under v2 rules; otherwise missing validation is INCOMPLETE, not inferred from processing success. |

For applicable domains, overall precedence is ERROR, INCOMPLETE, UNKNOWN, WARN,
OK. N/A is excluded; an entirely inapplicable dry run remains N/A. An active
execution keeps RUNNING; recent ledger activity and its age are separate live
diagnostics, not proof that an idle process is alive. A terminal ledger without
a final report means incomplete finalization.

The response separates `execution_state`, `checks_verdict`,
`evidence_completeness`, `evidence_availability`, and `replay_readiness_now`.
Replay readiness is NOT EVALUATED by this endpoint. CURRENT panels continue
using their existing 15-minute freshness checks. A historical OK is never a
current replay authorization.

The `summary`, `domains` and `rows` arrays carry the same selected identity and
revision. No selection is SELECT RUN; no persisted run is UNKNOWN with
`run_not_found`; identity mismatch or corruption is ERROR; missing committed
revision is INCOMPLETE; read/timeout failures are QUERY ERROR. Legacy reports
are explicitly `legacy_no_snapshot`, and their missing observations remain
unknown or incomplete. No migration rewrites legacy history.

Finalization writes a content-addressed revision into `status-revisions` first,
then atomically publishes `pipeline-run-report.json` as the commit record.
Retrying identical evidence keeps the same revision. Late workflow or other
evidence creates another revision and retains the earlier one. A crash before
publication leaves the previous complete report readable; an orphan revision
does not become the selected status. Every read verifies the current report,
its embedded snapshot, and the committed revision file without a verdict cache.

The existing local archive command accepts `--report-root` to include reports
and revisions alongside manifest-bound evidence. The restore copy is under
`restored/run-reports`. Source and restored bytes are rechecked; missing or
corrupt files cannot be hidden behind an archived OK. Reports outside the
selected pipeline/run directory are never included.

Grafana keeps CURRENT telemetry separately labelled. The Overview domain table
and selected-run summary use the same saved-run endpoint; all seven dashboards
include an expandable saved-evidence view. Navigation preserves the selected
run and chart range. Chart coverage and the Set range to run action remain in
Run Explorer; partial coverage never modifies the saved-run verdict.


## Contract migration and rollback

New writers publish `pipeline_run_report_v2` and `selected-run-v2` assessments.
Readers retain v1 report and rule support; old revisions are never rewritten.
Explicit `skip_gold` is N/A under v2 rules. See
[ADR-061](../02-architecture/decisions/ADR-061-persisted-selected-run-assessment.md)
for deployment order, archive versioning and rollback without deleting evidence.

The v2 JSON Schema references unchanged field contracts in the immutable v1
schema through its `bioetl://` identifier. Package both schema files and register
both `$id` values with the validator's local schema registry; validation requires
no network access. The writer integration tests exercise this offline registry.


### Persisted selector options

Control-plane filter options include identity-checked persisted pipeline reports,
including historical runs absent from the current manifest catalog. Workflow,
pipeline, run type, status and exact run filters remain conjunctive; unrelated
reports never supply a selected scope. Corrupt or mismatched report identities
produce an error instead of fabricated options. Existing manifest options are
retained and report values are deduplicated.

Grafana HTTP selector queries request `response_shape=options` and declare string
`text`/`value` columns with Infinity's `simple` parser and `items` root. The backend
parser drops all fields for an empty array even with declared columns, causing
`at least one field expected for variable`. The simple parser preserves the empty
column schema. Empty options remain empty; transport errors remain query errors.
