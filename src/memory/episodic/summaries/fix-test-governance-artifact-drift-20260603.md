---
id: fix-test-governance-artifact-drift-20260603
title: Fix test-governance artifact drift
task_id: fix-test-governance-artifact-drift-20260603
created_at: '2026-06-03T17:05:43Z'
ttl_days: 14
confidence: episodic
source_refs:
- AGENTS.md
summary: 'Re-generated the stale test-governance snapshot so reports/quality/test-governance-current.json
  now matches live collector output. Verified both WSL and Windows .venv-win paths:
  report_test_governance_audit --check returns 0 and the failing architecture pytest
  node passes.'
---

# Episodic summary

## Task

- Title: Fix test-governance artifact drift

## Outcome

- Re-generated the stale test-governance snapshot so reports/quality/test-governance-current.json now matches live collector output. Verified both WSL and Windows .venv-win paths: report_test_governance_audit --check returns 0 and the failing architecture pytest node passes.

## Lessons learned

- Replace with durable follow-up if needed
