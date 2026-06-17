---
id: fix-architecture-generated-artifact-failures
title: Fix architecture generated artifact failures
task_id: fix-architecture-generated-artifact-failures
created_at: '2026-06-17T08:40:04Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_adr_enforcement_matrix.py
summary: 'Made the ADR enforcement matrix generator robust to git-grep failures by
  falling back to a deterministic Python scan over git ls-files output, regenerated
  ADR enforcement matrix artifacts, synchronized the architecture quality scorecard
  to the current module coverage inventory hashes, and verified the ADR matrix, scorecard,
  and issue #5265 closeout architecture tests pass. Debt budgets were not increased.'
---

# Episodic summary

## Task

- Title: Fix architecture generated artifact failures

## Outcome

- Made the ADR enforcement matrix generator robust to git-grep failures by falling back to a deterministic Python scan over git ls-files output, regenerated ADR enforcement matrix artifacts, synchronized the architecture quality scorecard to the current module coverage inventory hashes, and verified the ADR matrix, scorecard, and issue #5265 closeout architecture tests pass. Debt budgets were not increased.

## Lessons learned

- Replace with durable follow-up if needed
