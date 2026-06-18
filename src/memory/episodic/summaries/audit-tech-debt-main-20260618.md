---
id: audit-tech-debt-main-20260618
title: Audit BioETL technical debt on main
task_id: audit-tech-debt-main-20260618
created_at: '2026-06-18T09:17:05Z'
ttl_days: 14
confidence: episodic
source_refs:
- AGENTS.md
summary: Audited BioETL main technical debt against canonical HEAD/GitHub main. Confirmed
  transition compatibility debt is zero; active debt is concentrated in 13 sanctioned
  public entrypoints, runtime_builders fragmentation (44 files; 15 support, 4 policy,
  2 compat, 3 assembly, 9 builder), CLI explicit-registry bootstrap split, infrastructure
  config package-root facade, Pandera Python 3.14 compat seam, residual determinism
  compatibility (config_hash alias plus 17 date-only entities), 2 permanent config
  aliases, and 31 compatibility test files. Found no direct layer-leak matches in
  committed HEAD for domain/application/infrastructure/interfaces boundaries. Bronze
  fixture gaps are zero; deprecated gold contract registry inventory is empty; runtime
  UUID seams inventory is empty. Observability governance is strong with a passed
  runtime_cardinality_review artifact dated 2026-06-04, but freshness beyond stored
  artifact remains limited.
---

# Episodic summary

## Task

- Title: Audit BioETL technical debt on main

## Outcome

- Audited BioETL main technical debt against canonical HEAD/GitHub main. Confirmed transition compatibility debt is zero; active debt is concentrated in 13 sanctioned public entrypoints, runtime_builders fragmentation (44 files; 15 support, 4 policy, 2 compat, 3 assembly, 9 builder), CLI explicit-registry bootstrap split, infrastructure config package-root facade, Pandera Python 3.14 compat seam, residual determinism compatibility (config_hash alias plus 17 date-only entities), 2 permanent config aliases, and 31 compatibility test files. Found no direct layer-leak matches in committed HEAD for domain/application/infrastructure/interfaces boundaries. Bronze fixture gaps are zero; deprecated gold contract registry inventory is empty; runtime UUID seams inventory is empty. Observability governance is strong with a passed runtime_cardinality_review artifact dated 2026-06-04, but freshness beyond stored artifact remains limited.

## Lessons learned

- Replace with durable follow-up if needed
