______________________________________________________________________

id: task-aware-retrieval-profiles
title: Task-aware retrieval profiles
kind: domain_knowledge
source_refs:

- src/memory/query.py
- src/memory/DAILY_WORKFLOW.md
  confidence: curated
  last_verified: '2026-04-20T00:00:00Z'
  summary: Retrieval profiles should match the task type instead of using one generic search mode.

______________________________________________________________________

# Domain knowledge

## Concept

- The memory layer exposes retrieval profiles such as `architecture`, `implementation`, `operations`, and `audit` to bias ranking toward the most useful evidence for the current task.
- The same query string can surface different artifacts depending on whether the agent is tracing architecture, editing runtime code, or investigating an operational event.

## Practical implications

- Use `implementation` when changing code or configs, `operations` when investigating failures and runbooks, and `architecture` when reasoning about ADRs or structural boundaries.
- Keep retrieval profile choices explicit in agent workflows so that context gathering remains repeatable and reviewable.
