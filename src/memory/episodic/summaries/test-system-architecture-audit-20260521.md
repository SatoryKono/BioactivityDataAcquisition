---
id: test-system-architecture-audit-20260521
title: BioETL test system architecture audit
task_id: test-system-architecture-audit-20260521
created_at: '2026-05-21T15:46:13Z'
ttl_days: 14
confidence: episodic
source_refs:
- configs/quality/test_governance_audit.yaml
- configs/quality/test_matrix.yaml
- configs/quality/test_telemetry_baseline.yaml
- reports/quality/module-coverage-inventory.json
- tests/architecture/test_test_governance_audit.py
summary: 'Completed read-only architecture-strict audit of BioETL test system on main/aec237206234.
  Findings: strong lane governance and invariant coverage exist; main risks are stale
  module coverage inventory without coverage.xml, 479 weak-no-value tests, 2742 duplicate-name
  occurrences, 56 compatibility/legacy test files, heavy architecture scanners/top
  slow tests, high unit repo I/O surface, and deterministic identity debt from 413
  uuid4 call sites.'
---

# Episodic summary

## Task

- Title: BioETL test system architecture audit

## Outcome

- Completed read-only architecture-strict audit of BioETL test system on main/aec237206234. Findings: strong lane governance and invariant coverage exist; main risks are stale module coverage inventory without coverage.xml, 479 weak-no-value tests, 2742 duplicate-name occurrences, 56 compatibility/legacy test files, heavy architecture scanners/top slow tests, high unit repo I/O surface, and deterministic identity debt from 413 uuid4 call sites.

## Lessons learned

- Replace with durable follow-up if needed
