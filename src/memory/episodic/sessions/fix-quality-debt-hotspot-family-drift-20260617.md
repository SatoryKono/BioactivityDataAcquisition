---
id: fix-quality-debt-hotspot-family-drift-20260617
title: Fix quality debt hotspot family drift
task_id: fix-quality-debt-hotspot-family-drift-20260617
created_at: '2026-06-17T13:00:43Z'
ttl_days: 14
confidence: episodic
source_refs:
- configs/quality/debt_scorecard.yaml
- reports/quality/hotspot-family-baseline.json
- tests/architecture/test_quality_debt_scorecard.py
summary: Active task session context.
query: test_quality_debt_scorecard hotspot_family_ratchets application_core total_loc
  files_ge_250_loc debt_scorecard hotspot-family-baseline
---

# Session note

## Task

- Title: Fix quality debt hotspot family drift
- Retrieval query: test_quality_debt_scorecard hotspot_family_ratchets application_core total_loc files_ge_250_loc debt_scorecard hotspot-family-baseline

## Retrieved context

- Catalog hits: 0
- RAG hits: 0
- Timeline hits: 0

## Working notes

- Replace with current findings
