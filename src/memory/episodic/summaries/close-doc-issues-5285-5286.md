---
id: close-doc-issues-5285-5286
title: Close documentation issues 5285 and 5286
task_id: close-doc-issues-5285-5286
created_at: '2026-06-17T10:27:05Z'
ttl_days: 14
confidence: episodic
source_refs:
- docs/02-architecture/00-overview.md
- mkdocs.yml
- docs/04-reference/pipeline-catalog.md
- docs/04-reference/pipelines/README.md
- docs/04-reference/pipelines/INDEX.md
- https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5285
- https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5286
summary: 'Synced ADR-050 into docs/02-architecture/00-overview.md and mkdocs.yml;
  added normalized pipeline operational coverage surface in docs/04-reference/pipelines/INDEX.md
  with catalog/README links; validated docs links/configs/specs and runtime mirror/freshness
  drift; closed GitHub issues #5285 and #5286 as completed. MkDocs strict build could
  not be completed locally: .venv lacks mkdocs and uv --extra docs hung after dependency
  resolution when run with escalation.'
---

# Episodic summary

## Task

- Title: Close documentation issues 5285 and 5286

## Outcome

- Synced ADR-050 into docs/02-architecture/00-overview.md and mkdocs.yml; added normalized pipeline operational coverage surface in docs/04-reference/pipelines/INDEX.md with catalog/README links; validated docs links/configs/specs and runtime mirror/freshness drift; closed GitHub issues #5285 and #5286 as completed. MkDocs strict build could not be completed locally: .venv lacks mkdocs and uv --extra docs hung after dependency resolution when run with escalation.

## Lessons learned

- Replace with durable follow-up if needed
