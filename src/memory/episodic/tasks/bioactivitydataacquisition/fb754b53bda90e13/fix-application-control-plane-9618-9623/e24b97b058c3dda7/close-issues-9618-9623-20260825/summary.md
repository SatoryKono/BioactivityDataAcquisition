---
record_id: close-issues-9618-9623-20260825
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 1ccb863c8f14358867ea6ba5827d7a86c097d0c8
branch: fix/application-control-plane-9618-9623
worktree_id: fb754b53bda90e13
task_id: close-issues-9618-9623-20260825
actor:
  runtime: codex
  agent: root
  model: gpt-5
created_at: '2026-08-25T17:05:13.983638+00:00'
source_refs:
- fix/application-control-plane-9618-9623
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 433cb0bbe73c716b2d23ac766621aec98f1d6ac06e9a422cab1243f959931b4f
id: close-issues-9618-9623-20260825
title: Close application issues 9618 and 9623
ttl_days: 14
confidence: episodic
summary: 'Rehomed nine workflow execution state-transition modules from application.services.control_plane.workflow
  to application.services.workflow.control_plane; retained lazy WorkflowExecutionService
  compatibility facade; updated production importers, tests, docs, coverage/import/dependency/source/scorecard
  artifacts; added six shrink-only forbidden cross-subdomain import pairs and AST
  architecture guard for issue 9623. Canonical metrics: application_services_control_plane
  files 142->133, LOC 16438->15077 (-8.28%), helper ratio 0.402->0.374, budgets unchanged.
  Focused regression 168 passed, Import Linter 6/6 kept, docs checks green; full architecture
  local run timed out at 10m without failure output, with GitHub CI required before
  merge.'
---

# Episodic summary

## Task

- Title: Close application issues 9618 and 9623

## Outcome

- Rehomed nine workflow execution state-transition modules from application.services.control_plane.workflow to application.services.workflow.control_plane; retained lazy WorkflowExecutionService compatibility facade; updated production importers, tests, docs, coverage/import/dependency/source/scorecard artifacts; added six shrink-only forbidden cross-subdomain import pairs and AST architecture guard for issue 9623. Canonical metrics: application_services_control_plane files 142->133, LOC 16438->15077 (-8.28%), helper ratio 0.402->0.374, budgets unchanged. Focused regression 168 passed, Import Linter 6/6 kept, docs checks green; full architecture local run timed out at 10m without failure output, with GitHub CI required before merge.

## Lessons learned

- Replace with durable follow-up if needed
