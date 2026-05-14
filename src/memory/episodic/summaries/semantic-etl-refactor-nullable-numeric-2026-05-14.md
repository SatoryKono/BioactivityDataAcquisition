---
id: semantic-etl-refactor-nullable-numeric-2026-05-14
title: Implement nullable numeric semantic contract guard
task_id: semantic-etl-refactor-nullable-numeric-2026-05-14
created_at: '2026-05-14T17:03:52Z'
ttl_days: 14
confidence: episodic
source_refs:
- scripts/engineering/qa/check_gold_nullable_numeric_compatibility.py
summary: Added Gold nullable numeric compatibility QA gate for publication year/citations,
  molecule descriptors, and ChEMBL activity measurements. The gate checks published
  Gold JSON contracts, source Pandera markers, and gold-schemas documentation. Added
  routed scripts.engineering.qa command and integration tests. Validation passed for
  direct/routed gate, new tests, semantic contract bundle, Gold snapshot registry
  tests, ruff, py_compile, import-boundary scan, and touched-doc forbidden-pattern
  scan. Full check_docs_drift remains blocked by existing OSError on unrelated docs
  report path.
---

# Episodic summary

## Task

- Title: Implement nullable numeric semantic contract guard

## Outcome

- Added Gold nullable numeric compatibility QA gate for publication year/citations, molecule descriptors, and ChEMBL activity measurements. The gate checks published Gold JSON contracts, source Pandera markers, and gold-schemas documentation. Added routed scripts.engineering.qa command and integration tests. Validation passed for direct/routed gate, new tests, semantic contract bundle, Gold snapshot registry tests, ruff, py_compile, import-boundary scan, and touched-doc forbidden-pattern scan. Full check_docs_drift remains blocked by existing OSError on unrelated docs report path.

## Lessons learned

- Replace with durable follow-up if needed
