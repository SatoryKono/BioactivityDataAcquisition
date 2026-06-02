---
id: quarantine-backend-ready-warning
title: Debug Quarantine Explorer readiness warning
task_id: quarantine-backend-ready-warning
created_at: '2026-06-01T19:28:57Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Diagnosed Windows Quarantine Explorer readiness warning for chembl_baseline.
  Found stale duplicate listeners on port 8081, cleaned them up, fixed backend cleanup
  to terminate all listeners, disabled TCP reuse_address for health server, added
  regression coverage, refreshed module coverage inventory, and verified targeted
  architecture guardrails.
---

# Episodic summary

## Task

- Title: Debug Quarantine Explorer readiness warning

## Outcome

- Diagnosed Windows Quarantine Explorer readiness warning for chembl_baseline. Found stale duplicate listeners on port 8081, cleaned them up, fixed backend cleanup to terminate all listeners, disabled TCP reuse_address for health server, added regression coverage, refreshed module coverage inventory, and verified targeted architecture guardrails.

## Lessons learned

- Replace with durable follow-up if needed
