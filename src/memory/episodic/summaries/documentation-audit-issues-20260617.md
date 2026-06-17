---
id: documentation-audit-issues-20260617
title: Verify documentation audit and prepare GitHub issues
task_id: documentation-audit-issues-20260617
created_at: '2026-06-17T10:06:32Z'
ttl_days: 14
confidence: episodic
source_refs:
- docs/02-architecture/00-overview.md
- mkdocs.yml
- docs/04-reference/pipeline-catalog.md
- docs/04-reference/pipelines/INDEX.md
- docs/03-guides/testing.md
- docs/05-operations/deployment/README.md
- docs/03-guides/workflows.md
- https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5285
- https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5286
summary: 'Verified the provided 2026-06-17 documentation audit against live repo.
  Confirmed ADR documentation drift: 50 ADR files exist and ADR-050 is present in
  decisions/registry/enforcement artifacts, while docs/02-architecture/00-overview.md
  still says 49 ADRs and mkdocs.yml ADR nav stops at ADR-049. Confirmed pipeline docs
  issue should be narrowed to uneven per-pipeline operational facet coverage, not
  missing pipeline catalog/specs. Marked README/CLI version conflict, testing reference
  absence, deployment index absence, workflow backlog-noise, and dashboard inventory
  drift as not currently reproduced. Created GitHub issues #5285 and #5286 for the
  confirmed remediation work. gh CLI token is invalid in Windows gh, so GitHub connector
  was used for issue creation and public REST/curl for read-only verification.'
---

# Episodic summary

## Task

- Title: Verify documentation audit and prepare GitHub issues

## Outcome

- Verified the provided 2026-06-17 documentation audit against live repo. Confirmed ADR documentation drift: 50 ADR files exist and ADR-050 is present in decisions/registry/enforcement artifacts, while docs/02-architecture/00-overview.md still says 49 ADRs and mkdocs.yml ADR nav stops at ADR-049. Confirmed pipeline docs issue should be narrowed to uneven per-pipeline operational facet coverage, not missing pipeline catalog/specs. Marked README/CLI version conflict, testing reference absence, deployment index absence, workflow backlog-noise, and dashboard inventory drift as not currently reproduced. Created GitHub issues #5285 and #5286 for the confirmed remediation work. gh CLI token is invalid in Windows gh, so GitHub connector was used for issue creation and public REST/curl for read-only verification.

## Lessons learned

- Replace with durable follow-up if needed
