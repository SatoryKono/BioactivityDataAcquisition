---
id: control-plane-artifact-validation-timeout
title: Fix control-plane artifact validation timeout
task_id: control-plane-artifact-validation-timeout
created_at: '2026-05-06T07:42:51Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/integration/ci/test_control_plane_artifact_validation.py
summary: Fixed timeout in tests/integration/ci/test_control_plane_artifact_validation.py
  by changing scripts/engineering/ci/validate_control_plane_artifacts.py to validate
  Git-tracked committed artifact examples in real checkouts and use filesystem fallback
  only outside Git roots, such as tmp_path tests. Added regression coverage proving
  untracked local runtime data/output/control files are ignored.
---

# Episodic summary

## Task

- Title: Fix control-plane artifact validation timeout

## Outcome

- Fixed timeout in tests/integration/ci/test_control_plane_artifact_validation.py by changing scripts/engineering/ci/validate_control_plane_artifacts.py to validate Git-tracked committed artifact examples in real checkouts and use filesystem fallback only outside Git roots, such as tmp_path tests. Added regression coverage proving untracked local runtime data/output/control files are ignored.

## Lessons learned

- Replace with durable follow-up if needed
