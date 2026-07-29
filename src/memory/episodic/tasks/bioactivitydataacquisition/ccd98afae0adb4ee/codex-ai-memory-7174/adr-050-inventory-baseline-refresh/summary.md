---
record_id: adr-050-inventory-baseline-refresh
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 1662fb33039778948b567b7898f358f38092a7e3
branch: codex/ai-memory-7174
worktree_id: ccd98afae0adb4ee
task_id: adr-050-inventory-baseline-refresh
actor:
  runtime: unknown
  agent: memory-workflow
  model: null
created_at: '2026-07-29T17:00:32.273250+00:00'
source_refs:
- <add-source-ref>
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: e92c9196284b74e8b04a87798ecdcb0d0c47416d9c8341aa8465882ce757565c
id: adr-050-inventory-baseline-refresh
title: Refresh ADR-050 silver-filter inventory baselines
ttl_days: 14
confidence: episodic
summary: Regenerated the ADR-050 CSV/JSON/Markdown inventory baselines. The only semantic
  drift was the first_line anchor for the Silver filter rejection metric moving from
  616 to 617. Inventory and config invariant suites pass; no budgets changed.
---

# Episodic summary

## Task

- Title: Refresh ADR-050 silver-filter inventory baselines

## Outcome

- Regenerated the ADR-050 CSV/JSON/Markdown inventory baselines. The only semantic drift was the first_line anchor for the Silver filter rejection metric moving from 616 to 617. Inventory and config invariant suites pass; no budgets changed.

## Lessons learned

- Replace with durable follow-up if needed
