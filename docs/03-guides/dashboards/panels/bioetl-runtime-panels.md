# Pipeline Diagnostics — panel guide

Pipeline Diagnostics examines saved evidence for one selected Run ID. It is
not a current fleet monitor. The dashboard time range is preserved in navigation;
it does not turn a historical run into current telemetry. Use Incident Workspace
for fleet and time-range charts and Replay Readiness for replay decisions.

## Navigation and scope — 1000, 9400

The navigation bus preserves the selected run and time range. The scope banner
explains that this page uses saved pipeline evidence. Select a Pipeline and Run ID
before interpreting the tables. A failed request is not an empty successful run.

## Review Selected Run Status — 9998

The saved report summary separates Result (processing state), Status (evaluation
verdict), and Evidence (completeness). Rules, when supplied by the response,
identify the evaluation rules. SUCCESS does not authorize replay. Missing required
checks remain INCOMPLETE. Use Run Explorer to inspect the selected run.

## Inspect Pipeline Identity — 9402

The Ops HTTP identity-table endpoint provides the run UUID, manifest, provider,
contract and execution context. Pagination exposes additional parameters. Inspect
value exposes complete identifiers. Aggregate Pipeline scope does not guess a run.

## Inspect Processed Records — 9403

The Ops HTTP processed-records endpoint provides Bronze, Silver and Gold accounting
rows. Counts and percentages are neutral quantities, not verdicts. Zero means a
recorded zero; absent evidence is not zero. Cell links open the saved report for
the selected pipeline and run, so the operator can check the source counts.

## Inspect Saved Run Evidence — 9450

This group ships collapsed. Expand it to inspect total duration, stages, domain
verdicts and the saved report identity. These panels remain scoped to the same UUID.

## Review Total Run Duration — 9463

The saved report's completion timestamp minus its start timestamp gives the total
run duration, as in Run Explorer. This is not the sum of measured stage timings.
Missing timestamps must not produce a fabricated duration.

## Inspect Selected Run Stages — 9460

Saved report stages contain input/output counts, stage state, reason and source.
At most 12 rows are shown. Not recorded means an individual stage timing was not
saved. A recorded zero remains zero. Open report leads to the complete raw report;
UNFINISHED means no terminal event was recorded, not proof of current execution.

## Inspect Selected Run Domains — 9451

One row per saved domain shows Status, Reason and Action. Known reason codes have
plain English labels; unfamiliar codes remain visible for diagnosis. For example,
Processing completed explains execution_success. Standalone pipeline; no workflow
applies explains the Workflow N/A state. These labels do not recalculate verdicts.
Open report provides the original evidence and unmodified reason codes.

## Inspect Selected Run Identity — 9452

One row provides Pipeline, Run ID, Completed, Rules, Revision and Evidence.
Completed uses the dashboard timezone and YYYY-MM-DD HH:mm format. Revision is a
report identifier, not a current runtime health check. Evidence describes report
completeness, not replay readiness.

## Missing evidence and errors

SELECT RUN requests an explicit selection. VALID EMPTY applies only to a successful
empty response. QUERY ERROR means the request failed; inspect panel status and the
Ops HTTP service before interpreting data. UNKNOWN and INCOMPLETE preserve missing
required evidence. N/A is reserved for an explicitly inapplicable check. The raw
report is authoritative; display mappings never manufacture success.
