---
id: fix-adr-scorecard-coverage-failures
title: Fix ADR scorecard coverage architecture failures
task_id: fix-adr-scorecard-coverage-failures
created_at: '2026-06-17T08:46:55Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests-architecture-failures
summary: 'Fixed architecture failures by making ADR enforcement matrix scanning degrade
  from git grep to git ls-files backed Python scanning on git grep failure, adding
  regression coverage for the fallback, and staging refreshed module coverage plus
  architecture quality scorecard artifacts so live collector hashes match. Validation
  passed: targeted architecture pytest for ADR matrix, architecture scorecard, and
  issue #5265 closeout; ADR matrix --check; module coverage --check; ruff check/format;
  git diff --check.'
---

# Episodic summary

## Task

- Title: Fix ADR scorecard coverage architecture failures

## Outcome

- Fixed architecture failures by making ADR enforcement matrix scanning degrade from git grep to git ls-files backed Python scanning on git grep failure, adding regression coverage for the fallback, and staging refreshed module coverage plus architecture quality scorecard artifacts so live collector hashes match. Validation passed: targeted architecture pytest for ADR matrix, architecture scorecard, and issue #5265 closeout; ADR matrix --check; module coverage --check; ruff check/format; git diff --check.

## Lessons learned

- Replace with durable follow-up if needed
