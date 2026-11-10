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

Repository validation proves generated layout and copy only. Live application
to **Incident Workspace v2** and **Isolated 100000 Incident Workspace** must each
be recorded as `NOT_VERIFIABLE` until the deployed dashboard, expanded row and
legend have been inspected. Confirm actual states and a measured zero against
their source; a generated JSON or successful CI run is not live acceptance.
