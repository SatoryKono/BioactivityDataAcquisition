---
record_id: zed-architecture-fast-timeout-20260831
record_type: working
repo_id: bioactivitydataacquisition
git_commit: f2166217fc24c731e519a733fb34c318d74e5ceb
branch: fix/docs-ruleset-active-9800-20260831
worktree_id: 7360d78d97884e9f
task_id: zed-architecture-fast-timeout-20260831
actor:
  runtime: codex
  agent: py-test-bot
  model: null
created_at: '2026-08-31T17:21:21.986634+00:00'
source_refs:
- scripts/engineering/dev/zed_pytest_lane.py
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 2b817ea5746bacb5c9f79584d73121ca48f7ecbbae84ebe3783289c38ae35838
id: zed-architecture-fast-timeout-20260831
title: Fix Zed task concurrency and architecture drift
ttl_days: 14
confidence: episodic
summary: Diagnosed pytest repr_failure timeout as secondary to overlapping tasks and
  an external Grok task shell that force-killed every pytest process. Added per-checkout
  OS lock to zed_pytest_lane, set all Zed tasks hide=never, refreshed test-governance/flaky/telemetry
  artifacts without changing the 85 percent threshold, and validated lint plus focused
  and architecture-tail suites. A single uninterrupted full architecture-fast receipt
  remains unavailable because external task shells repeatedly terminated it.
---

# Episodic summary

## Task

- Title: Fix Zed task concurrency and architecture drift

## Outcome

- Diagnosed pytest repr_failure timeout as secondary to overlapping tasks and an external Grok task shell that force-killed every pytest process. Added per-checkout OS lock to zed_pytest_lane, set all Zed tasks hide=never, refreshed test-governance/flaky/telemetry artifacts without changing the 85 percent threshold, and validated lint plus focused and architecture-tail suites. A single uninterrupted full architecture-fast receipt remains unavailable because external task shells repeatedly terminated it.

## Lessons learned

- Replace with durable follow-up if needed
