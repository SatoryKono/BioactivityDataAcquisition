---
id: issue-5508-maintenance-owner-paths
title: Refactor maintenance CLI access chain to owner-only paths
task_id: issue-5508-maintenance-owner-paths
created_at: '2026-06-22T15:58:03Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/maintenance_service_access.py
summary: Collapsed maintenance CLI service access onto composition.maintenance_service_access,
  which delegates directly to composition owner internals instead of retained public
  maintenance/resources facades. Reduced maintenance.py to the public Click shell,
  ratcheted compatibility importer expectations for maintenance_api to zero first-party
  src importers, and refreshed compatibility census, module coverage inventory, and
  architecture quality scorecard.
---

# Episodic summary

## Task

- Title: Refactor maintenance CLI access chain to owner-only paths

## Outcome

- Collapsed maintenance CLI service access onto composition.maintenance_service_access, which delegates directly to composition owner internals instead of retained public maintenance/resources facades. Reduced maintenance.py to the public Click shell, ratcheted compatibility importer expectations for maintenance_api to zero first-party src importers, and refreshed compatibility census, module coverage inventory, and architecture quality scorecard.

## Lessons learned

- Replace with durable follow-up if needed
