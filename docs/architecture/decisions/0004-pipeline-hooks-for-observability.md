# 0004 Pipeline Hooks For Observability

## Status
Accepted

## Context
Pipeline runners already expose lifecycle hook points for extract, transform, validate, and write stages. These hooks are used to emit structured logs and metrics through the unified logger and post-transformer chain so that runs remain auditable.

## Decision
We will maintain first-class pipeline hooks dedicated to observability. Hooks will emit structured events, metrics, and trace metadata without mutating business data. The DI container wires the logging and telemetry providers so that pipelines can attach observers without hard dependencies on specific monitoring backends.

## Consequences
- Observability remains consistent across providers because hooks are part of the base pipeline template.
- Metrics and traces can be enriched or redirected by swapping observers in the container without code changes in pipelines.
- Hook coverage will be documented and extended as new stages or error policies are added to keep run visibility complete.
