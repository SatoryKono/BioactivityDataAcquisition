---
id: fix-test-structural-debt-200-loc
title: Fix oversized test function in quality integral gate tests
task_id: fix-test-structural-debt-200-loc
created_at: '2026-06-16T12:37:47Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/scripts/ci/test_quality_integral_gate.py
summary: Split oversized debt-governance quality-gate test into two focused tests
  with shared builders so structural debt guard passes without changing assertions.
---

# Episodic summary

## Task

- Title: Fix oversized test function in quality integral gate tests

## Outcome

- Split oversized debt-governance quality-gate test into two focused tests with shared builders so structural debt guard passes without changing assertions.

## Lessons learned

- Replace with durable follow-up if needed
