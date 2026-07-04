# Requirements Traceability Crosswalk

- snapshot_date: 2026-06-26
- source: `docs/01-requirements/REQUIREMENTS.md` v1.11
- canonical_rules_owner: `docs/00-project/RULES.md` v6.1.4
- artifact: `docs/01-requirements/traceability/requirements-traceability-crosswalk.csv`
- row_count: 156
- modality_counts: `138 MUST`, `13 MUST NOT`, `4 SHOULD`, `1 MAY`
- status_counts: `150 confirmed`, `6 updated`, `0 conflict`, `0 follow-up`

## Updated Rows

- `REQ-CB-004` — canonical Prometheus metric naming synchronized
- `REQ-OBS-001` — `run_id` correlation wording synchronized with Prometheus label guardrail
- `REQ-DQ-001` — canonical `bioetl_*` Prometheus naming synchronized
- `REQ-DQ-002` — `bioetl_dq_validation_score` naming synchronized
- `REQ-DQ-003` — `bioetl_data_freshness_seconds` naming synchronized
- `REQ-HEALTH-003` — `bioetl_provider_health_status` naming synchronized

## Resolution Notes

- The historical `139 MUST` summary defect is resolved in `REQUIREMENTS.md` and reflected in the CSV.
- No active `CONTRIBUTING.md` conflict required remediation in current `main`.
- The historical `.codex/agents/CODEX-RUNTIME.md` missing-file defect remains resolved and was not reopened.
