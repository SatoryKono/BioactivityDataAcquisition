---
id: observability-audit-chembl-activity-20260508
title: Observability audit for chembl_activity workflow
task_id: observability-audit-chembl-activity-20260508
created_at: '2026-05-08T19:05:45Z'
ttl_days: 14
confidence: episodic
source_refs:
- AGENTS.md
summary: 'Ran chembl_activity workflow limit 10000; workflow_run_id ce953b90-ef43-475b-ae27-f8cff732bdeb;
  workflow manifest 6019f27e-010b-4e58-b3d0-f33d62d23cfb; pipeline run_id db8717c1-1129-4423-9118-bcab633a39c6;
  pipeline manifest 931f219f-8868-4a14-85e1-7d0e080fc980; success. Alias defects A-D
  did not reproduce. DQ warn semantics correct with dq_monitor_disabled plus silver_filter_rejects.
  Loki ingestion works; Tempo empty expected for NoOpTracing. Real defects: Runtime
  Error Rate panel empty despite denominator >20 due absent healthy-zero error numerator;
  Silver Reject Explorer backend broken (8081 reset, compose/health server contract
  issue); Workflow Run Outcomes / Range uses max_over_time on cumulative counter and
  falsely shows failed=1 while failed-range panel is 0.'
---

# Episodic summary

## Task

- Title: Observability audit for chembl_activity workflow

## Outcome

- Ran chembl_activity workflow limit 10000; workflow_run_id ce953b90-ef43-475b-ae27-f8cff732bdeb; workflow manifest 6019f27e-010b-4e58-b3d0-f33d62d23cfb; pipeline run_id db8717c1-1129-4423-9118-bcab633a39c6; pipeline manifest 931f219f-8868-4a14-85e1-7d0e080fc980; success. Alias defects A-D did not reproduce. DQ warn semantics correct with dq_monitor_disabled plus silver_filter_rejects. Loki ingestion works; Tempo empty expected for NoOpTracing. Real defects: Runtime Error Rate panel empty despite denominator >20 due absent healthy-zero error numerator; Silver Reject Explorer backend broken (8081 reset, compose/health server contract issue); Workflow Run Outcomes / Range uses max_over_time on cumulative counter and falsely shows failed=1 while failed-range panel is 0.

## Lessons learned

- Replace with durable follow-up if needed
