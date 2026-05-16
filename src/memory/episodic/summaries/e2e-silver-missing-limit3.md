---
id: e2e-silver-missing-limit3
title: investigate-missing-silver-table-e2e
task_id: e2e-silver-missing-limit3
created_at: '2026-05-16T13:10:40Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Removed module-scoped chembl_activity seed fixtures from advanced_scenarios
  E2E and moved seed materialization into VCR-scoped test bodies via _seed_chembl_activity_silver(e2e_data_dir,
  limit=10). This avoids live/module-setup drift where fixture setup could build the
  seed outside active cassette playback and fail with missing Silver table.
---

# Episodic summary

## Task

- Title: investigate-missing-silver-table-e2e

## Outcome

- Removed module-scoped chembl_activity seed fixtures from advanced_scenarios E2E and moved seed materialization into VCR-scoped test bodies via _seed_chembl_activity_silver(e2e_data_dir, limit=10). This avoids live/module-setup drift where fixture setup could build the seed outside active cassette playback and fail with missing Silver table.

## Lessons learned

- Replace with durable follow-up if needed
