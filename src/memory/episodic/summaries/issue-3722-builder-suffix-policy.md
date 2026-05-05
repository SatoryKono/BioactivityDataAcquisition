---
id: issue-3722-builder-suffix-policy
title: Enforce composition-only Builder suffix policy
task_id: issue-3722-builder-suffix-policy
created_at: '2026-05-05T16:16:05Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: 'Extended the layer-aware naming gate for issue #3722: public *Builder classes,
  aliases, facade re-exports, and unregistered non-composition *_builder(s).py module
  names are now rejected. Existing non-composition builder-named helper modules are
  documented as structured allowed_module_exceptions, while composition-owned and
  private builder helpers remain allowed.'
---

# Episodic summary

## Task

- Title: Enforce composition-only Builder suffix policy

## Outcome

- Extended the layer-aware naming gate for issue #3722: public *Builder classes, aliases, facade re-exports, and unregistered non-composition *_builder(s).py module names are now rejected. Existing non-composition builder-named helper modules are documented as structured allowed_module_exceptions, while composition-owned and private builder helpers remain allowed.

## Lessons learned

- Replace with durable follow-up if needed
