---
id: fix-cli-import-guard-syntaxerror
title: Fix CLI command import guard syntax error
task_id: fix-cli-import-guard-syntaxerror
created_at: '2026-05-30T08:33:14Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/helpers/git_index_scan.py
summary: Fixed invalid star-import wrapper syntax in run_manifest_diagnostics_artifact_support
  and hardened git_tracked_files to drop stale git-index entries that no longer exist
  in the working tree, unblocking CLI import guard scans.
---

# Episodic summary

## Task

- Title: Fix CLI command import guard syntax error

## Outcome

- Fixed invalid star-import wrapper syntax in run_manifest_diagnostics_artifact_support and hardened git_tracked_files to drop stale git-index entries that no longer exist in the working tree, unblocking CLI import guard scans.

## Lessons learned

- Replace with durable follow-up if needed
