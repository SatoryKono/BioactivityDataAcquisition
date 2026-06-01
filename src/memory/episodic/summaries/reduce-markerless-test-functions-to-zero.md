---
id: reduce-markerless-test-functions-to-zero
title: Reduce markerless test functions toward zero
task_id: reduce-markerless-test-functions-to-zero
created_at: '2026-06-01T13:34:25Z'
ttl_days: 14
confidence: episodic
source_refs:
- user-request-markerless-to-zero
summary: Bulk closeout added module-level lane pytest markers across remaining markerless
  unit, architecture, integration, contract, security, and smoke test modules. Governance
  scanner now reports markerless_test_functions=0 and configs/quality/test_governance_audit.yaml
  ratchets markerless_test_functions_max to 0. Removed a small set of unused imports
  surfaced by critical touched-file ruff checks. Verified targeted governance budget
  guard, critical ruff selectors E9/F401/F821/E402 on mtime-touched tests, representative
  execution shard, YAML parse, syntax scan, live governance counts, and scoped whitespace/conflict
  scan. Full path-scoped ruff remains polluted by pre-existing lint debt outside this
  marker closeout.
---

# Episodic summary

## Task

- Title: Reduce markerless test functions toward zero

## Outcome

- Bulk closeout added module-level lane pytest markers across remaining markerless unit, architecture, integration, contract, security, and smoke test modules. Governance scanner now reports markerless_test_functions=0 and configs/quality/test_governance_audit.yaml ratchets markerless_test_functions_max to 0. Removed a small set of unused imports surfaced by critical touched-file ruff checks. Verified targeted governance budget guard, critical ruff selectors E9/F401/F821/E402 on mtime-touched tests, representative execution shard, YAML parse, syntax scan, live governance counts, and scoped whitespace/conflict scan. Full path-scoped ruff remains polluted by pre-existing lint debt outside this marker closeout.

## Lessons learned

- Replace with durable follow-up if needed
