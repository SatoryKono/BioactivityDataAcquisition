---
id: shrink-cli-config-bootstrap-seam
title: Shrink bootstrap cli config seam
task_id: shrink-cli-config-bootstrap-seam
created_at: '2026-05-21T09:49:31Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/bootstrap/cli/config.py
summary: Compressed composition bootstrap CLI config seam to 59 lines and restored
  a direct pipeline_config_api import via a local loader wrapper, satisfying the RF-014
  line-budget and helper-owner guardrail without changing the public patch seam.
---

# Episodic summary

## Task

- Title: Shrink bootstrap cli config seam

## Outcome

- Compressed composition bootstrap CLI config seam to 59 lines and restored a direct pipeline_config_api import via a local loader wrapper, satisfying the RF-014 line-budget and helper-owner guardrail without changing the public patch seam.

## Lessons learned

- Replace with durable follow-up if needed
