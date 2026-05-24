---
id: compatibility-freeze-bootstrap-all-literal
title: fix-package-level-lazy-proxy-freeze-guard
task_id: compatibility-freeze-bootstrap-all-literal
created_at: '2026-05-24T17:41:59Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/bootstrap/__init__.py
summary: Changed composition bootstrap package __all__ from dynamic list(_PUBLIC_EXPORTS)
  to a literal typed list so compatibility freeze guards can verify the curated lazy
  proxy export surface; validated targeted freeze guard, full compatibility freeze
  guard architecture file, ruff, and diff whitespace check.
---

# Episodic summary

## Task

- Title: fix-package-level-lazy-proxy-freeze-guard

## Outcome

- Changed composition bootstrap package __all__ from dynamic list(_PUBLIC_EXPORTS) to a literal typed list so compatibility freeze guards can verify the curated lazy proxy export surface; validated targeted freeze guard, full compatibility freeze guard architecture file, ruff, and diff whitespace check.

## Lessons learned

- Replace with durable follow-up if needed
