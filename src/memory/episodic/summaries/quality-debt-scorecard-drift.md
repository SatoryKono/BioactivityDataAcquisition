---
id: quality-debt-scorecard-drift
title: Fix quality debt scorecard hotspot family metric drift
task_id: QUALITY-DEBT-SCORECARD-DRIFT
created_at: '2026-06-18T10:42:26Z'
ttl_days: 14
confidence: episodic
source_refs:
- configs/quality/debt_scorecard.yaml
summary: 'Resolved test_quality_debt_scorecard hotspot family metric drift by aligning
  application_core hotspot_family_ratchets metrics in configs/quality/debt_scorecard.yaml
  with the committed/generated hotspot-family baseline: total_loc=22207 and helper_function_ratio=0.35.
  Regenerated hotspot-family baseline artifacts with report-family-baseline and validated
  YAML load, baseline check, targeted failing test, and full test_quality_debt_scorecard.py.'
---

# Episodic summary

## Task

- Title: Fix quality debt scorecard hotspot family metric drift

## Outcome

- Resolved test_quality_debt_scorecard hotspot family metric drift by aligning application_core hotspot_family_ratchets metrics in configs/quality/debt_scorecard.yaml with the committed/generated hotspot-family baseline: total_loc=22207 and helper_function_ratio=0.35. Regenerated hotspot-family baseline artifacts with report-family-baseline and validated YAML load, baseline check, targeted failing test, and full test_quality_debt_scorecard.py.

## Lessons learned

- Replace with durable follow-up if needed
