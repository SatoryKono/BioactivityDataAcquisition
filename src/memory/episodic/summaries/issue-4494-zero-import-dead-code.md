---
id: issue-4494-zero-import-dead-code
title: "Issue 4494 zero-import inventory \u0438 freshness triage \u0434\u043B\u044F\
  \ dead code"
task_id: issue-4494-zero-import-dead-code
created_at: '2026-05-22T08:50:34Z'
ttl_days: 14
confidence: episodic
source_refs:
- AGENTS.md
- configs/quality/retirement_candidate_triage.yaml
- scripts/engineering/qa/report_dead_code_inventory.py
summary: 'Bound dead-code inventory freshness to issue #4494 by adding review-window
  metadata, stale check enforcement in report_dead_code_inventory --check, architecture/unit
  coverage, and a tighter zero-import budget of 40 based on the regenerated inventory.'
---

# Episodic summary

## Task

- Title: Issue 4494 zero-import inventory и freshness triage для dead code

## Outcome

- Bound dead-code inventory freshness to issue #4494 by adding review-window metadata, stale check enforcement in report_dead_code_inventory --check, architecture/unit coverage, and a tighter zero-import budget of 40 based on the regenerated inventory.

## Lessons learned

- Replace with durable follow-up if needed
