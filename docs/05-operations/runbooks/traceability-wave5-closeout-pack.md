# Traceability Wave 5 Closeout Pack

*Last verified: 2026-03-26*

## Purpose

Provide one practical execution pack for the final manual `Wave 5` gate:
operator tabletop/adoption validation.

Use this pack together with:

- [Run Manifest Inspection](run-manifest-inspection.md)
- [Traceability Signal Ownership](traceability-signal-ownership.md)
- [Traceability Tabletop Drills](traceability-tabletop-drills.md)
- [Traceability Adoption Checklist](traceability-adoption-checklist.md)

## Closeout Scope

The technical `Wave 5` gates are already covered by automated evidence. This
pack exists only for the remaining manual proof that operators can navigate:

`alert -> run_id -> manifest -> diagnostics -> artifacts -> decision`

## Required Sessions

Run exactly these 3 sessions:

| Session | Scenario | Primary goal |
|---|---|---|
| `W5-TT-01` | Scenario A: Missing Manifest Link | prove immediate control-plane escalation path |
| `W5-TT-02` | Scenario B: Artifact Linkage Regression | prove artifact/lineage gap diagnosis |
| `W5-TT-03` | Scenario C: DQ-Driven Failure with Good Control Plane | prove DQ-aware decision routing |

## Facilitator Prep

Before each session confirm:

- one realistic `run_id` or synthetic example is ready;
- `bioetl run-manifest show <run-id> --format json` is available;
- operator has access to the related ticket/incident template;
- expected owner path is known from
  [Traceability Signal Ownership](traceability-signal-ownership.md).

## Operator Flow

For every session the operator should perform the same base flow:

1. Run `bioetl run-manifest show <run-id> --format json`.
2. Record `run_id`, `manifest_id`, `pipeline_name`, `latest_status`, and `latest_event_type`.
3. Review `event_family_counts`, `artifact_refs`, `missing_artifact_links`, and `alert_signals`.
4. Choose routing owner and escalation path.
5. State one decision: `retry`, `quarantine`, `rollback`, `monitor`, or `escalate`.
6. Explain why that decision is safe under the runbook policy.

## Evidence To Capture

Record these fields for every session:

- `session_id`
- `date`
- `scenario`
- `operator`
- `run_id`
- `manifest_id`
- `time_to_first_diagnosis`
- `time_to_decision`
- `score_0_to_8`
- `outcome`
- `owner_route`
- `decision`
- `notes`

## Session Log Template

Paste completed rows into
[Traceability Adoption Checklist](traceability-adoption-checklist.md).

| Session ID | Date | Scenario | Operator | run_id | manifest_id | Time to first diagnosis | Time to decision | Score | Outcome | Owner route | Decision | Notes |
|---|---|---|---|---|---|---:|---:|---:|---|---|---|---|
| `W5-TT-01` | YYYY-MM-DD | Missing Manifest Link | name | `...` | `.../n/a` | Xm | Ym | N | pass / conditional / fail | Control Plane Owner | escalate | summary |
| `W5-TT-02` | YYYY-MM-DD | Artifact Linkage Regression | name | `...` | `...` | Xm | Ym | N | pass / conditional / fail | Storage/Metadata Owner | monitor / escalate | summary |
| `W5-TT-03` | YYYY-MM-DD | DQ Failure | name | `...` | `...` | Xm | Ym | N | pass / conditional / fail | Data Quality Owner | quarantine / retry / escalate | summary |

## Done-When

The manual `Wave 5` gate is ready to mark passed when:

- all 3 sessions are recorded;
- average score is `>= 7`;
- no failed session is left without follow-up;
- the result is referenced in the `Wave 5` release decision.

## Sign-Off Note

Suggested release note text:

> Operator tabletop/adoption gate passed: 3 sessions completed, average score
> >= 7, no unresolved failed drills, release decision updated.
