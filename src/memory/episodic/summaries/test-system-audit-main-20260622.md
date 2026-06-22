---
id: test-system-audit-main-20260622
title: Audit BioETL test system on main
task_id: test-system-audit-main-20260622
created_at: '2026-06-22T09:16:05Z'
ttl_days: 14
confidence: episodic
source_refs:
- AGENTS.md
summary: 'Audited BioETL test system on main using repo artifacts and targeted scans.
  Evidence: 1812 test files across unit/integration/e2e/architecture/contract, 20907
  test functions, coverage baseline 92.81%, module inventory 2173 modules with 0 uncovered/unmeasured
  modules, contract matrix 27/27 Gold-enabled rows covered, VCR catalog 198 cassettes
  with 100% sidecars and 0 duplicate scenario stems, fixture duplicate inventory 0
  duplicate files, governance report 497 assertless candidates mostly intentional
  no-exception contracts, slow telemetry dominated by architecture subprocess/scanner
  tests, historical rollup shows drift-heavy flaky candidates. Main recommendations:
  keep architecture/replay guards, split slow governance from fast feedback, consolidate
  generated schema no-exception tests, remove/retire stale closeout ratchets, move
  module-scope temp roots out of pure unit import paths, and add/keep focused observability
  emission contracts.'
---

# Episodic summary

## Task

- Title: Audit BioETL test system on main

## Outcome

- Audited BioETL test system on main using repo artifacts and targeted scans. Evidence: 1812 test files across unit/integration/e2e/architecture/contract, 20907 test functions, coverage baseline 92.81%, module inventory 2173 modules with 0 uncovered/unmeasured modules, contract matrix 27/27 Gold-enabled rows covered, VCR catalog 198 cassettes with 100% sidecars and 0 duplicate scenario stems, fixture duplicate inventory 0 duplicate files, governance report 497 assertless candidates mostly intentional no-exception contracts, slow telemetry dominated by architecture subprocess/scanner tests, historical rollup shows drift-heavy flaky candidates. Main recommendations: keep architecture/replay guards, split slow governance from fast feedback, consolidate generated schema no-exception tests, remove/retire stale closeout ratchets, move module-scope temp roots out of pure unit import paths, and add/keep focused observability emission contracts.

## Lessons learned

- Replace with durable follow-up if needed
