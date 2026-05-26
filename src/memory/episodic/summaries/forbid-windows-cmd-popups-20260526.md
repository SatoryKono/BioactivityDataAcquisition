---
id: forbid-windows-cmd-popups-20260526
title: Forbid Windows cmd popup windows for subprocess helpers
task_id: forbid-windows-cmd-popups-20260526
created_at: '2026-05-26T06:21:52Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/memory/notes.py
- tests/unit/memory/test_notes_workflow.py
- tests/architecture/test_application_services_lazy_facade_governance.py
- tests/architecture/test_composite_canonical_surfaces.py
- scripts/engineering/qa/report_observability_metric_inventory.py
- tests/unit/scripts/test_report_observability_metric_inventory.py
summary: Added hidden Windows subprocess kwargs (CREATE_NO_WINDOW plus STARTUPINFO/SW_HIDE)
  to bounded git/rg subprocess helpers used by memory note parsing, architecture scanners,
  and observability metric inventory scans. Added regression coverage for the no-console
  kwargs in memory, architecture, and inventory tests.
---

# Episodic summary

## Task

- Title: Forbid Windows cmd popup windows for subprocess helpers

## Outcome

- Added hidden Windows subprocess kwargs (CREATE_NO_WINDOW plus STARTUPINFO/SW_HIDE) to bounded git/rg subprocess helpers used by memory note parsing, architecture scanners, and observability metric inventory scans. Added regression coverage for the no-console kwargs in memory, architecture, and inventory tests.

## Lessons learned

- Any subprocess helper added for Windows/PyCharm timeout mitigation should also
  pass hidden Windows startup kwargs; otherwise fixing a hang can introduce
  visible console popups during test runs.
