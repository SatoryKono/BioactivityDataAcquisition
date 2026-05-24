---
id: debug-cmd-launch-loop
title: Investigate repeated cmd launches
task_id: debug-cmd-launch-loop
created_at: '2026-05-24T15:05:44Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Patched detached observability backend startup to request CREATE_NO_WINDOW
  and hidden STARTUPINFO on Windows, and added focused unit coverage for platform-specific
  subprocess kwargs.
---

# Episodic summary

## Task

- Title: Investigate repeated cmd launches

## Outcome

- Patched detached observability backend startup to request CREATE_NO_WINDOW and hidden STARTUPINFO on Windows, and added focused unit coverage for platform-specific subprocess kwargs.

## Lessons learned

- Replace with durable follow-up if needed
