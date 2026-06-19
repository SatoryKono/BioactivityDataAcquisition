---
id: fix-track-d-fixture-linkage
title: Fix track_d fixture control_plane linkage hash regression
task_id: fix-track-d-fixture-linkage
created_at: '2026-06-19T08:28:46Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/integration/ci/test_track_d_fixture_control_plane_linkage.py
summary: Normalized effective-config semantic identity to ignore machine-local data_dir
  and cached bronze paths, added regression coverage for replay-equivalent temp roots,
  and refreshed module coverage source-tree hash after targeted validation.
---

# Episodic summary

## Task

- Title: Fix track_d fixture control_plane linkage hash regression

## Outcome

- Normalized effective-config semantic identity to ignore machine-local data_dir and cached bronze paths, added regression coverage for replay-equivalent temp roots, and refreshed module coverage source-tree hash after targeted validation.

## Lessons learned

- Replace with durable follow-up if needed
