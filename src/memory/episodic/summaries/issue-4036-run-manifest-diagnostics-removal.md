---
id: issue-4036-run-manifest-diagnostics-removal
title: Issue 4036 run manifest diagnostics facade removal
task_id: issue-4036-run-manifest-diagnostics-removal
created_at: '2026-05-13T16:41:40Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Removed run_manifest_diagnostics.py from application.services, moved the
  remaining test caller to the canonical control_plane owner, updated active memory/governance
  path maps, and passed targeted pytest via the repo wrapper; refresh still requires
  skip-refresh because generated memory surfaces can lag removal waves.
---

# Episodic summary

## Task

- Title: Issue 4036 run manifest diagnostics facade removal

## Outcome

- Removed run_manifest_diagnostics.py from application.services, moved the remaining test caller to the canonical control_plane owner, updated active memory/governance path maps, and passed targeted pytest via the repo wrapper; refresh still requires skip-refresh because generated memory surfaces can lag removal waves.

## Lessons learned

- Replace with durable follow-up if needed
