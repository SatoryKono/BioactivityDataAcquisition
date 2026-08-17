---
record_id: coderabbit-residual-fixes-20260817
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 80383012948d978e4abaa1a6f1079bfeeedbbd4e
branch: agent/coderabbit-fixes-20260817
worktree_id: c8e879045fbcee33
task_id: coderabbit-residual-fixes-20260817
actor:
  runtime: codex
  agent: py-test-bot
  model: null
created_at: '2026-08-17T02:15:32.455765+00:00'
source_refs:
- reports/quality/coderabbit/20260816/review_A_S01-domain-normalization.log
- reports/quality/coderabbit/20260816/review_A_S01-domain-filtering.log
- reports/quality/coderabbit/20260816/review_A_S01-domain-lineage.log
- reports/quality/coderabbit/20260816/review_A_S01-domain-mapping.log
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 7bd36b3ff7a08bdb152fbaf114fa9fd51619c5f72e34cb84be4631d9f82181a8
id: coderabbit-residual-fixes-20260817
title: Continue fixing CodeRabbit findings
ttl_days: 14
confidence: episodic
summary: 'Fixed seven confirmed CodeRabbit residuals: strict date-part and ASCII-year
  normalization, canonical JSON backend parity, multi-column FilterLoadResult invariants,
  JSON-safe lineage exports, publication-type fail-closed normalization, ChEMBL unknown
  classification, and PubMed raw-field precedence. Focused/domain tests, Ruff, mypy,
  architecture, docs, debt, governance, and quality gates passed.'
---

# Episodic summary

## Task

- Title: Continue fixing CodeRabbit findings

## Outcome

- Fixed seven confirmed CodeRabbit residuals: strict date-part and ASCII-year normalization, canonical JSON backend parity, multi-column FilterLoadResult invariants, JSON-safe lineage exports, publication-type fail-closed normalization, ChEMBL unknown classification, and PubMed raw-field precedence. Focused/domain tests, Ruff, mypy, architecture, docs, debt, governance, and quality gates passed.

## Lessons learned

- Replace with durable follow-up if needed
