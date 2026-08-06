---
record_id: dashboard-source-origin-guard-20260806
record_type: working
repo_id: bioactivitydataacquisition
git_commit: b16050337eb1890ead331e64ea40e3e080f9f4ed
branch: agent/stream1-edge-http-crossref-security
worktree_id: b5393af69d37a674
task_id: dashboard-source-origin-guard-20260806
actor:
  runtime: codex
  agent: py-config-bot
  model: null
created_at: '2026-08-06T07:17:23.970568+00:00'
source_refs:
- reports/codex/review_py-config-bot_20260806_1010.md
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 26337ebd2c815ecb2092c8cdd9e9076c1caead8c7ce7a4dc4d9918df72d76d08
id: dashboard-source-origin-guard-20260806
title: Exclude stale checkout from dashboard data plane
ttl_days: 14
confidence: episodic
summary: Implemented and deployed a managed dashboard source identity, exact data/report
  bind checks, Grafana fail-closed bootstrap, Ops HTTP identity exposure, cutover-helper
  hardening, documentation, and regression coverage. Live main and monitoring now
  originate from E:\github\BioactivityDataAcquisition; new 2026-08-06 run IDs are
  visible.
---

# Episodic summary

## Task

- Title: Exclude stale checkout from dashboard data plane

## Outcome

- Implemented and deployed a managed dashboard source identity, exact data/report bind checks, Grafana fail-closed bootstrap, Ops HTTP identity exposure, cutover-helper hardening, documentation, and regression coverage. Live main and monitoring now originate from E:\github\BioactivityDataAcquisition; new 2026-08-06 run IDs are visible.

## Lessons learned

- Replace with durable follow-up if needed
