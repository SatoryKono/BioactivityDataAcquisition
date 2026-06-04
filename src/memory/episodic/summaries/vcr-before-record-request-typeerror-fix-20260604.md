---
id: vcr-before-record-request-typeerror-fix-20260604
title: Fix VCR before_record_request TypeError
task_id: vcr-before-record-request-typeerror-fix-20260604
created_at: '2026-06-04T15:35:53Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Replaced raw vcrpy filter_headers/filter_query_parameters config with a defensive
  repo-local before_record_request sanitizer in tests/helpers/vcr_config.py, and added
  unit regression coverage for malformed request surfaces. Verified unit tests plus
  multiple Windows VCR suites now pass.
---

# Episodic summary

## Task

- Title: Fix VCR before_record_request TypeError

## Outcome

- Replaced raw vcrpy filter_headers/filter_query_parameters config with a defensive repo-local before_record_request sanitizer in tests/helpers/vcr_config.py, and added unit regression coverage for malformed request surfaces. Verified unit tests plus multiple Windows VCR suites now pass.

## Lessons learned

- Replace with durable follow-up if needed
