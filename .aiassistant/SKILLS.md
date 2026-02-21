# BioETL Project Skills & Competencies

This document lists the required skills and standards for the BioETL project. All agents must demonstrate proficiency in these areas by adhering to the linked rules.

## Core Engineering Skills

| Skill Name | Description | Rule / Standard | Complexity | Status |
| :--- | :--- | :--- | :---: | :---: |
| **Hexagonal Architecture** | Separation of Domain, App, Infra layers | [09-etl-architecture.md](./rules/09-etl-architecture.md) | 4 | ✅ |
| **Medallion Data Flow** | Bronze (Raw) -> Silver (Clean) -> Gold (Agg) | [17-data-processing.md](./rules/17-data-processing.md) | 3 | ✅ |
| **Delta Lake Management** | ACID transactions, Vacuum, Optimize | [17-data-processing.md](./rules/17-data-processing.md) | 4 | ✅ |
| **Polars Lazy API** | High-perf ETL with LazyFrames | [17-data-processing.md](./rules/17-data-processing.md) | 3 | ✅ |
| **Pandera Validation** | Schema enforcement & runtime checks | [17-data-processing.md](./rules/17-data-processing.md) | 2 | ✅ |
| **Bioinformatics Domain** | Understanding Targets, Assays, Compounds | [16-domain-knowledge.md](./rules/16-domain-knowledge.md) | 4 | ✅ |
| **Async I/O (httpx)** | Non-blocking API clients | [08-api-clients.md](./rules/08-api-clients.md) | 3 | ✅ |
| **Structured Logging** | JSON logging with context (structlog) | [03-logging.md](./rules/03-logging.md) | 2 | ✅ |
| **Data Quality Monitoring** | Anomaly detection & quarantine | [09-etl-architecture.md](./rules/09-etl-architecture.md) | 4 | ✅ |
| **Dependency Injection** | Composition Root pattern | [09-etl-architecture.md](./rules/09-etl-architecture.md) | 3 | ✅ |
| **VCR.py Testing** | Deterministic integration tests | [15-vcr-policy.md](./rules/15-vcr-policy.md) | 2 | ✅ |
| **Secret Management** | .env handling & PII hashing | [10-secrets-and-config.md](./rules/10-secrets-and-config.md) | 3 | ✅ |
| **Resiliency Patterns** | Retries, Backoff, Circuit Breakers | [08-api-clients.md](./rules/08-api-clients.md) | 3 | ✅ |
| **Pydantic Configuration** | Type-safe settings management | [10-secrets-and-config.md](./rules/10-secrets-and-config.md) | 2 | ✅ |
| **Johnny.Decimal Docs** | Structured documentation organization | [13-documentation-standards.md](./rules/13-documentation-standards.md) | 2 | ✅ |

## How to Use
When working on a task, identify the relevant skills and consult the corresponding rule file. For example, if adding a new data source, consult **Hexagonal Architecture** (for structure), **Async I/O** (for client), and **Polars** (for transformation).
