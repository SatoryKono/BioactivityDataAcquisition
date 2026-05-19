---
id: fix-advanced-scenarios-vcr-limit-envelope
title: Pin advanced scenario ChEMBL seed to cassette-backed limit
task_id: fix-advanced-scenarios-vcr-limit-envelope
created_at: '2026-05-18T18:45:06Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/e2e/test_advanced_scenarios_e2e.py
summary: Pinned advanced ChEMBL activity seed helper to cassette-backed limit=3 so
  advanced e2e scenarios skip cleanly instead of failing on VCR mismatches under record
  mode none.
---

# Episodic summary

## Task

- Title: Pin advanced scenario ChEMBL seed to cassette-backed limit

## Outcome

- Pinned advanced ChEMBL activity seed helper to cassette-backed limit=3 so advanced e2e scenarios skip cleanly instead of failing on VCR mismatches under record mode none.

## Lessons learned

- Replace with durable follow-up if needed
