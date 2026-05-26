---
id: fix-application-services-lazy-facade-subprocess-reader-timeout-20260526
title: Fix application services lazy facade subprocess reader timeout
task_id: fix-application-services-lazy-facade-subprocess-reader-timeout-20260526
created_at: '2026-05-26T03:58:27Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_application_services_lazy_facade_governance.py
summary: Removed Windows subprocess pipe captures from the application-services lazy
  facade governance scanner. All child process stdout now writes to a temporary file
  with stderr redirected to DEVNULL, preventing subprocess.communicate reader threads
  from hanging PyCharm/faulthandler while preserving bounded timeouts for rg, git
  grep, Python fallback scans, and candidate source reads.
---

# Episodic summary

## Task

- Title: Fix application services lazy facade subprocess reader timeout

## Outcome

- Removed Windows subprocess pipe captures from the application-services lazy facade governance scanner. All child process stdout now writes to a temporary file with stderr redirected to DEVNULL, preventing subprocess.communicate reader threads from hanging PyCharm/faulthandler while preserving bounded timeouts for rg, git grep, Python fallback scans, and candidate source reads.

## Lessons learned

- On Windows, `subprocess.run(..., capture_output=True)` can leave
  `subprocess._readerthread` frames visible to PyCharm timeouts; architecture
  tests that shell out should redirect stdout to a file when bounded output is
  needed.
