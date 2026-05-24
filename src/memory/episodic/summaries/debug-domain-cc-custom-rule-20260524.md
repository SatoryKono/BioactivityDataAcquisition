---
id: debug-domain-cc-custom-rule-20260524
title: Fix domain complexity failure in _custom_rule_violated
task_id: debug-domain-cc-custom-rule-20260524
created_at: '2026-05-24T13:04:57Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/domain/behavior/_dq_rule_evaluators.py
summary: Reduced _custom_rule_violated cyclomatic complexity via special-validator
  dispatch table without changing DQ behavior.
---

# Episodic summary

## Task

- Title: Fix domain complexity failure in _custom_rule_violated

## Outcome

- Reduced _custom_rule_violated cyclomatic complexity via special-validator dispatch table without changing DQ behavior.

## Lessons learned

- Replace with durable follow-up if needed
