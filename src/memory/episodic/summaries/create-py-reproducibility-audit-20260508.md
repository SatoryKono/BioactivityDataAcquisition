---
id: create-py-reproducibility-audit-20260508
title: Create py-reproducibility-audit skill
task_id: create-py-reproducibility-audit-20260508
created_at: '2026-05-08T16:33:20Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: 'Created a new project-local skill .codex/skills/py-reproducibility-audit
  for BioETL reproducibility audits and GitHub issue design. The skill uses a concise
  SKILL.md plus two references: one for the audit baseline and one for issue-creation
  rules. init_skill.py was attempted first but failed to create files on this path
  with a read-only filesystem error, so the final skill was created manually and validated
  with quick_validate.py.'
---

# Episodic summary

## Task

- Title: Create py-reproducibility-audit skill

## Outcome

- Created a new project-local skill .codex/skills/py-reproducibility-audit for BioETL reproducibility audits and GitHub issue design. The skill uses a concise SKILL.md plus two references: one for the audit baseline and one for issue-creation rules. init_skill.py was attempted first but failed to create files on this path with a read-only filesystem error, so the final skill was created manually and validated with quick_validate.py.

## Lessons learned

- Replace with durable follow-up if needed
