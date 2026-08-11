---
record_id: fix-live-observability-checkers-20260811
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 0774688ed86cd5d26ccf0e1b273404de1335ed86
branch: dashboard-consolidation-cycle
worktree_id: b5393af69d37a674
task_id: fix-live-observability-checkers-20260811
actor:
  runtime: codex
  agent: codex-root
  model: null
created_at: '2026-08-11T17:49:29.328554+00:00'
source_refs:
- scripts/ops/observability/check_prometheus_rules_health.py
- scripts/ops/observability/validate_live_observability.py
- tests/unit/scripts/ops/test_check_prometheus_rules_health.py
- tests/unit/scripts/ops/observability/test_validate_live_observability.py
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: d1c1b1269fcc8d2476bcd61d8bd73dc95e8635e2e1074601c75fa742ca1b3556
id: fix-live-observability-checkers-20260811
title: Fix live observability checkers
ttl_days: 14
confidence: episodic
summary: Replaced invalid PromQL regex escape with RE2-safe character class, aligned
  live dashboard validation with the seven canonical shipped UIDs, added regression
  tests, and validated 8/8 live checks. Proof-or-Stop plan stopped because repository-wide
  git diff exceeded its 20 second timeout.
---

# Episodic summary

## Task

- Title: Fix live observability checkers

## Outcome

- Replaced invalid PromQL regex escape with RE2-safe character class, aligned live dashboard validation with the seven canonical shipped UIDs, added regression tests, and validated 8/8 live checks. Proof-or-Stop plan stopped because repository-wide git diff exceeded its 20 second timeout.

## Lessons learned

- Replace with durable follow-up if needed
