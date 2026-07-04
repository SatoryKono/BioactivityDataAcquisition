> Mirror status: This file is a published/internal mirror under `docs/00-project/ai/**`. It is not a canonical runtime surface.
> Canonical runtime source:
> - Codex: `.codex/skills/prometheus-alert-rule-editor/SKILL.md`
> Governance: [AI Runtime Mirror Ownership](../../../agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md), [Memory Usage](../../../agents/guides/MEMORY_USAGE.md), [Post-Change Validation](../../../agents/policy/POST_CHANGE_VALIDATION.md).
> Edit the runtime source first, then refresh this mirror.
______________________________________________________________________

## name: prometheus-alert-rule-editor description: Create, review, and safely update Prometheus-backed alert rules, including expressions, labels, annotations, severity, and rule-group structure. Use when tasks touch alert behavior in Prometheus or Grafana-managed Prometheus alerting.

# Prometheus Alert Rule Editor

## Overview

Use this skill when editing alert rules and you need correctness, operator
clarity, and low-noise behavior.

## BioETL Runtime Policy

- Project runtime contract: `../../../AGENTS.md`
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`

Apply it to both repo-backed rule files and Grafana-managed Prometheus alerts,
but keep the storage model explicit.

## When To Use

Trigger this skill when the user asks to:

- create a new Prometheus alert
- tune thresholds or `for`
- fix noisy, missing, or misleading alerts
- change labels, annotations, severity, or grouping
- review alert rules before rollout

## Source Of Truth

- Normative index: `../../../../NORMATIVE_SOURCES.md`
- Root runtime contract: `../../../../../../AGENTS.md`
- Project rules: `../../../../RULES.md`
- Requirements: `../../../../../01-requirements/REQUIREMENTS.md`
- Accepted ADRs in `../../../../../02-architecture/decisions/`
- Memory policy: `../../../agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../agents/policy/POST_CHANGE_VALIDATION.md`

## Workflow

### 1. Read the Current Rule Shape

- Determine whether the rule lives in repo files or Grafana-managed alerting.
- Read the current rule and its surrounding group.
- Identify the actual operational intent before editing the expression.

### 2. Validate the Expression

- Confirm the metric family and selectors with
  `prometheus-metric-discovery` if needed.
- Validate the query semantics with `prometheus-query-debugger` when the
  expression is non-trivial.
- Preserve intent when refactoring the expression.

### 3. Review Alert Ergonomics

- Check threshold, `for`, and firing sensitivity.
- Make labels stable and routing-friendly.
- Make annotations actionable for operators.
- Avoid vague summaries and description text.

### 4. Edit Safely

- Prefer minimal changes over broad rewrites.
- Keep alert names, labels, and annotations consistent within the group.
- For Grafana-managed rules, also inspect notification routing when relevant.

### 5. Verify

- For repo-backed rules, add or update `promtool` tests where feasible.
- For Grafana-managed rules, validate the query and resulting rule shape
  through Grafana tooling.

## Rules

- Do not change alert intent silently.
- Do not invent metric names or label contracts.
- Keep annotations operator-facing and concrete.
- Avoid overly sensitive thresholds without evidence.
- Separate "alert expression is wrong" from "routing is wrong".

## Tooling Guidance

Prefer:

- `alerting_manage_rules`
- `alerting_manage_routing`
- `query_prometheus`

Use `prometheus-rule-testing` for repo-backed Prometheus rule files.
Grafana-managed alerts do not use `promtool` as their primary validation path.

## Definition of Done

- Rule storage model is explicit.
- Expression matches real metric semantics.
- Labels and annotations are coherent.
- Threshold and `for` behavior are intentional.
- Verification path is documented and executed where possible.
