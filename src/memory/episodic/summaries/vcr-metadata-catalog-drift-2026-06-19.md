---
id: vcr-metadata-catalog-drift-2026-06-19
title: Fix VCR metadata catalog drift
task_id: vcr-metadata-catalog-drift-2026-06-19
created_at: '2026-06-19T08:28:10Z'
ttl_days: 14
confidence: episodic
source_refs:
- scripts/engineering/qa/report_vcr_metadata_catalog.py
summary: Hardened VCR metadata catalog Python fallback scan to prefer longest overlapping
  tokens, eliminating Windows-only reachability drift for generic cassette stems.
---

# Episodic summary

## Task

- Title: Fix VCR metadata catalog drift

## Outcome

- Hardened VCR metadata catalog Python fallback scan to prefer longest overlapping tokens, eliminating Windows-only reachability drift for generic cassette stems.

## Lessons learned

- Replace with durable follow-up if needed
