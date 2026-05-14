---
id: fix-cli-commands-package-20260514
title: Fix CLI commands package helper export regression
task_id: fix-cli-commands-package-20260514
created_at: '2026-05-14T07:22:22Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/interfaces/cli/commands/__init__.py
summary: Prevented export_support from reappearing as a package-root CLI command seam
  after importing the public export command and verified the commands package and
  export helper tests pass.
---

# Episodic summary

## Task

- Title: Fix CLI commands package helper export regression

## Outcome

- Prevented export_support from reappearing as a package-root CLI command seam after importing the public export command and verified the commands package and export helper tests pass.

## Lessons learned

- Replace with durable follow-up if needed
