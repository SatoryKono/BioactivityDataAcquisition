---
id: fix-cli-inspection-output-seam-20260514
title: Fix CLI inspection_output package seam
task_id: fix-cli-inspection-output-seam-20260514
created_at: '2026-05-14T09:45:21Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/interfaces/cli/commands/diagnostics.py
summary: Redirected internal diagnostics/inspection command imports to _inspection_output
  and added regression coverage so inspection_output stays off the commands package-root
  seam after public command imports.
---

# Episodic summary

## Task

- Title: Fix CLI inspection_output package seam

## Outcome

- Redirected internal diagnostics/inspection command imports to _inspection_output and added regression coverage so inspection_output stays off the commands package-root seam after public command imports.

## Lessons learned

- Replace with durable follow-up if needed
