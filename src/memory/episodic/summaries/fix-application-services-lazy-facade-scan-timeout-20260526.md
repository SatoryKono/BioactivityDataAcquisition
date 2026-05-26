---
id: fix-application-services-lazy-facade-scan-timeout-20260526
title: Fix application services lazy facade scan timeout
task_id: fix-application-services-lazy-facade-scan-timeout-20260526
created_at: '2026-05-26T03:31:49Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_application_services_lazy_facade_governance.py
summary: Replaced the architecture scanner fallback that read every Python file with
  bounded git-grep/rg candidate discovery and subprocess-bounded candidate reads;
  Windows pytest now collects and passes the application-services lazy facade governance
  tests without hanging on Path.read_text.
---

# Episodic summary

## Task

- Title: Fix application services lazy facade scan timeout

## Outcome

- Replaced the architecture scanner fallback that read every Python file with bounded git-grep/rg candidate discovery and subprocess-bounded candidate reads; Windows pytest now collects and passes the application-services lazy facade governance tests without hanging on Path.read_text.

## Lessons learned

- Architecture scanners running under Windows/GDrive should avoid thread-wrapped
  `Path.read_text()` over whole source trees; use bounded grep candidate
  discovery and process-bounded reads for exact parsing.
