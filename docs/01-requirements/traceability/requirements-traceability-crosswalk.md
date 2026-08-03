# Requirements Traceability Crosswalk

- snapshot_date: 2026-07-16
- source: `docs/01-requirements/REQUIREMENTS.md` v1.12
- canonical_rules_owner: `docs/00-project/RULES.md` v6.1.5
- artifact: `docs/01-requirements/traceability/requirements-traceability-crosswalk.csv`
- row_count: 168
- modality_counts: `147 MUST`, `16 MUST NOT`, `4 SHOULD`, `1 MAY`
- status_counts: `162 confirmed`, `6 updated`, `0 conflict`, `0 follow-up`

## New Rows

- `REQ-GOV-001..012` — testable projections for the 18 Qodo-reconciled
  change-set gates in `RULES.md` §4.5.

## Updated Rows

- `REQ-CB-004` — canonical Prometheus metric naming synchronized
- `REQ-OBS-001` — `run_id` correlation wording synchronized with Prometheus label guardrail
- `REQ-DQ-001` — canonical `bioetl_*` Prometheus naming synchronized
- `REQ-DQ-002` — `bioetl_dq_validation_score` naming synchronized
- `REQ-DQ-003` — `bioetl_data_freshness_seconds` naming synchronized
- `REQ-HEALTH-003` — `bioetl_provider_health_status` naming synchronized

## Resolution Notes

- The crosswalk now covers all 168 active requirements, including the 12 new
  cross-cutting governance requirements.
- No active `CONTRIBUTING.md` conflict required remediation in current `main`.
- The historical `.codex/agents/CODEX-RUNTIME.md` missing-file defect remains resolved and was not reopened.
