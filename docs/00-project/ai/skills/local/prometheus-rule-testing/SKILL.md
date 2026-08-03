> Mirror status: This file is a published/internal mirror under `docs/00-project/ai/**`. It is not a canonical runtime surface.
> Canonical runtime source: `.codex/skills/prometheus-rule-testing/SKILL.md`
> Governance: AI_RUNTIME_MIRROR_OWNERSHIP.md
> Edit the runtime source first, then refresh this mirror.
______________________________________________________________________

---
name: "prometheus-rule-testing"
description: "Test repo-backed Prometheus alert and recording rules with `promtool` before deployment. Use when rule files are added, changed, reviewed, or debugged and deterministic validation is needed."
---

# Prometheus Rule Testing

## Source Of Truth

- Normative index: `../../../../NORMATIVE_SOURCES.md`
- Root runtime contract: `../../../../../../AGENTS.md`
- Project rules: `../../../../RULES.md`
- Requirements: `../../../../../01-requirements/REQUIREMENTS.md`
- Accepted ADRs in `../../../../../02-architecture/decisions/`
- Memory policy: `../../../agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../agents/policy/POST_CHANGE_VALIDATION.md`

- Shared Grafana/Prometheus prerequisites: [../grafana-dashboard-extension/references/grafana-prometheus-prerequisites.md](../grafana-dashboard-extension/references/grafana-prometheus-prerequisites.md)

## Overview

Use this skill to verify repo-backed Prometheus rule behavior with explicit test
cases instead of intuition.

## BioETL Runtime Policy

- Project runtime contract: `../../../AGENTS.md`

This skill is for Prometheus rule files that can be validated with `promtool`.
For Grafana-managed alerts, use `prometheus-alert-rule-editor` and live query
validation instead.

## When To Use

Trigger this skill when the user asks to:

- add tests for a Prometheus alert or recording rule
- verify a changed threshold or aggregation
- debug why a rule fires too early, too late, or not at all
- review repo-backed rules before merge

## Workflow

### 1. Read the Rule File

- Read the shared prerequisites when rule testing is part of an alert or
  dashboard validation chain.
- Inspect the target rule and its group context.
- Confirm the rule is repo-backed and compatible with `promtool`.
- Identify the behavior that needs to be proven.

### 2. Model Input Series

- Create the smallest deterministic input data that exercises the rule.
- Include both expected healthy and failing cases.
- Add missing-series coverage when absence semantics matter.

### 3. Assert Behavior

- Assert non-firing and firing states explicitly.
- Assert labels and annotations where they matter operationally.
- For recording rules, assert output series shape and values.

### 4. Run `promtool`

- Execute `promtool test rules`.
- Tighten the test if it still leaves interpretation room.
- Keep the test readable for future operators.

## Preferred Test Cases

- healthy baseline
- threshold breach
- recovery path
- missing-series case
- labels and annotations expectation

## Rules

- Keep tests deterministic.
- Prefer one clear intent per test group.
- Do not hide ambiguous behavior under overly broad fixtures.
- If a rule cannot be expressed clearly in tests, call that out.

## Tooling Guidance

Prefer local repo tooling first:

- `promtool test rules`
- repository test wrappers if they already exist

Use `prometheus-query-debugger` first when the underlying expression itself is
still unclear.

## Definition of Done

- The rule has explicit deterministic test coverage.
- Fire and non-fire behavior are both asserted where relevant.
- Labels and annotations are validated when operator behavior depends on them.
- Test intent is understandable without reverse-engineering the fixture.
