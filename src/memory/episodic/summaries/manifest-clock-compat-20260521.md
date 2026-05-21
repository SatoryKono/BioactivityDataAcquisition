---
id: manifest-clock-compat-20260521
title: Restore ManifestClock compatibility alias
task_id: manifest-clock-compat-20260521
created_at: '2026-05-21T09:47:01Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Restored compatibility by exporting ManifestClock as an alias of ManifestClockPort
  in control-plane manifest time helpers. This keeps runtime imports for run_manifest_service
  and e2e bootstrap paths stable without reintroducing a naming-guard ClassDef violation.
  Validated py_compile, direct imports, and architecture naming/private-import slices.
---

# Episodic summary

## Task

- Title: Restore ManifestClock compatibility alias

## Outcome

- Restored compatibility by exporting ManifestClock as an alias of ManifestClockPort in control-plane manifest time helpers. This keeps runtime imports for run_manifest_service and e2e bootstrap paths stable without reintroducing a naming-guard ClassDef violation. Validated py_compile, direct imports, and architecture naming/private-import slices.

## Lessons learned

- Replace with durable follow-up if needed
