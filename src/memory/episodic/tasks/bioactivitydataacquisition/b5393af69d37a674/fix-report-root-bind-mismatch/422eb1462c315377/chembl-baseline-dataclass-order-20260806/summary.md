---
record_id: chembl-baseline-dataclass-order-20260806
record_type: working
repo_id: bioactivitydataacquisition
git_commit: bd1f8cbaef86606efc74569458cd20b6f1df3613
branch: fix/report-root-bind-mismatch
worktree_id: b5393af69d37a674
task_id: chembl-baseline-dataclass-order-20260806
actor:
  runtime: codex
  agent: py-debug-bot
  model: null
created_at: '2026-08-06T18:45:19.249933+00:00'
source_refs:
- src/bioetl/infrastructure/adapters/chembl/client.py
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 7fe86716375a6894c9e666512bb5372ff45237441e04e9371369df9c51773f7c
id: chembl-baseline-dataclass-order-20260806
title: Fix ChEMBL baseline dataclass constructor failure
ttl_days: 14
confidence: episodic
summary: DBG-001 fixed inherited dataclass defaults by using explicit field() declarations
  for ChemblAdapter http_client/logger; focused WSL and Windows tests pass. Full suite
  preflight blocked twice by concurrent checkout mutations, with CrossRef source_content_mismatch
  on the second attempt.
---

# Episodic summary

## Task

- Title: Fix ChEMBL baseline dataclass constructor failure

## Outcome

- DBG-001 fixed inherited dataclass defaults by using explicit field() declarations for ChemblAdapter http_client/logger; focused WSL and Windows tests pass. Full suite preflight blocked twice by concurrent checkout mutations, with CrossRef source_content_mismatch on the second attempt.

## Lessons learned

- Replace with durable follow-up if needed
