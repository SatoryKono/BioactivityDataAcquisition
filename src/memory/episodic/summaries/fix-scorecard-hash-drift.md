---
id: fix-scorecard-hash-drift
title: Fix scorecard coverage evidence hash drift
task_id: fix-scorecard-hash-drift
created_at: '2026-06-19T18:02:39Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_vcr_metadata_inventory.py
summary: Resolved remaining targeted guard failures by making composition.bootstrap.__all__
  a literal frozen surface, routing split composite config imports through bioetl.domain.composite.config,
  regenerating ADR-050 silver filter inventory baselines, refreshing VCR metadata
  catalog, and updating managed VCR provider counts in test_matrix.yaml. Targeted
  architecture guards now pass without xdist.
---

# Episodic summary

## Task

- Title: Fix scorecard coverage evidence hash drift

## Outcome

- Resolved remaining targeted guard failures by making composition.bootstrap.__all__ a literal frozen surface, routing split composite config imports through bioetl.domain.composite.config, regenerating ADR-050 silver filter inventory baselines, refreshing VCR metadata catalog, and updating managed VCR provider counts in test_matrix.yaml. Targeted architecture guards now pass without xdist.

## Lessons learned

- Replace with durable follow-up if needed
