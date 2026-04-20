---
Version: 1.0.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-04-20'
---

# Root Status Artifacts Archive

This folder stores historical root-level status, recovery, sync, and wave
summary markdown artifacts that no longer belong in the repository root.

It also stores fixed-state setup notes that were previously committed as
one-off root deployment memos.

## Purpose

- preserve historical context for setup waves and bounded cleanup work;
- keep old links and forensic context available without treating these files as
  current root entrypoints;
- prevent the repository root from becoming a storage surface for one-off
  completion notes.

## Usage rules

- Treat files here as historical context, not active documentation.
- Prefer `docs/05-operations/` for active runbooks and quick references.
- Prefer `docs/plans/` for active planning artifacts.
- Prefer canonical root files like `README.md` and `CHANGELOG.md` for
  repository entrypoint content.
