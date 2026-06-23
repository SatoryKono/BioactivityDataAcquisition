---
name: "prometheus-query-debugger"
description: "Debug PromQL semantics, empty results, aggregation mistakes, histogram queries, and `No data` versus `0` behavior. Use when Prometheus-backed Grafana panels, recording rules, or alert expressions behave unexpectedly."
---

# Prometheus Query Debugger

## Overview

Use this skill to diagnose why a PromQL expression is empty, noisy,
misleading, or too expensive.

## BioETL Runtime Policy

- Project runtime contract: `../../../AGENTS.md`
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`

Default to reproducing the current query exactly before rewriting it.

## When To Use

Trigger this skill when the user asks to:

- fix a panel that returns no data or wrong totals
- understand why a PromQL query is noisy or expensive
- debug `rate`, `increase`, aggregation, or label-matching mistakes
- repair histogram or percentile queries
- clarify whether missing series should show `0` or `No data`

## Workflow

### 1. Reproduce the Current Query

- Start from the exact current expression.
- Use instant or range query mode intentionally.
- Confirm whether the issue is reproducible before changing anything.

### 2. Reduce to the Smallest Working Shape

- Strip the query back to a minimal selector.
- Rebuild one semantic step at a time:
  selector, filter, aggregation, transform, threshold.
- Identify the first step where behavior diverges from expectation.

### 3. Validate Query Semantics

- Check whether the metric type supports the chosen function.
- Validate aggregation dimensions explicitly.
- Inspect joins, grouping modifiers, and label drops carefully.

### 4. Resolve Empty-State Semantics

- Decide whether missing series means true zero or diagnostic absence.
- Use `or vector(0)` only when absence really means zero events.
- Preserve absence when it signals ingestion, scrape, or pipeline problems.

### 5. Rewrite Minimally

- Prefer the smallest safe change over stylistic rewrites.
- Keep final queries readable and operator-explainable.
- Hand off dashboard-specific work to `grafana-dashboard-extension` if needed.

## Review Checklist

- Metric type and function choice are compatible.
- `sum by`, `avg by`, and grouping dimensions are intentional.
- `rate`, `irate`, and `increase` choice is justified.
- Histogram logic is correct for the metric family.
- `No data` versus `0` is explicit.
- Query complexity is reasonable.

## Tooling Guidance

Prefer:

- `query_prometheus`
- `query_prometheus_histogram`
- `list_prometheus_metric_names`
- `list_prometheus_label_names`
- `list_prometheus_label_values`

Use local dashboard or rule files to understand the intended UX, but validate
PromQL against live datasource semantics when available.

## Definition of Done

- The failure mode is explained, not just patched.
- The rewritten query is minimal and semantically correct.
- Empty-state behavior is intentional.
- Cardinality or cost risks are called out.
