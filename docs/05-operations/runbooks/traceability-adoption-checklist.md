# Traceability Adoption Checklist

*Last verified: 2026-03-26*

## Purpose

Capture objective operator-adoption evidence for Wave 4 Traceability Fabric
and the final manual release-readiness gate referenced by Wave 5.
This checklist is executed after tabletop drills and incident simulations.

## Wave 5 Closeout Expectation

Before declaring the operator gate passed:

- record at least 3 recent sessions covering scenarios A/B/C from
  [Traceability Tabletop Drills](traceability-tabletop-drills.md);
- use the canonical execution flow from
  [Traceability Wave 5 Closeout Pack](traceability-wave5-closeout-pack.md);
- achieve average score `>= 7`;
- ensure no failed session remains without follow-up within 7 days;
- attach the resulting outcome to the Wave 5 release decision.

## Readiness Checklist

Mark all items before declaring operator adoption complete:

- [ ] On-call can resolve `run_id -> manifest_id` using `run-manifest show`.
- [ ] On-call can explain `diagnostics.latest_status` and `latest_event_type`.
- [ ] On-call can interpret `event_family_counts` without escalation.
- [ ] On-call can identify artifact linkage gaps from `missing_artifact_links`.
- [ ] On-call can route incident by `alert_signals` to the correct owner.
- [ ] On-call can justify decision using `next_steps` + runbook policy.
- [ ] Escalation path is executed within target SLA for P1 scenarios.
- [ ] Drill evidence is recorded in the session log below.

## Session Log

| Date | Scenario | Operator | Time to first diagnosis | Time to decision | Score (0-8) | Outcome | Notes |
|---|---|---|---:|---:|---:|---|---|
| YYYY-MM-DD | Missing Manifest / Artifact Linkage / DQ Failure | name | Xm | Ym | N | pass / conditional / fail | summary |

## Exit Gate

Wave 4 / Wave 5 operator adoption gate is considered passed when:

- at least 3 recent sessions are recorded;
- average score is >= 7;
- no failed session remains without a follow-up session in 7 days.

## Related Runbooks

- [Traceability Tabletop Drills](traceability-tabletop-drills.md)
- [Traceability Wave 5 Closeout Pack](traceability-wave5-closeout-pack.md)
- [Traceability Signal Ownership](traceability-signal-ownership.md)
- [Run Manifest Inspection](run-manifest-inspection.md)
