---
id: fix-source-test-mapping-pandera-compat-20260603
title: Fix source-test mapping exemption for pandera compat
task_id: fix-source-test-mapping-pandera-compat-20260603
created_at: '2026-06-03T13:54:30Z'
ttl_days: 14
confidence: episodic
source_refs:
- configs/quality/source_test_mapping_exceptions.yaml
summary: Updated the thin-package source-test mapping exception for pandera_compat.py
  to point at the existing owner tests after the compatibility test rename, restoring
  the architecture policy guard.
---

# Episodic summary

## Task

- Title: Fix source-test mapping exemption for pandera compat

## Outcome

- Updated the thin-package source-test mapping exception for pandera_compat.py to point at the existing owner tests after the compatibility test rename, restoring the architecture policy guard.

## Lessons learned

- Replace with durable follow-up if needed
