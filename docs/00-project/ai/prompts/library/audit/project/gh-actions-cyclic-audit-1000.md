---
id: prompt.audit.project.gh-actions-cyclic-1000
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, any]
params: [PR_NUMBER, BRANCH, HEAD_SHA, MERGE_SHA]
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
related_ssot:
  - AGENTS.md
  - docs/00-project/NORMATIVE_SOURCES.md
anti_patterns:
  - Raising tech-debt budgets
  - Committing to main
  - Skipping hooks
tags: [gh-actions, cyclic, audit, operator]
summary: GH Actions cyclic audit 1000x test->fix->retest
---

# GH Actions Cyclic Audit — 1000x test->fix->retest

**Repo:** `SatoryKono/BioactivityDataAcquisition`
**PR:** `{{PR_NUMBER}}` | **Branch:** `{{BRANCH}}` | **Base:** `main`
**Head SHA:** `{{HEAD_SHA}}`
**Merge SHA:** `{{MERGE_SHA}}`

## Цель
Довести PR до зелёного `checks-complete` за 1000 итераций.

## Цикл
for i in 1..1000: test -> fix -> retest
