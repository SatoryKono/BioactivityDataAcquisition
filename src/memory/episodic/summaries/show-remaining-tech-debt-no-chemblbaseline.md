---
id: show-remaining-tech-debt-no-chemblbaseline
title: Show remaining technical debt tasks excluding ChemblBaseline
task_id: show-remaining-tech-debt-no-chemblbaseline
created_at: '2026-06-01T13:56:14Z'
ttl_days: 14
confidence: episodic
source_refs:
- user-request-remaining-tech-debt-no-chemblbaseline
summary: 'Queried open GitHub issues through API using .env token read-only. After
  excluding issue titles explicitly scoped to ChemblBaseline/baseline smoke, remaining
  non-ChemblBaseline technical-debt tasks are #4909, #4910, #4829, and #4830. Eight
  ChemblBaseline-scoped issues remain excluded per user request.'
---

# Episodic summary

## Task

- Title: Show remaining technical debt tasks excluding ChemblBaseline

## Outcome

- Queried open GitHub issues through API using .env token read-only. After excluding issue titles explicitly scoped to ChemblBaseline/baseline smoke, remaining non-ChemblBaseline technical-debt tasks are #4909, #4910, #4829, and #4830. Eight ChemblBaseline-scoped issues remain excluded per user request.

## Lessons learned

- Replace with durable follow-up if needed
