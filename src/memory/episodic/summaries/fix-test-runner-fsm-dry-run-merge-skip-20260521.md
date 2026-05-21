---
id: fix-test-runner-fsm-dry-run-merge-skip-20260521
title: Fix composite runner FSM dry-run merge skip regression
task_id: fix-test-runner-fsm-dry-run-merge-skip-20260521
created_at: '2026-05-21T10:17:22Z'
ttl_days: 14
confidence: episodic
source_refs:
- d68e4d9a4
summary: Fixed the naming/package consistency gate regression by removing the public
  application-layer ManifestClockPort symbol. _manifest_time_support now exposes ManifestClockProtocol
  privately through the public ManifestClock alias, and WorkflowManifestService now
  types its clock dependency with ManifestClock. Verified naming gate, py_compile,
  architecture gate, WorkflowManifestService tests, and RunManifestService tests.
---

# Episodic summary

## Task

- Title: Fix composite runner FSM dry-run merge skip regression

## Outcome

- Fixed the naming/package consistency gate regression by removing the public application-layer ManifestClockPort symbol. _manifest_time_support now exposes ManifestClockProtocol privately through the public ManifestClock alias, and WorkflowManifestService now types its clock dependency with ManifestClock. Verified naming gate, py_compile, architecture gate, WorkflowManifestService tests, and RunManifestService tests.

## Lessons learned

- Replace with durable follow-up if needed
