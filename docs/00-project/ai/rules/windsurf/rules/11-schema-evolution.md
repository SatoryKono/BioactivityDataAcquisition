---
trigger: glob
description: "BioETL schema evolution — contracts, deprecation, breaking changes"
globs:
  - "configs/**/*.yaml"
  - "src/**/schemas/**"
  - "docs/04-reference/contracts/**"
---

# Schema Evolution and Data Contracts

**Canonical references:** `AGENTS.md`, `docs/00-project/NORMATIVE_SOURCES.md`, `docs/00-project/RULES.md`, `docs/01-requirements/REQUIREMENTS.md`, `docs/02-architecture/decisions/`.

## Schema Drift Classification

| Drift | Severity | Action |
| ----- | -------- | ------ |
| New optional field | Info | Structured logging |
| Required field removed or type change | **Critical** | Block pipeline; owner + **48h SLA**; unresolved Critical blocks next release |

Canonical schema structure from unified entity configuration + typed annotations. Generated registries/Gold exports checked in CI for stale state.

## Breaking Change Protocol (MUST)

1. PR **MUST** include consumer-impact / migration note (changelog/ADR)
2. Update code schema, generated JSON contract, documentation, golden fixtures **in one change set**
3. Deprecation window: **14 days** before field removal
4. Update `CHANGELOG.md` for schema/column/CLI changes
5. Major migrations: version bump, compatibility window, dual-read/dual-write if needed, backfill, updated contract/golden tests

## Data Contracts

- Gold contracts: `docs/04-reference/contracts/gold/{provider}_{entity}_v{major}.{minor}.json`
- Version: `{provider}_{entity}_v{major}.{minor}` — minor = nullable add; major = remove/rename/type change
- Public Gold PKs: canonical names (`publication-id`, `target-id`, …) — not legacy aliases

## Delta PK Migration Order (MUST)

1. Add new canonical column
2. Backfill from legacy column
3. Dual-write window (canonical + alias)
4. Drop legacy only in **major** release

Skipping steps is a contract governance violation.

## Pandera Runtime Boundary (ADR-048)

- Domain schemas/contracts in `domain/schemas/`, `domain/contracts/`
- Runtime compat bootstrap: `composition.bootstrap.runtime.pipeline.apply_runtime_compatibility_patches` is retained as a no-op; removed Pandera-specific shims stay absent unless a new ADR permits them
- Import-time package `__init__` patching **MUST NOT**

## Rollback

- **Code/infrastructure**: manual per runbook — no `bioetl rollback` command in Local-Only runtime
- **Data DQ issues**: manual analysis + replay — DQ errors **MUST NOT** auto-rollback app version
- Document last known-good artifacts and compatibility checks

## Silent Changes Forbidden

No silent breaking changes to CLI/API/schema/storage semantics/hashing. Consumers **MUST** get migration guidance and verifiable acceptance criteria.
