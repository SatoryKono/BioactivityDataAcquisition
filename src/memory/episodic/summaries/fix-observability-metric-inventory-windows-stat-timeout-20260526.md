---
id: fix-observability-metric-inventory-windows-stat-timeout-20260526
title: Fix observability metric inventory Windows stat timeout
task_id: fix-observability-metric-inventory-windows-stat-timeout-20260526
created_at: '2026-05-26T04:06:08Z'
ttl_days: 14
confidence: episodic
source_refs:
- scripts/engineering/qa/report_observability_metric_inventory.py
- tests/unit/scripts/test_report_observability_metric_inventory.py
summary: Updated observability metric inventory text discovery to avoid Windows/GDrive
  stat hangs. Repo-local scan roots now use bounded git ls-files before any Path.exists/is_file/os.walk
  fallback, and rg/git discovery stdout is captured through temporary files instead
  of subprocess pipes. Added unit regressions for stat-free git discovery and suffix
  filtering.
---

# Episodic summary

## Task

- Title: Fix observability metric inventory Windows stat timeout

## Outcome

- Updated observability metric inventory text discovery to avoid Windows/GDrive stat hangs. Repo-local scan roots now use bounded git ls-files before any Path.exists/is_file/os.walk fallback, and rg/git discovery stdout is captured through temporary files instead of subprocess pipes. Added unit regressions for stat-free git discovery and suffix filtering.

## Lessons learned

- For repository-local inventory scans on Windows/GDrive worktrees, prefer
  `git ls-files` before `Path.exists`, `Path.is_file`, or recursive `os.walk`;
  Python stat calls can block before test-level timeouts can recover.
