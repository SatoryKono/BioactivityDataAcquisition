---
id: semantic-etl-refactor-generic-field-ownership-2026-05-14
title: Implement generic field ownership guard
task_id: semantic-etl-refactor-generic-field-ownership-2026-05-14
created_at: '2026-05-14T17:17:44Z'
ttl_days: 14
confidence: episodic
source_refs:
- scripts/engineering/qa/check_generic_field_ownership.py
summary: 'Added generic field ownership registry and QA gate for denied generic lexical
  fields: description, relation, score, source, status, type, and value. The gate
  scans canonical registry clusters, Gold JSON properties, composite column groups,
  and composite field group base names, requiring explicit owner, semantic role, and
  rationale metadata for allowed provider-scoped uses. Added routed scripts.engineering.qa
  command, integration tests, and canonical registry documentation. Validation passed
  for direct/routed gate, semantic-field registry gate, semantic contract bundle,
  YAML parse, ruff, py_compile, touched-doc forbidden-pattern scan, and import-boundary
  scan. Full check_docs_drift remains blocked by existing OSError on unrelated docs
  report path.'
---

# Episodic summary

## Task

- Title: Implement generic field ownership guard

## Outcome

- Added generic field ownership registry and QA gate for denied generic lexical fields: description, relation, score, source, status, type, and value. The gate scans canonical registry clusters, Gold JSON properties, composite column groups, and composite field group base names, requiring explicit owner, semantic role, and rationale metadata for allowed provider-scoped uses. Added routed scripts.engineering.qa command, integration tests, and canonical registry documentation. Validation passed for direct/routed gate, semantic-field registry gate, semantic contract bundle, YAML parse, ruff, py_compile, touched-doc forbidden-pattern scan, and import-boundary scan. Full check_docs_drift remains blocked by existing OSError on unrelated docs report path.

## Lessons learned

- Replace with durable follow-up if needed
