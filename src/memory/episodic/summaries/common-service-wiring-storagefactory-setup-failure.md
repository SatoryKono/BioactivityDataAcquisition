---
id: common-service-wiring-storagefactory-setup-failure
title: Fix common_service_wiring StorageFactory setup failure
task_id: common-service-wiring-storagefactory-setup-failure
created_at: '2026-06-04T12:30:36Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Updated the integration pipeline storage factory compatibility patch to use
  create=True for the removed common_service_wiring.StorageFactory alias; validated
  ChEMBL activity happy-path and error-handling integration tests plus ruff.
---

# Episodic summary

## Task

- Title: Fix common_service_wiring StorageFactory setup failure

## Outcome

- Updated the integration pipeline storage factory compatibility patch to use create=True for the removed common_service_wiring.StorageFactory alias; validated ChEMBL activity happy-path and error-handling integration tests plus ruff.

## Lessons learned

- Replace with durable follow-up if needed
