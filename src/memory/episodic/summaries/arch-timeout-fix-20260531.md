---
id: arch-timeout-fix-20260531
title: Fix architecture test timeout
task_id: arch-timeout-fix-20260531
created_at: '2026-05-31T12:59:38Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_application_services_lazy_facade_governance.py
summary: Bypassed slow external repo scans for Windows processes running against /mnt-mounted
  worktrees in the lazy facade governance architecture test; targeted pytest passed.
---

# Episodic summary

## Task

- Title: Fix architecture test timeout

## Outcome

- Bypassed slow external repo scans for Windows processes running against /mnt-mounted worktrees in the lazy facade governance architecture test; targeted pytest passed.

## Lessons learned

- Replace with durable follow-up if needed
