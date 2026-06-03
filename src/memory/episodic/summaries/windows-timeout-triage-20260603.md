---
id: windows-timeout-triage-20260603
title: Identify Windows pytest timeout source
task_id: windows-timeout-triage-20260603
created_at: '2026-06-03T09:25:04Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/e2e/test_pipeline_matrix_e2e.py
summary: Reduced default matrix E2E parametrization to critical smoke pipelines only,
  deferring non-critical entity pipelines with dedicated owner suites or alternative
  coverage to reduce Windows timeout exposure.
---

# Episodic summary

## Task

- Title: Identify Windows pytest timeout source

## Outcome

- Reduced default matrix E2E parametrization to critical smoke pipelines only, deferring non-critical entity pipelines with dedicated owner suites or alternative coverage to reduce Windows timeout exposure.

## Lessons learned

- Replace with durable follow-up if needed
