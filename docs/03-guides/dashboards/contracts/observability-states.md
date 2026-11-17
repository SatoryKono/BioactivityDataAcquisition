# Incident Workspace: observability states

This contract applies to Incident Workspace v2 and legacy Isolated 100000.
LA-04 (#12938) uses the same cause-verification terms; LA-05 (#12939) uses
the same missing-signal and empty-observation terms. Neither severity nor
telemetry presence proves the cause of an incident.

| State | Meaning | Signal source / evidence | Operator action |
| --- | --- | --- | --- |
| OK | Observed health inputs satisfy their healthy criteria in the stated scope. | Mapped current status gauges, with required inputs present. | Continue monitoring; inspect coverage before trusting an empty incident table. |
| WARN | Observed inputs meet a warning threshold. | Mapped current status gauges or a documented panel warning threshold. | Inspect the indicated domain and threshold in the same scope. |
| CRIT | Observed inputs meet a critical threshold. Severity describes the panel's subject: a telemetry CRIT is a visibility problem. | Mapped current status gauges or a documented critical threshold. | Triage domain evidence; if in Observability Signals, restore visibility before concluding product failure. |
| FIRING | An alert rule currently evaluates as firing; causality is not established. | Prometheus ALERTS with alertstate=firing. | Open rule/domain evidence; verify the cause independently (LA-04). |
| UNKNOWN | Required evidence cannot establish a verdict. It is not a measured zero. | Null/absent status gauge, unknown enum, unavailable source or failed query. | Check query errors, source availability, selectors and required inputs. |
| NO OBSERVATIONS | No matching events in the stated scope/window, with producer availability, observed scope and declared event families verified. | Evidence-gated lazy-event query; status gauges do not qualify merely because they are absent. | Confirm scope/window and witnesses; if witnesses are missing, investigate missing telemetry (LA-05). |
| TELEMETRY MISSING | Expected measurement or evidence is absent; product health is unresolved. | Missing required series, scrape or recording-rule coverage; telemetry coverage panels. | Check producer emission, scrape targets, rule evaluation and selector/query alignment (LA-05). |
| Not verified | The cause or freshness assertion has not been verified, even if severity is CRIT. | Raw UNVERIFIED cause verification, or unavailable observation/publication timestamps. | Follow domain evidence to verify cause and timestamps; never infer verification from a firing rule (LA-04). |
| STALE | Measured evidence age exceeds its displayed freshness threshold; this is a visibility warning, not product failure. | Current Workflow Evidence: publication age > 24h (86400s). | Refresh the evidence source; inspect publication time independently of run execution dates. |
| Blank / No data | A rendering outcome without a semantic verdict; never automatically OK or zero. | Empty result/frame, missing field, query error, unavailable source or no selected context. | Inspect query/frame, scope and source health. Classify as NO OBSERVATIONS only with its witnesses; otherwise UNKNOWN or TELEMETRY MISSING. |

Numeric encodings are source-specific: use the panel's labelled value mapping,
not a shared numeric enum. In particular, workflow input priority and domain
status gauges have different encodings.

| Panel / source | Numeric mapping |
| --- | --- |
| Monitor Scope Status (9401), Monitor Pipeline Status (18940): `bioetl_workflow_scope_priority_by_input` | 0=OK, 1=UNKNOWN, 2=WARN, 3=CRIT; null=UNKNOWN |
| Monitor Telemetry (907): clamped `bioetl_control_plane_telemetry_missing_5m` | 0=OK, 1=WARN, >=2=CRIT; null=UNKNOWN. These are missing telemetry groups, not failed runs. |

Real zero requires an actual observed sample and its unit, scope and window.
Do not insert synthetic zeroes to hide missing evidence. `VALID_EMPTY` / `VALID
EMPTY` is justified empty output only with the panel's documented evidence
prerequisites; it does not establish fleet health. `Not provided` is a missing
attribute, not a health verdict. `PENDING` is a rule awaiting its firing duration,
not a verified incident. `PRESENT` is observed series coverage, not success;
`DEGRADED` is a monitoring-quality warning, not proof of product failure.

Incident signals (status, suspects, alerts and Fleet) and visibility evidence
must remain visually distinct. Row **Observability Signals** (8809), immediately
before Fleet (8808), holds panels 9102, 907, 894 and 9491 and an on-screen legend.
Scope, window and source remain those of each panel; moving panels changes no
query or health threshold. Current/global evidence does not attest a selected
historical Run ID. Scope headings must preserve that distinction.

LA-07 (#12941): Current Workflow Evidence shows publication age and its 24h
display threshold. The heading reports STALE if any known scoped publication
exceeds that threshold; otherwise missing/invalid publication timestamps or
missing scope produce Not verified. Within threshold means only a measured age
at or below the threshold, never an OK health verdict. Row-level freshness stays
Not verified when its timestamp is absent. Retained evidence and workflow health
rules do not expire at this display threshold. Refresh the dashboard to evaluate
age again; query failures remain errors, never fresh evidence.

Run ID selectors omit the ambiguous legacy [STALE catalog] suffix. They make
no freshness assertion: their on-screen description says catalog freshness is
Not verified here and distinguishes run execution dates from catalog age.
Refresh the dashboard to request an updated list. Catalog API metadata and its
cache policy remain unchanged. The same selector projection is used by Explorer,
Data Quality and Replay Readiness in both dashboard generations.

Repository validation proves generated layout and copy only. Live application
to **Incident Workspace v2** and **Isolated 100000 Incident Workspace** must each
be recorded as `NOT_VERIFIABLE` until the deployed dashboard, expanded row and
legend have been inspected. Confirm actual states and a measured zero against
their source; a generated JSON or successful CI run is not live acceptance.

LA-12 (#12946): Overview and Data Quality expose selection provenance before
run evidence. AUTO means the latest run by start time in the selected scope,
including unfinished runs. EXPLICIT means the requested Run ID stays bound;
an unavailable explicit run is never replaced with a different latest run.
The context includes the actual Run ID, execution state, saved verdict and
Context checked at (Grafana query evaluation time). This clock is not run start,
browser click, server cache load or catalog freshness. A refreshed query
re-evaluates the displayed context. Empty
catalogs say NO RUN; resolution failure says Context unavailable. Neither
context provenance nor the dashboard time range proves saved-run health.


## Portfolio status vocabulary and evidence clocks

The active portfolio uses the five stable UIDs in dashboard-inventory.yaml.
The dashboard-2.0 tag identifies the shared presentation contract; UID suffixes
are compatibility identifiers, not competing data or presentation generations.
The role-specific selector registry remains selector-contracts.yaml. A local
lookup or diagnostic selector is not implicitly a filter on every panel.

Overview separates the saved assessment from CURRENT fleet alert counts and
CURRENT processing-anchor age. FIRING and PENDING counts include every active BioETL
alert, independently of run selectors; zero active alerts is not pipeline OK.
The ingestion-age card follows the visible Pipeline filter, uses the oldest
observed successful-DQ run-start processing anchor after max-per-pipeline/entity
source deduplication. This is not run completion or input-record event time;
provider/source-event freshness remains unverified. STALE >24h is warning and >72h is critical, matching
BioETLDataFreshnessLagHigh/Critical; both alerts additionally need 15m pending.
Entities with missing, invalid or future timestamps remain unverified; an empty
valid set is UNKNOWN. Partial observed coverage never proves completeness.
Workflow publication uses its
separate, existing 24h display threshold. Cache TTL is neither of these clocks.

Run Context displays the saved assessment timestamp and elapsed age alongside
the read clock. It does not display a green cache state as evidence freshness.
There is no inferred freshness SLA for the saved run or a skipped provider
probe. Provider Check shows why a probe was skipped and marks its observation
time N/A instead of substituting run completion.

Incident's first ranked answer and alert list use CURRENT query time, even
when the dashboard range is historical. All returned rows remain reachable;
pagination bounds only the viewport. The heading states the returned row count.
Diagnostic priority HIGH=2 / ELEVATED=1 is a diagnostic rank, distinct from Prometheus alert severity,
cause verification and event freshness. Missing event timestamps remain Not
verified. Fleet empty values say UNKNOWN / no samples and link to coverage
details; no absent telemetry is repaired by a healthy zero.

Monitor Telemetry (907), Monitor Ledger (893) and Review Stage Progress (2460)
use CURRENT clocks for their fixed-window diagnostics. A historical dashboard
date must not turn today's telemetry warning into UNKNOWN. The ledger-appends
chart (8807) remains TIME RANGE and retains its selected rate interval.
Review Stage Progress retains every observed pipeline/run-type/stage group;
pagination limits the viewport rather than dropping all but three groups.
Lag is sorted descending so the observed largest lag is visible first.

Inspect Global Signal Measurements (22011) uses the same CURRENT clock as the
ranked answer; its fixed 15m lag operand does not use a historical dashboard end.
HIGH does not mean a critical Prometheus alert or a verified cause. The active
alert list retains its own severity and pending/firing state. Neither evaluation
time nor a retained Pushgateway sample supplies an event observation timestamp.

| Surface | State interpretation |
| --- | --- |
| Saved run processing | SUCCESS/FAILED/RUNNING describe execution, independently of current alerts. |
| Saved run assessment | OK/WARN/ERROR/INCOMPLETE describe the saved checks and their coverage. They never certify current pipeline health. |
| Exact replay | READY requires the required exact-run checks; fail blocks readiness and an unknown required check is INSUFFICIENT. SELECT RUN requires explicit identity, and is not an AUTO assessment. |
| Individual checks | pass/fail/unknown/n/a describe one named check, not the entire run. |
| Provider Check | NOT PROBED means cached Bronze was used and the provider API was not called. It is neither a healthy probe nor missing evidence. |
| Freshness | Cache FRESH/STALE is the HTTP snapshot age against the returned cache policy; it does not certify freshness of the saved assessment or a provider probe. |
| Source or selection gaps | SELECT RUN, NO RUNS, VALID EMPTY, UNKNOWN and Source unavailable retain distinct meanings above; none is automatically OK. |

Run Context shows the saved assessment timestamp separately from Context checked
at and HTTP cache freshness. The selected-status cache is fresh for less than
30 seconds and may serve stale snapshots for less than 90 seconds while refreshing.
The API returns these policy bounds; presentation must not invent a different
SLA. Since completed on Provider Evidence measures run completion age, not the
age of a remote API probe. A cached-Bronze run has no current remote probe.
A saved run does not expire into a failed run merely because wall time advances.
No periodic-launch SLA is established by the dashboard refresh interval.
Workflow publication evidence retains its separately documented 24h threshold.

Saved refresh=1m (60 seconds) must match a value in timepicker.refresh_intervals.
An unsupported literal such as 60s can leave the session timer Off even for a
relative range. Legacy links with refresh=60s must select 1m in the refresh menu. Managed CURRENT panels
retain their independent refresh clock; their evaluation timestamps are not
publication timestamps. Use a relative range to check the dashboard timer.
