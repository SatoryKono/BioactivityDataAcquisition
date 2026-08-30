# Requirements Traceability Crosswalk

- snapshot_date: 2026-08-28
- source: `docs/01-requirements/REQUIREMENTS.md` v1.12.7
- canonical_rules_owner: `docs/00-project/RULES.md` v6.1.11
- artifact: `docs/01-requirements/traceability/requirements-traceability-crosswalk.csv`
- row_count: 192
- modality_counts: `167 MUST`, `16 MUST NOT`, `8 SHOULD`, `1 MAY`
- status_counts: `186 confirmed`, `6 updated`, `0 conflict`, `0 follow-up`

## New Rows

- `REQ-ARCH-011/012/013/030/031/040/041`, `REQ-AUDIT-001/002`, `REQ-CONF-001`,
  `REQ-ERR-015`, `REQ-OBS-010`, `REQ-VAL-001..008` — invented IDs from RULES,
  ADR-033, and `src/bioetl/` now have canonical CSV rows (#9803).
- `REQ-DASH-001..004` — density, typography, area-fill presentation, and
  scalar information density (`DASH-DENSITY-002`) delegated by `RULES.md`
  §3.2.3 to the scoped dashboard contract.
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

- The crosswalk now covers all 192 active requirements, including the 20
  previously invented RULES/ADR-033/`src/` identifiers, the four
  dashboard presentation requirements and 12 cross-cutting governance
  requirements.
- No active `CONTRIBUTING.md` conflict required remediation in current `main`.
- The historical `.codex/agents/CODEX-RUNTIME.md` missing-file defect remains resolved and was not reopened.
