---
id: fix-compatibility-importer-census-governance
title: Fix compatibility importer census governance failure
task_id: fix_compatibility_importer_census_governance
created_at: '2026-06-15T17:37:15Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Regenerated committed compatibility importer census JSON and Markdown artifacts
  to match the current generator output. Drift was in retained_public_export_facades
  for health_api sanctioned lazy export keys. Verified report --check and exact sync
  test on Linux and Windows. No src changes or coverage/scorecard refresh required.
---

# Episodic summary

## Task

- Title: Fix compatibility importer census governance failure

## Outcome

- Regenerated committed compatibility importer census JSON and Markdown artifacts to match the current generator output. Drift was in retained_public_export_facades for health_api sanctioned lazy export keys. Verified report --check and exact sync test on Linux and Windows. No src changes or coverage/scorecard refresh required.

## Lessons learned

- Replace with durable follow-up if needed
