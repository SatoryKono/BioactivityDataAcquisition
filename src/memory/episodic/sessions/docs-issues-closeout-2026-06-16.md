---
id: docs-issues-closeout-2026-06-16
title: Resolve documentation audit issues
task_id: docs-issues-closeout-2026-06-16
created_at: '2026-06-16T07:47:09Z'
ttl_days: 14
confidence: episodic
source_refs:
- reports/github_issue_drafts/2026-06-16-documentation-audit-main-issues.md
- reports/docs-audit/2026-06-16-summary.md
- docs/03-guides/testing.md
- docs/05-engineering/test_coverage_issues.md
summary: Active task session context.
query: docs issues closeout make docs-build docs-serve setup-dev test-deps-dev services_api
---

# Session note

## Task

- Title: Resolve documentation audit issues
- Retrieval query: docs issues closeout make docs-build docs-serve setup-dev test-deps-dev services_api

## Retrieved context

- Catalog hits: 0
- RAG hits: 0
- Timeline hits: 0

## Working notes

- Removed stale references to nonexistent make targets from active docs and one
  active AI runtime guide.
- Replaced docs/testing setup wording with the supported flow:
  `make install`, `make test-deps`, `make setup-plugins`, `make lint`, and
  `uv run python -m scripts.docs build-site`.
- Converted `services_api.py` in published engineering coverage docs from a
  live coverage target into a retired-target note and removed it from the
  roadmap list.
- Validation passed:
  `python3 -m scripts.docs check-links --links --specs --configs`,
  `python3 -m scripts.docs check-drift --ports --classes`,
  `python3 -m scripts.docs check-drift --runtime-mirrors --freshness`.
