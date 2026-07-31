---
record_id: fix-research-workflow-frontmatter
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 7341ab109babf13a7b5460342250440bded2ec81
branch: main
worktree_id: ccd98afae0adb4ee
task_id: fix-research-workflow-frontmatter
actor:
  runtime: codex
  agent: root
  model: null
created_at: '2026-07-31T07:26:48.410573+00:00'
source_refs:
- .codex/skills/research-workflow/SKILL.md
- .codex/skills/research-workflow/agents/openai.yaml
- .codex/skills/collecting-evidence/SKILL.md
- tests/architecture/test_codex_skill_agent_links.py
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 76e6544aa9311d08d0fe0268adf70debece53ec04d2ab5bf7a8da898e7896296
id: fix-research-workflow-frontmatter
title: Fix research-workflow skill frontmatter
ttl_days: 14
confidence: episodic
summary: Split malformed research-workflow YAML frontmatter into quoted description,
  context, and agent fields across runtime peers; added required OpenAI metadata;
  restored active collecting-evidence skill referenced by orchestration; synchronized
  catalogs and docs mirrors. Full Codex skill-agent architecture suite and all parity/drift
  checks pass.
---

# Episodic summary

## Task

- Title: Fix research-workflow skill frontmatter

## Outcome

- Split malformed research-workflow YAML frontmatter into quoted description, context, and agent fields across runtime peers; added required OpenAI metadata; restored active collecting-evidence skill referenced by orchestration; synchronized catalogs and docs mirrors. Full Codex skill-agent architecture suite and all parity/drift checks pass.

## Lessons learned

- Replace with durable follow-up if needed
