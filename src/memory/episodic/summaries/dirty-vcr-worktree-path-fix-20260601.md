---
id: dirty-vcr-worktree-path-fix-20260601
title: Fix dirty VCR worktree path normalization
task_id: dirty-vcr-worktree-path-fix-20260601
created_at: '2026-06-01T10:32:44Z'
ttl_days: 14
confidence: episodic
source_refs:
- scripts/engineering/qa/check_test_audit_preflight.py
summary: Made git-status path parsing tolerant to a stripped leading space on the
  first porcelain line so dirty VCR worktree examples keep the full tests/fixtures/vcr
  path.
---

# Episodic summary

## Task

- Title: Fix dirty VCR worktree path normalization

## Outcome

- Made git-status path parsing tolerant to a stripped leading space on the first porcelain line so dirty VCR worktree examples keep the full tests/fixtures/vcr path.

## Lessons learned

- Replace with durable follow-up if needed
