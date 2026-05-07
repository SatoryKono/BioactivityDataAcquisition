---
id: fix-dq-visual-semantics-20260507
title: Fix DQ dashboard visual semantics thresholds
task_id: fix-dq-visual-semantics-20260507
created_at: '2026-05-07T15:42:09Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Fixed bioetl-dq-v2 first-screen severity thresholds for Monitor DQ Current
  Status and Monitor DQ Threshold State to use canonical green/orange/red 0/1/2 steps.
  Added regression coverage in test_grafana_dashboard_metric_semantics.py. Also resolved
  a pre-existing duplicate JSON key dataLinks in DQ panel id=116 so strict JSON config
  validation passes again. JSON validation, visual semantics check, targeted DQ metric
  semantics tests, DQ grafana config tests, and dashboard inventory parity all passed.
---

# Episodic summary

## Task

- Title: Fix DQ dashboard visual semantics thresholds

## Outcome

- Fixed bioetl-dq-v2 first-screen severity thresholds for Monitor DQ Current Status and Monitor DQ Threshold State to use canonical green/orange/red 0/1/2 steps. Added regression coverage in test_grafana_dashboard_metric_semantics.py. Also resolved a pre-existing duplicate JSON key dataLinks in DQ panel id=116 so strict JSON config validation passes again. JSON validation, visual semantics check, targeted DQ metric semantics tests, DQ grafana config tests, and dashboard inventory parity all passed.

## Lessons learned

- Replace with durable follow-up if needed
