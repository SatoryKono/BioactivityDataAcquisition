---
id: create-filesystem-cleanup-issues
title: Create filesystem cleanup issues
task_id: create-filesystem-cleanup-issues
created_at: '2026-05-22T19:11:12Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Created GitHub issues from the filesystem audit evidence pack. Opened issue
  4555 for tracked root tests.txt allowlist/governance drift, issue 4556 for .codex_tmp
  root hygiene registry baseline drift, and issue 4557 for docs/site and docs/exports
  lifecycle classification drift across generated-artifact tooling. Deliberately did
  not create issues for local-only untracked files like test_print.py and new.env
  because they are workspace-local rather than repository-level governance defects.
---

# Episodic summary

## Task

- Title: Create filesystem cleanup issues

## Outcome

- Created GitHub issues from the filesystem audit evidence pack. Opened issue 4555 for tracked root tests.txt allowlist/governance drift, issue 4556 for .codex_tmp root hygiene registry baseline drift, and issue 4557 for docs/site and docs/exports lifecycle classification drift across generated-artifact tooling. Deliberately did not create issues for local-only untracked files like test_print.py and new.env because they are workspace-local rather than repository-level governance defects.

## Lessons learned

- Replace with durable follow-up if needed
