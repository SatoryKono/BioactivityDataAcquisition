---
name: "prometheus-metric-discovery"
description: "Discover real Prometheus metrics, labels, label values, and metric metadata before writing PromQL or editing dashboards and alerts. Use when tasks touch Prometheus-backed Grafana panels, alert rules, recording rules, query debugging, or datasource investigation."
---

# Prometheus Metric Discovery

## Source Of Truth

- Normative index: `../../../docs/00-project/NORMATIVE_SOURCES.md`
- Root runtime contract: `../../../AGENTS.md`
- Project rules: `../../../docs/00-project/RULES.md`
- Requirements: `../../../docs/01-requirements/REQUIREMENTS.md`
- Accepted ADRs in `../../../docs/02-architecture/decisions`


## Overview

Use this skill to establish what actually exists in Prometheus before changing a
query, dashboard panel, or rule.

## BioETL Runtime Policy

- Project runtime contract: `../../../AGENTS.md`
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`

Treat discovery as a required first step, not optional cleanup after a failed
query.

## When To Use

Trigger this skill when the user asks to:

- build a new PromQL query
- debug a Prometheus-backed Grafana panel
- add or edit an alert or recording rule
- find the right metric or label set for a dashboard
- verify whether a metric, label, or series really exists

## Workflow

### 1. Discover Candidate Metrics

- Start with metric-name discovery instead of guessing.
- Prefer nearby naming families over isolated one-off metrics.
- If the task started from an existing query, extract its core metric names
  first.

### 2. Inspect Metric Metadata

- Check metric type and help text where available.
- Distinguish counters, gauges, histograms, and summaries before proposing
  PromQL changes.
- Call out when the metric shape does not support the intended analysis.

### 3. Inspect Labels

- List label names for the relevant metric family.
- Inspect label values only for the labels needed by the task.
- Prefer stable, low-cardinality selectors.

### 4. Validate the Selector

- Build the smallest selector that still expresses the task.
- Avoid overfitting on instance-specific or ephemeral labels.
- If the selector is expensive or ambiguous, say so before handing off.

### 5. Hand Off Verified Inputs

- Return the verified metric names, labels, and safe selectors.
- Hand off to `prometheus-query-debugger`,
  `prometheus-alert-rule-editor`, or `grafana-dashboard-extension` as needed.

## Rules

- Do not invent metric names.
- Do not assume label names from memory.
- Prefer existing stable labels over ad-hoc selectors.
- Call out high-cardinality risk early.
- Separate "metric missing" from "wrong query shape".

## Tooling Guidance

Prefer live Prometheus discovery tools when available:

- `list_prometheus_metric_names`
- `list_prometheus_metric_metadata`
- `list_prometheus_label_names`
- `list_prometheus_label_values`
- `query_prometheus`

If the task is repo-first, use local dashboard/rule files only to learn what to
search for, not as proof that the metric exists.

## Definition of Done

- Candidate metric names are verified.
- Required labels are verified.
- The recommended selector is explicit and reasonably stable.
- High-cardinality or ambiguity risks are called out.
