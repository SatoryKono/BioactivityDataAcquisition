---
record_id: docs-nav-growth-20260730
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 2d3166a86aa912b9794475a3dd6abf934c1fb0a0
branch: main
worktree_id: ccd98afae0adb4ee
task_id: docs-nav-growth-20260730
actor:
  runtime: unknown
  agent: memory-workflow
  model: null
created_at: '2026-07-30T06:11:03.793103+00:00'
source_refs:
- mkdocs.yml
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 034ea6657b41cb2f64e5967d9e7220776b857eb0ac35766aba328489f6a6779b
id: docs-nav-growth-20260730
title: Resolve docs outside mkdocs nav growth without raising baseline
ttl_days: 14
confidence: episodic
summary: Published the new pipeline passport projection guide and internal-published
  Codex task routing mirror in existing mkdocs nav sections. Not-in-nav returned from
  299 to the unchanged baseline 297. Guardrail tests, docs link/spec/config checks,
  runtime mirror drift, and diff check passed. mkdocs strict build was skipped because
  mkdocs is not installed in the active venv.
---

# Episodic summary

## Task

- Title: Resolve docs outside mkdocs nav growth without raising baseline

## Outcome

- Published the new pipeline passport projection guide and internal-published Codex task routing mirror in existing mkdocs nav sections. Not-in-nav returned from 299 to the unchanged baseline 297. Guardrail tests, docs link/spec/config checks, runtime mirror drift, and diff check passed. mkdocs strict build was skipped because mkdocs is not installed in the active venv.

## Lessons learned

- Replace with durable follow-up if needed
