---
trigger: model_decision
description: USE WHEN designing or editing pipelines; one source → one public pipeline; unified components; standard stages
---

# 09. ETL Architecture & Patterns (Skills: Hexagonal, DI, DQ Monitoring)

## Overview
This document defines the architectural blueprint for the BioETL project, enforcing strict separation of concerns, dependency injection, and robust data quality monitoring.

## 1. Hexagonal Architecture (Ports & Adapters)

### Core Principle
Dependencies point **inwards**. The Domain layer knows nothing about the outside world (Infrastructure).

1.  **Domain (Inner Hexagon)**: `src/bioetl/domain`
    -   **Entities**: Pure Python dataclasses (e.g., `Compound`, `Target`). No ORM logic.
    -   **Ports**: Abstract Base Classes (ABCs) or Protocols defining interfaces (e.g., `TargetRepository`, `ChemblClient`).
    -   **Use Cases**: Application logic orchestration.

2.  **Application (Orchestration)**: `src/bioetl/application`
    -   **Services**: Implement use cases using Ports.
    -   **DTOs**: Data Transfer Objects for API inputs/outputs.
    -   **Example**: `CompoundEnrichmentService` uses `CompoundRepository` (Port).

3.  **Infrastructure (Adapters)**: `src/bioetl/infrastructure`
    -   **Implementations**: Concrete classes implementing Domain Ports (e.g., `SqlTargetRepository`, `HttpChemblClient`).
    -   **External Libs**: `httpx`, `polars`, `deltalake`.

4.  **Composition Root (Wiring)**: `src/bioetl/composition`
    -   **The ONLY place** where classes are instantiated and dependencies injected.
    -   **Bootstrap**: `bootstrap.py` assembles the object graph.

## 2. Dependency Injection (Skill: Dependency Injection)

### Pattern: Constructor Injection
All dependencies must be passed explicitly via `__init__`.
-   **Anti-Pattern**: Creating dependencies inside methods (`repo = SqlRepo()`).
-   **Anti-Pattern**: Using global state or Singletons (`Repo.instance()`).

### Composition Root Example
```python
# src/bioetl/composition/bootstrap.py

def assemble_pipeline(settings: Settings) -> Pipeline:
    # 1. Create Adapters (Infrastructure)
    client = HttpxClient(base_url=settings.chembl_url)
    repo = ChemblRepository(client)
    logger = StructLogAdapter()

    # 2. Create Service (Application)
    service = CompoundEnrichmentService(repo, logger)

    # 3. Create Pipeline (Domain/App)
    return Pipeline(service)
```

## 3. Data Quality Monitoring (Skill: Data Quality Monitoring)

### Strategy: "Trust but Verify"
Data quality checks happen **before** loading into Silver/Gold layers.

1.  **Schema Validation (Pandera)**:
    -   Enforce types and constraints (e.g., `pchembl_value >= 0`).
    -   Reject entire batch if critical schema violation occurs.

2.  **Anomaly Detection (Statistical)**:
    -   Monitor metrics like `row_count`, `null_percentage`, `mean_value`.
    -   **Z-Score Check**: If `(current - mean) / std_dev > 3`, flag as anomaly.
    -   **Action**: Log warning or halt pipeline based on severity (Configurable).

3.  **Quarantine Pattern**:
    -   **Bad Rows**: Rows failing non-critical checks (e.g., malformed date) are moved to `data/quarantine/`.
    -   **Good Rows**: Proceed to next stage.
    -   **Metric**: `quarantined_rows_count` must be exported to Prometheus.

## 4. Pipeline Execution Flow

1.  **Extract (Source -> Bronze)**: Raw download. Fail fast on network errors.
2.  **Transform (Bronze -> Silver)**:
    -   Validate Schema (Pandera).
    -   Clean & Normalize (Polars).
    -   Deduplicate (Content Hash).
3.  **Load (Silver -> Gold)**:
    -   Aggregate.
    -   Optimize (Delta Lake Vacuum/Z-Order).

# REFERENCE

See [docs/styleguide/08-etl-architecture.md](../../docs/styleguide/08-etl-architecture.md) for detailed documentation.
