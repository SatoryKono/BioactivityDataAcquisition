---
id: docs-audit-main-2026-06-16
title: Audit documentation on main and prepare GitHub issues
task_id: docs-audit-main-2026-06-16
created_at: '2026-06-16T06:55:11Z'
ttl_days: 14
confidence: episodic
source_refs:
- AGENTS.md
- README.md
- mkdocs.yml
- reports/docs-audit/2026-06-16-summary.md
- reports/github_issue_drafts/2026-06-16-documentation-audit-main-issues.md
summary: Active task session context.
query: documentation audit drift README dashboard dq contracts main
---

# Session note

## Task

- Title: Audit documentation on main and prepare GitHub issues
- Retrieval query: documentation audit drift README dashboard dq contracts main

## Retrieved context

- Catalog hits: 0
- RAG hits: 0
- Timeline hits: 0

## Working notes

- Revalidated the user-supplied audit against the current `main` worktree.
- Confirmed the previously reported README drift is already resolved on `main`.
- Confirmed dashboard-guide routing drift is resolved: inventory and panel pages
  now exist and are in `mkdocs.yml`.
- Confirmed DQ contract routing drift is resolved in the active published
  contract pack.
- Found two remaining live issues:
  1. active guides still reference nonexistent make targets
     (`docs-build`, `docs-serve`, `setup-dev`, `test-deps-dev`);
  2. published engineering coverage docs still track retired
     `src/bioetl/composition/services_api.py`.
- GitHub connector issue lookup failed with bad credentials, so issue creation
  was replaced by local draft artifacts.
