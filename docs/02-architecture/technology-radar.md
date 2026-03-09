# Technology Radar

*Updated: 2026-03-09 | Aligned with RULES.md v5.23*

This document records the rationale behind every significant tool, library, and
platform choice in BioETL. It follows the
[ThoughtWorks Technology Radar](https://www.thoughtworks.com/radar) ring model:

| Ring | Meaning |
|------|---------|
| **Adopt** | Battle-tested, part of our default stack |
| **Trial** | Worth pursuing; use with care |
| **Assess** | Worth exploring; low-risk experiments only |
| **Hold** | Do not start new work; migrate away when practical |

Each entry links to the ADR (if one exists) that formalises the decision.

---

## Language & Runtime

### Python 3.11+ — *Adopt*

**Rationale:** Python is the lingua franca of data engineering and computational
biology. Version 3.11+ brings significant performance improvements (up to 60 %
faster CPython) and better error messages. Version 3.13 is the recommended target
for new environments.

**Alternatives considered:** Rust (too steep for a data-science team), Julia (niche
ecosystem), Go (poor scientific library coverage).

---

## Dependency Management

### uv — *Adopt*

**Rationale:** `uv` (Astral) provides near-instant dependency resolution and
installation through its Rust-based solver. Compared to `pip+pip-tools` or
`poetry`, it is significantly faster in CI and offers deterministic lock-file
semantics compatible with `pyproject.toml` PEP 621 metadata.

**Alternatives considered:** `poetry` (slower resolver, non-standard extras
syntax), `pdm` (limited adoption), `conda` (too heavy for a single-language
project).

---

## Data Processing

### Polars — *Adopt*

**Rationale:** Polars provides lazy evaluation, a vectorised Rust engine, and
significantly better performance than pandas for large-frame operations. Its
strict type system catches schema drift early. Used throughout the Silver and
Gold transformation stages.

**Alternatives considered:** `pandas` (still a required dependency for Pandera
compatibility; used as bridge type), `DuckDB` (assessed, but adds an extra
binary dependency not needed for local-only).

### Pandera — *Adopt*

**Rationale:** Declarative DataFrame schema validation with Polars and pandas
backends. Enables field-level DQ contracts expressed in Python — the same
language as the pipeline code — and integrates with `pyproject.toml`-based
configuration. See [ADR-027](decisions/ADR-027-dq-rules-externalization.md) and
[ADR-028](decisions/ADR-028-filter-rules-externalization.md).

**Alternatives considered:** `great_expectations` (heavy config overhead,
separate YAML store), custom validators (reinventing the wheel).

### PyArrow — *Adopt*

**Rationale:** Required low-level dependency for both `polars` and `deltalake`.
Provides efficient columnar memory representation and Parquet I/O primitives.

---

## Storage

### Delta Lake (`delta-rs`) — *Adopt*

**Rationale:** ACID transactions, schema enforcement, time-travel, and Z-ORDER
optimisation on top of the local file system — with no external services
required. This is the **mandatory** format for Silver and Gold layers.
See [ADR-001](decisions/ADR-001-delta-lake-vs-parquet.md).

**Alternatives considered:** Raw Parquet (no ACID, no time-travel — rejected),
Apache Iceberg (no pure-Python writer without Spark), Apache Hudi (JVM-only).

### JSONL + Zstandard (Bronze) — *Adopt*

**Rationale:** Bronze writes are append-only ingestion artifacts. JSONL preserves
the raw API response structure; Zstandard compression delivers 70–80 % size
reduction at high decompression speed. Files are immutable after creation.
See [ADR-002](decisions/ADR-002-medallion-architecture.md).

---

## HTTP & Networking

### httpx — *Adopt*

**Rationale:** Native async support (`asyncio`), HTTP/2, built-in retry hooks,
and a clean interface for both sync and async use. Replaces `requests` for all
provider clients. See [ADR-032](decisions/ADR-032-unified-http-client.md).

**Alternatives considered:** `aiohttp` (lower-level, more boilerplate),
`requests` (sync-only, no HTTP/2), `urllib3` (too low-level).

---

## Validation & Serialisation

### Pydantic v2 — *Adopt*

**Rationale:** Fast Rust-backed validation, first-class `dataclass`-like API,
and strong mypy integration. Used for all domain models, config schemas, and
API response deserialisation. See [ADR-004](decisions/ADR-004-pydantic-vs-dataclasses.md).

**Alternatives considered:** `dataclasses` + `__post_init__` validation
(verbose, no serialisation), `attrs` (less Python-community momentum),
`marshmallow` (separate schema definition overhead).

### orjson — *Adopt*

**Rationale:** 2–10× faster JSON serialisation/deserialisation compared to
the stdlib `json` module. Zero additional runtime cost; drop-in compatible for
most use-cases. Used in all high-throughput serialisation paths.

---

## Observability

### structlog — *Adopt*

**Rationale:** Structured logging produces machine-readable log events that
integrate cleanly with log aggregation tooling. Processor chains allow
context enrichment without polluting call sites.
See [ADR-006](decisions/ADR-006-logger-metrics-ports.md) and
[ADR-017](decisions/ADR-017-observability-architecture.md).

**Alternatives considered:** `loguru` (structured output support is limited),
stdlib `logging` (no native structured output).

### Prometheus Client — *Adopt*

**Rationale:** Prometheus metrics are the de-facto standard for operational
observability. The `prometheus-client` library emits metrics compatible with
any Prometheus/Grafana stack. Metrics are exposed via a `MetricsPort` to keep
infrastructure details out of the domain layer.
See [ADR-017](decisions/ADR-017-observability-architecture.md).

### OpenTelemetry — *Trial*

**Rationale:** OTEL provides vendor-neutral distributed tracing. Currently an
optional `[tracing]` extra; a `NoOpTracing` adapter is provided for environments
without an OTEL collector.
See [ADR-022](decisions/ADR-022-tracing-noop.md).

---

## CLI

### Click — *Adopt*

**Rationale:** Battle-tested, composable command-line interface framework with
strong typing support and test utilities. Used for all user-facing pipeline
commands.

### Typer — *Trial*

**Rationale:** Thin wrapper over Click that derives CLI arguments from Python
type hints, reducing boilerplate. Evaluated as a replacement for verbose Click
command definitions.

---

## Testing

### pytest — *Adopt*

**Rationale:** The dominant Python testing framework with a rich plugin
ecosystem. Used for unit, integration, e2e, architecture, and contract tests.

### VCR.py — *Adopt*

**Rationale:** Records and replays HTTP interactions, allowing provider-specific
tests to run without network access. Cassettes are stored in
`tests/fixtures/vcr/`.

### Hypothesis — *Trial*

**Rationale:** Property-based testing for data-transformation functions.
Generates edge-case inputs automatically, surfacing bugs that example-based
tests miss.

### pytest-xdist — *Trial*

**Rationale:** Parallelises the test suite across CPU cores. Used in CI
(`make test-ci`); not the default locally to avoid resource contention.

---

## Type Checking

### mypy (strict) — *Adopt*

**Rationale:** Mandatory static type checking at `--strict` level prevents an
entire class of runtime errors. All public interfaces must carry type
annotations.

### basedpyright — *Trial*

**Rationale:** Faster Pyright-based type checker used as a secondary validation
pass in CI. Catches cases mypy misses and vice versa.

---

## Code Quality

### Ruff — *Adopt*

**Rationale:** All-in-one Python linter and formatter written in Rust.
Replaces `flake8`, `isort`, `pyupgrade`, and `black` with a single tool that
is 10–100× faster.

### Bandit — *Adopt*

**Rationale:** SAST scanner for common Python security issues. Blocks merge
on `HIGH` severity findings. Part of the mandatory security gate.

### Xenon / Radon — *Adopt*

**Rationale:** Cyclomatic complexity enforcement. `xenon` gates on thresholds
(max-absolute B, average A); `radon` provides maintainability index metrics.

---

## Documentation

### MkDocs + Material theme — *Adopt*

**Rationale:** Docs-as-code approach with Markdown sources in the repository.
Material theme provides a polished look, search, dark/light toggle, and Mermaid
diagram rendering with no extra build step.

### mkdocstrings — *Adopt*

**Rationale:** Auto-generates API reference pages directly from Google-style
docstrings, keeping code and docs in sync.

### Mermaid — *Adopt*

**Rationale:** Diagram-as-code format that renders inside both MkDocs and
GitHub Markdown. Governance rules for diagram quality are defined in
[ADR-040](decisions/ADR-040-diagram-governance.md).

---

## Configuration

### PyYAML — *Adopt*

**Rationale:** Provider and entity pipeline configurations are stored as YAML
files in `configs/`. YAML is human-readable and version-control-friendly.
See [ADR-025](decisions/ADR-025-pipeline-config-unification.md) and
[ADR-039](decisions/ADR-039-unified-entity-config-format.md).

---

## Containerisation

### Docker Compose — *Trial*

**Rationale:** Used for optional local service stack (Prometheus, Grafana).
The core BioETL pipeline does **not** require Docker (ADR-010: Local-Only).

**Status:** Optional extra; not part of the critical path.

---

## On Hold / Not Used

| Tool | Ring | Reason |
|------|------|--------|
| Apache Spark | Hold | JVM dependency incompatible with local-only architecture |
| Airflow / Prefect | Hold | Over-engineered orchestration for a single-machine deployment |
| Redis | Hold | Deferred to future distributed deployment (ADR-010) |
| MinIO / S3 | Hold | Deferred to future distributed deployment (ADR-010) |
| Celery | Hold | Network broker required; incompatible with local-only |
| SQLAlchemy / ORM | Hold | No relational DB; Delta Lake covers structured storage needs |
| Raw Parquet (Silver/Gold) | Hold | Replaced by Delta Lake (ADR-001) |
| `print()` for logging | Hold | Use structlog `LoggerPort` instead |

---

## Related Documents

- [Architecture Overview](00-overview.md)
- [System Context](system-context.md)
- [ADR Index](decisions/README.md)
- [RULES.md](../00-project/RULES.md) — §Technology stack constraints
- [REQUIREMENTS.md](../01-requirements/REQUIREMENTS.md) — REQ-ARCH-*
