# Observability Layers Architecture

## Overview

BioETL implements a layered approach to observability, separating the **Definition** of what to observe from the **Implementation** of how to store/transmit it.

## Application Layer (src/bioetl/application/observability/)

This layer focuses on **Domain Events** and **Pipeline Lifecycle**.

*   **PipelineObserver**: A context manager that wraps pipeline execution.
    *   *Role*: Captures Start/Success/Failure events.
    *   *Metrics*: Duration, Status.
    *   *Logs*: Structured lifecycle logs.

## Infrastructure Layer (src/bioetl/infrastructure/observability/)

This layer provides the concrete **Adapters** for observability ports.

*   **PrometheusMetrics**: Implements `MetricsPort`.
    *   *Role*: Exposes metrics via HTTP endpoint.
*   **Structlog**: Implements `LoggerPort` (implicitly via duck typing).
*   **OpenTelemetry**: (Optional) Implements `TracingPort`.

## Interaction Diagram

```mermaid
sequenceDiagram
    participant App as Application (Pipeline)
    participant Obs as PipelineObserver
    participant Port as MetricsPort (Interface)
    participant Infra as PrometheusMetrics (Impl)

    App->>Obs: enter()
    Obs->>Port: increment-counter(started)
    Port->>Infra: INC bioetl_pipeline_runs_total

    App->>App: process-batch()

    App->>Obs: exit(success)
    Obs->>Port: observe-histogram(duration)
    Port->>Infra: OBS bioetl_pipeline_duration_seconds
```

## Metrics Standards

All metrics MUST follow these naming conventions:

*   Prefix: `bioetl_`
*   Common Labels: `pipeline`, `run_type`, `stage`, `provider`, `adapter`
*   Current registry size: **68 metrics** (see `src/bioetl/infrastructure/observability/metrics_export_names.py`)

See `docs/04-reference/contracts/observability.md` for the current canonical contract (v3.0.0).
