---
id: github-issue-closeability-check
title: Check which open GitHub issues can be closed
task_id: github-issue-closeability-check
created_at: '2026-05-21T14:43:10Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: 'Reviewed 9 open GitHub issues against issue DoD, local code/config/docs,
  GitHub API state, and targeted verification. Strong close candidates: #4420, #4423,
  #4427. Conditional candidate: #4419 has root-cause evidence and targeted/golden/integration
  config gates, but full unit config gate has unrelated failures. Do not close: #4421,
  #4422, #4424, #4425, #4439 based on remaining evidence/gate failures.'
---

# Episodic summary

## Task

- Title: Check which open GitHub issues can be closed

## Outcome

- Reviewed 9 open GitHub issues against issue DoD, local code/config/docs, GitHub API state, and targeted verification. Strong close candidates: #4420, #4423, #4427. Conditional candidate: #4419 has root-cause evidence and targeted/golden/integration config gates, but full unit config gate has unrelated failures. Do not close: #4421, #4422, #4424, #4425, #4439 based on remaining evidence/gate failures.

## Lessons learned

- Replace with durable follow-up if needed
