---
record_id: dash-dedupe-02eeaf066f
record_type: working
repo_id: bioactivitydataacquisition
git_commit: bc814f0c435c809529761f41108ba8e742ec3211
branch: main
worktree_id: 7360d78d97884e9f
task_id: dash-dedupe-02eeaf066f
actor:
  runtime: grok
  agent: grok-4.6
  model: null
created_at: '2026-08-20T19:19:51.112231+00:00'
source_refs:
- <add-source-ref>
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 8db37f0c031094211e67a1f5a8a16e8910b4ba8cf4dbe07013fd2da959a0c55f
id: dash-dedupe-02eeaf066f
title: Dashboard intra-UID data duplication audit 0-6
ttl_days: 14
confidence: episodic
summary: 'Audited 7 shipped UIDs. Only same-row-subset: Run Explorer 9403 vs 3023.
  surface_score=1. Reports in reports/audit/grafana-panels/data-duplication/. ALLOW_ISSUE_WRITE=false.'
---

# Episodic summary

## Task

- Title: Dashboard intra-UID data duplication audit 0-6

## Outcome

- Audited 7 shipped UIDs. Only same-row-subset: Run Explorer 9403 vs 3023. surface_score=1. Reports in reports/audit/grafana-panels/data-duplication/. ALLOW_ISSUE_WRITE=false.

## Lessons learned

- Replace with durable follow-up if needed
