---
id: test-system-audit-main
title: Audit BioETL test system on main
task_id: test-system-audit-main
created_at: '2026-06-19T16:24:49Z'
ttl_days: 14
confidence: episodic
source_refs:
- reports/quality/test-governance-current.json
summary: Audit found strong source coverage and invariant/contract coverage, but identified
  unit-lane routing drift for repo_backed tests, repo I/O leakage inside unit paths,
  weak VCR-backed integration tests with duplicate cassettes, repeated full E2E pipeline
  runs, synthetic Silver fallback in advanced E2E, and architecture scan tests dominating
  runtime.
---

# Episodic summary

## Task

- Title: Audit BioETL test system on main

## Outcome

- Audit found strong source coverage and invariant/contract coverage, but identified unit-lane routing drift for repo_backed tests, repo I/O leakage inside unit paths, weak VCR-backed integration tests with duplicate cassettes, repeated full E2E pipeline runs, synthetic Silver fallback in advanced E2E, and architecture scan tests dominating runtime.

## Lessons learned

- Replace with durable follow-up if needed
