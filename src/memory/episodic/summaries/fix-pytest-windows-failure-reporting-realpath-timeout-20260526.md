---
id: fix-pytest-windows-failure-reporting-realpath-timeout-20260526
title: Fix pytest Windows failure reporting realpath timeout
task_id: fix-pytest-windows-failure-reporting-realpath-timeout-20260526
created_at: '2026-05-26T04:43:31Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/conftest.py
- tests/unit/tools/test_pytest_last_failed_policy.py
summary: Added a Windows/PyCharm pytest configuration guard that forces traceback
  style to line for JetBrains-hosted pytest runs unless an already safe line/no style
  is set. This avoids pytest short/long failure formatting, which calls inspect.findsource
  and ntpath.realpath and can hang on Windows Google Drive-backed worktrees while
  reporting a failed test. Added unit regressions for PYCHARM_HOSTED and _jb_pytest_runner.py
  detection.
---

# Episodic summary

## Task

- Title: Fix pytest Windows failure reporting realpath timeout

## Outcome

- Added a Windows/PyCharm pytest configuration guard that forces traceback style to line for JetBrains-hosted pytest runs unless an already safe line/no style is set. This avoids pytest short/long failure formatting, which calls inspect.findsource and ntpath.realpath and can hang on Windows Google Drive-backed worktrees while reporting a failed test. Added unit regressions for PYCHARM_HOSTED and _jb_pytest_runner.py detection.

## Lessons learned

- For Windows/PyCharm runs on Google Drive-backed worktrees, pytest traceback
  formatting can be the timeout source after the test already failed. Avoid
  `short`/`long` traceback styles there because they resolve source locations via
  `inspect.findsource` and `ntpath.realpath`.
