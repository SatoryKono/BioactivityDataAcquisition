---
trigger: model_decision
description: USE WHEN designing or editing pipelines; one source → one public pipeline; unified components; standard stages
---

etl-architecture

> Scope:
>
> - USE WHEN designing or editing pipelines; one source → one public pipeline; unified components; standard stages
> - Use when editing files matching: `src/bioetl/pipelines/**/*.py`, `docs/etl_contract/**/*.md`, `docs/pipelines/**/*.md`

# NAMING

- Pipeline names: `{source}_{entity}` (e.g., `chembl_activity`, `uniprot_protein`).

# ARCHITECTURE

- Unified components: Logger, OutputWriter, APIClient, Schema.
- Adapter pattern for external sources.
- Contract stages: extract → transform → validate → export.
- Prefer star schema: dims (documents, targets, assays, testitems) + fact (activity).

# IDP

- Idempotent runs with deterministic sorting and hashing; re-runs do not duplicate data.

# REFERENCE

See [docs/styleguide/08-etl-architecture.md](../../docs/styleguide/08-etl-architecture.md) for detailed documentation.
