---
id: debug-memory-validate-timeout
title: Debug memory scaffold validation timeout
task_id: debug-memory-validate-timeout
created_at: '2026-05-24T12:52:41Z'
ttl_days: 14
confidence: episodic
source_refs:
- AGENTS.md
summary: 'Debugged timeout in tests/unit/memory/test_validate.py. Root cause: validate_memory_scaffold
  scanned 2081 episodic markdown notes and parsed each via full YAML/body path, causing
  slow baseline validation on Windows. Fixed by adding metadata-only parsing for include_body=False,
  switching episodic validation away from body reads, and bounding default episodic
  scan to 200 notes per canonical episodic directory while keeping full-history validation
  as explicit opt-in. Verified default validate_memory_scaffold now returns zero issues
  in about 4.63s; full include_all_episodic_notes mode still surfaces 16 historical
  corpus issues and remains available for forensic scans.'
---

# Episodic summary

## Task

- Title: Debug memory scaffold validation timeout

## Outcome

- Debugged timeout in tests/unit/memory/test_validate.py. Root cause: validate_memory_scaffold scanned 2081 episodic markdown notes and parsed each via full YAML/body path, causing slow baseline validation on Windows. Fixed by adding metadata-only parsing for include_body=False, switching episodic validation away from body reads, and bounding default episodic scan to 200 notes per canonical episodic directory while keeping full-history validation as explicit opt-in. Verified default validate_memory_scaffold now returns zero issues in about 4.63s; full include_all_episodic_notes mode still surfaces 16 historical corpus issues and remains available for forensic scans.

## Lessons learned

- Replace with durable follow-up if needed
