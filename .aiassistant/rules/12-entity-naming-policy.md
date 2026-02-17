---
trigger: model_decision
description: USE WHEN naming classes, functions, modules, pipelines, tests, or configs; enforce role suffixes and function prefixes
---

# Entity Naming Policy

> Scope:
>
> - USE WHEN naming classes, functions, modules, pipelines, tests, or configs
> - Use when editing files matching: `src/**/*.py`, `tests/**/*.py`, `configs/**/*.yaml`
>
> Canonical sources: RULES.md §2, `configs/naming_exceptions.yaml`

## BASIC RULES

- **Modules**: `^[a-z0-9_]+$` (snake_case)
- **Classes**: PascalCase, `^[A-Z][A-Za-z0-9]+$`
- **Functions**: snake_case, `^[a-z_][a-z0-9_]*$`
- **Constants**: UPPER_SNAKE_CASE, `^[A-Z][A-Z0-9_]*$`
- **Private**: leading `_`

## CLASS SUFFIXES (ROLES)

| Suffix | Usage | Example |
|--------|-------|---------|
| `Factory` | General factories | `PipelineFactory` |
| `Client` | API/service clients | `ChEMBLClient` |
| `Port`/`Protocol` | Domain contracts | `DataSourcePort` |
| `Service` | Application services | `ValidationService` |
| `Transformer` | Record transformers | `CompoundTransformer` |
| `Adapter` | Infrastructure adapters | `BaseHttpAdapter` |
| `Error` | Exceptions | `ValidationError` |
| `Schema` | Pandera/Pydantic schemas | `CompoundGoldSchema` |
| `Config` | Configuration objects | `RuntimeConfig` |
| `Extractor` | Field extractors | `AuthorExtractor` |
| `Parser` | Parsing utilities | `MedlineDateParser` |
| `Aggregator` | Composite aggregators | `EnricherAggregator` |
| `Recorder` | Metrics recorders | `BatchMetricsRecorder` |
| `Result` | Operation results | `ValidationResult` |
| `Mixin` | Behavior mixins | `HealthCheckMixin` |

Exceptions to suffix requirements are documented in `configs/naming_exceptions.yaml`
(domain entities, enums, value objects, TypedDicts, base classes).

## FUNCTION PREFIXES

- `get_` — cheap local reads
- `fetch_` — network/IO operations
- `iter_` — lazy generators/iterators
- `create_`/`build_`/`make_`/`default_` — object creation/factories
- `register_` — registry registration
- `resolve_`/`ensure_` — normalization/preparation
- `validate_`/`parse_`/`serialize_` — validation/parsing/serialization
- `on_` — callbacks/handlers
- `is_`/`has_`/`can_` — boolean checks

## PIPELINES

- Path: `src/bioetl/application/pipelines/<provider>/<entity>_transformer.py`
- Provider: `^[a-z0-9_]+$`
- Entity: `^[a-z0-9_]+$`

## TESTS

- Unit: `tests/unit/application/pipelines/<provider>/test_<entity>_transformer.py`
- Integration: `tests/integration/` or suffix `_integration.py`
- Architecture: `tests/architecture/`
- Golden: `tests/golden/test_<area>_golden.py`

## CONFIGS

- Files: `^[a-z0-9_]+.ya?ml$` in `configs/`
- Pipelines: `configs/pipelines/<provider>/<entity>.yaml`
- DQ rules: `configs/quality/entities/<provider>/<entity>.yaml`
- Filter rules: `configs/filters/entities/<provider>/<entity>.yaml`
- Keys inside YAML: lower_snake_case

## EXAMPLES

Valid:

- Class: `ChemblDataClient`, `DataSourcePort`, `ActivityTransformer`
- Function: `fetch_one()`, `iter_pages()`, `create_pipeline()`
- Module: `data_client.py`, `activity_transformer.py`
- Pipeline: `src/bioetl/application/pipelines/chembl/activity_transformer.py`
- Test: `tests/unit/application/pipelines/chembl/test_activity_transformer.py`

Invalid:

- Class: `chemblDataClient`, `Data_Client`
- Function: `FetchOne()`, `getData()`
- Module: `DataClient.py`, `data-client.py`

## REFERENCE

- [RULES.md §2](../../docs/00-project/RULES.md) — Canonical naming conventions
- [configs/naming_exceptions.yaml](../../configs/naming_exceptions.yaml) — Allowed exceptions
- [ai-selfreview-rules.md](../../.claude/rules/ai-selfreview-rules.md) §4 — NAME rules for self-review
