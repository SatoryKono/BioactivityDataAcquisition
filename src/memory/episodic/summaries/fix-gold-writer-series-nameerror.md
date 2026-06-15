---
id: fix-gold-writer-series-nameerror
title: Fix Series NameError in Gold writer merged validation test
task_id: fix-gold-writer-series-nameerror
created_at: '2026-06-15T12:43:32Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Fixed the Gold writer merged validation test by moving the Pandera Series
  import to module scope so the nested DataFrameModel class can resolve it. The exact
  failing selector and the full TestGoldWriterMergedValidation block now pass on both
  WSL and Windows .venv-win.
---

# Episodic summary

## Task

- Title: Fix Series NameError in Gold writer merged validation test

## Outcome

- Fixed the Gold writer merged validation test by moving the Pandera Series import to module scope so the nested DataFrameModel class can resolve it. The exact failing selector and the full TestGoldWriterMergedValidation block now pass on both WSL and Windows .venv-win.

## Lessons learned

- Replace with durable follow-up if needed
