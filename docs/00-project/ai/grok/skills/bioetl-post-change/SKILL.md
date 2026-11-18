---
name: bioetl-post-change
description: Run BioETL post-change validation after edits — mirrors, inventory hashes, focused tests. Use after write-capable work, before PR/closeout, or /bioetl-post-change.
---

# BioETL post-change validation

Policy: `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`.
This skill selects that policy. It does not restate the checklist.

## When to use

- After any write-capable task on BioETL
- Before opening a PR or closing issues
- After edits under runtime trees or `src/bioetl/**`

## Steps

1. Follow `POST_CHANGE_VALIDATION.md` for the surfaces actually touched.
2. Report checks run, checks skipped, and mirror-sync status.
