---
id: fix-application-services-lazy-facade-windows-scanner-fallback-20260526
title: Fix application services lazy facade Windows scanner fallback
task_id: fix-application-services-lazy-facade-windows-scanner-fallback-20260526
created_at: '2026-05-26T03:45:19Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_application_services_lazy_facade_governance.py
summary: Updated application-services lazy facade governance scan to avoid unbounded
  in-process file reads. Candidate discovery now uses bounded rg, bounded git grep
  with common Windows Git paths, and a bounded Python subprocess fallback when external
  scanners are unavailable. Candidate source reads are also isolated in subprocesses
  so slow Windows/GDrive file I/O cannot hang the pytest main thread.
---

# Episodic summary

## Task

- Title: Fix application services lazy facade Windows scanner fallback

## Outcome

- Updated application-services lazy facade governance scan to avoid unbounded in-process file reads. Candidate discovery now uses bounded rg, bounded git grep with common Windows Git paths, and a bounded Python subprocess fallback when external scanners are unavailable. Candidate source reads are also isolated in subprocesses so slow Windows/GDrive file I/O cannot hang the pytest main thread.

## Lessons learned

- Windows/PyCharm architecture scans on Google Drive-backed worktrees should
  prefer bounded external scanners and isolate any Python file reads in child
  processes; thread-based timeouts do not stop a blocked `Path.read_text`.
