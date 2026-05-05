---
id: sonar-duplications-reduction-wave-2
title: Reduce Sonar duplications wave 2
task_id: sonar-duplications-reduction-wave-2
created_at: '2026-05-05T08:59:21Z'
ttl_days: 14
confidence: episodic
source_refs:
- docs/00-project/ai/memory/memory-py-architecture-debt-bot.md
summary: Replaced repeated CompositeRunnerDependencies/CompositePipelineRunner setup
  in runner FSM suites with runner_test_support.create_runner, fixed create_runner
  run_id consistency, and collapsed repeated RecordProcessorConfig/gold-validator
  boilerplate into test helpers while keeping targeted pytest suites green.
---

# Episodic summary

## Task

- Title: Reduce Sonar duplications wave 2

## Outcome

- Replaced repeated CompositeRunnerDependencies/CompositePipelineRunner setup in runner FSM suites with runner_test_support.create_runner, fixed create_runner run_id consistency, and collapsed repeated RecordProcessorConfig/gold-validator boilerplate into test helpers while keeping targeted pytest suites green.

## Lessons learned

- Replace with durable follow-up if needed
