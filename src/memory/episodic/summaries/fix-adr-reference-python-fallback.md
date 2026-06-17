---
id: fix-adr-reference-python-fallback
title: Fix ADR reference Python fallback when git commands fail
task_id: fix-adr-reference-python-fallback
created_at: '2026-06-17T09:56:09Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Fixed ADR enforcement reference discovery so git-grep failure falls back
  to ripgrep and then a pure Python filesystem scanner instead of git ls-files. Regression
  test now verifies the pure Python fallback on a minimal tree without invoking Git.
  ADR matrix tests, module artifact check, ruff check, and ruff format passed.
---

# Episodic summary

## Task

- Title: Fix ADR reference Python fallback when git commands fail

## Outcome

- Fixed ADR enforcement reference discovery so git-grep failure falls back to ripgrep and then a pure Python filesystem scanner instead of git ls-files. Regression test now verifies the pure Python fallback on a minimal tree without invoking Git. ADR matrix tests, module artifact check, ruff check, and ruff format passed.

## Lessons learned

- Replace with durable follow-up if needed
