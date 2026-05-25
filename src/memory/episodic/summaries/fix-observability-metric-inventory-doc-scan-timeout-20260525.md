---
id: fix-observability-metric-inventory-doc-scan-timeout-20260525
title: Fix observability metric inventory doc scan timeout
task_id: fix-observability-metric-inventory-doc-scan-timeout-20260525
created_at: '2026-05-25T18:03:13Z'
ttl_days: 14
confidence: episodic
source_refs:
- scripts/engineering/qa/report_observability_metric_inventory.py
- tests/unit/scripts/test_report_observability_metric_inventory.py
- tests/integration/test_runtime_metric_emission_consistency.py
summary: Moved observability metric documentation mention scanning to bounded git
  grep in real checkouts, with explicit UTF-8 subprocess decoding and direct-read
  fallback only for temporary non-git trees; added regression coverage and validated
  the Windows pytest timeout case.
---

# Episodic summary

## Task

- Title: Fix observability metric inventory doc scan timeout

## Outcome

- Moved observability metric documentation mention scanning to bounded git grep in real checkouts, with explicit UTF-8 subprocess decoding and direct-read fallback only for temporary non-git trees; added regression coverage and validated the Windows pytest timeout case.

## Lessons learned

- Inventory scanners that run inside pytest should avoid unbounded Python
  `Path.read_text()` across documentation trees on Windows/GDrive checkouts;
  prefer bounded subprocess grep with explicit UTF-8 decoding.
