---
id: fix-app-services-facade-tempfile-cleanup-win32-20260526
title: Fix application services facade Windows scanner timeout
task_id: fix-app-services-facade-tempfile-cleanup-win32-20260526
created_at: '2026-05-26T05:29:17Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_application_services_lazy_facade_governance.py
summary: Removed the unbounded Python subprocess tree-scan fallback from the application-services
  lazy facade governance test. The scanner now uses bounded rg/git grep fixed-string
  line discovery, filters exact package-root imports in Python, ignores submodule
  imports, and performs best-effort temp output cleanup without masking TimeoutExpired
  as WinError 32.
---

# Episodic summary

## Task

- Title: Fix application services facade Windows scanner timeout

## Outcome

- Removed the unbounded Python subprocess tree-scan fallback from the application-services lazy facade governance test. The scanner now uses bounded rg/git grep fixed-string line discovery, filters exact package-root imports in Python, ignores submodule imports, and performs best-effort temp output cleanup without masking TimeoutExpired as WinError 32.

## Lessons learned

- For Windows/PyCharm architecture scans on Google Drive-backed worktrees,
  subprocess-based Python `rglob` fallbacks are not bounded enough. Prefer
  line-oriented `rg`/`git grep` discovery and fail fast when both tools are
  unavailable.
