---
id: root-script-compat-scan-timeout
title: fix-root-script-compatibility-scan-timeout
task_id: root-script-compat-scan-timeout
created_at: '2026-05-25T04:18:09Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_root_script_compatibility_surfaces.py
summary: Replaced Python rglob/read_text scan in root script compatibility guard with
  git grep over target legacy wrapper strings, and excluded generated/memory/archive
  path prefixes. Windows and WSL targeted guardrail tests now pass under --timeout=30.
---

# Episodic summary

## Task

- Title: fix-root-script-compatibility-scan-timeout

## Outcome

- Replaced Python rglob/read_text scan in root script compatibility guard with git grep over target legacy wrapper strings, and excluded generated/memory/archive path prefixes. Windows and WSL targeted guardrail tests now pass under --timeout=30.

## Lessons learned

- Replace with durable follow-up if needed
