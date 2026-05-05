---
id: sonar-tangles-fix-wave-4
title: Fix Sonar weak tangles wave 4
task_id: sonar-tangles-fix-wave-4
created_at: '2026-05-05T08:12:16Z'
ttl_days: 14
confidence: episodic
source_refs:
- docs/00-project/ai/memory/memory-py-architecture-debt-bot.md
summary: Reduced weak Sonar coupling by converting composition.factories.services
  package exports to a lazy facade around pipeline creation support and by extracting
  a CsvExporter protocol seam so gold and silver storage helpers depend on a lightweight
  export contract instead of the concrete exporter class; resynced architecture dependency
  docs after the topology change.
---

# Episodic summary

## Task

- Title: Fix Sonar weak tangles wave 4

## Outcome

- Reduced weak Sonar coupling by converting composition.factories.services package exports to a lazy facade around pipeline creation support and by extracting a CsvExporter protocol seam so gold and silver storage helpers depend on a lightweight export contract instead of the concrete exporter class; resynced architecture dependency docs after the topology change.

## Lessons learned

- Replace with durable follow-up if needed
