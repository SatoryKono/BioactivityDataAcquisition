---
id: fix-test-structural-debt-2000-loc
title: Fix test structural debt failures
task_id: fix-test-structural-debt-2000-loc
created_at: '2026-06-16T08:18:26Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Validated structural-debt failures against current tree. tests/unit/interfaces/http/test_health_server_control_plane_identity.py
  is 1749 LOC, below the 2000 LOC threshold. tests/unit/composition/test_coverage_boost_facades.py
  workflow service tests are split into 32-LOC and 21-LOC functions, below the 200
  LOC threshold. Direct pytest run for tests/architecture/test_test_structural_debt.py
  passed.
---

# Episodic summary

## Task

- Title: Fix test structural debt failures

## Outcome

- Validated structural-debt failures against current tree. tests/unit/interfaces/http/test_health_server_control_plane_identity.py is 1749 LOC, below the 2000 LOC threshold. tests/unit/composition/test_coverage_boost_facades.py workflow service tests are split into 32-LOC and 21-LOC functions, below the 200 LOC threshold. Direct pytest run for tests/architecture/test_test_structural_debt.py passed.

## Lessons learned

- Replace with durable follow-up if needed
