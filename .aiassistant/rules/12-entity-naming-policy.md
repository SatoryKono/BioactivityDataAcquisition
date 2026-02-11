______________________________________________________________________

## trigger: model_decision description: USE WHEN naming classes, functions, modules, pipelines, tests, or configs; enforce role suffixes and function prefixes

# Entity Naming Policy

> Scope:
>
> - USE WHEN naming classes, functions, modules, pipelines, tests, or configs
> - Use when editing files matching: `src/**/*.py`, `tests/**/*.py`, `configs/**/*.yaml`

## BASIC RULES

- **Modules**: `^[a-z0-9_]+$` (snake_case)
- **Classes**: PascalCase, `^[A-Z][A-Za-z0-9]+$`
- **Functions**: snake_case, `^[a-z_][a-z0-9_]*$`
- **Constants**: UPPER_SNAKE_CASE, `^[A-Z][A-Z0-9_]*$`
- **Private**: leading `_`

## CLASS SUFFIXES (ROLES)

- `Factory` — general factories
- `ClientFactory` — client factories
- `DataClient` — contract implementations
- `Client` — general clients
- `Facade` — top-level facades
- `Registry` — registries
- `Adapter`/`Transport` — low-level adapters/transports
- `Protocol`/`ABC` — contracts
- `Config`/`Model`/`Params` — configuration/model types
- `Error` — exceptions
- `Impl` — implementations (e.g., `ChemblDataClientHTTPImpl`)

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

- Path: `src/bioetl/pipelines/<provider>/<entity>/<stage>.py`
- Provider: `^[a-z0-9_]+$`
- Entity: `^[a-z0-9_]+$`
- Stage: `extract`, `transform`, `validate`, `normalize`, `write`, `run`, `errors`, `descriptor`, `metrics`, `backfill`, `cleanup`

## TESTS

- Unit: `tests/bioetl/.../test_<module>.py`
- Pipeline: `tests/unit/application/pipelines/<provider>/test_<entity>_transformer.py`
- Integration: `tests/integration/` or suffix `_integration.py`
- Golden: `tests/golden/test_<area>_golden.py`

## CONFIGS

- Files: `^[a-z0-9_]+.ya?ml$` in `configs/`
- Pipelines: `configs/pipelines/<provider>/<entity>.yaml`
- Keys inside YAML: lower_snake_case

## EXAMPLES

Valid:

- Class: `ChemblDataClient`, `DataClientProtocol`, `ChemblDataClientHTTPImpl`
- Function: `fetch_one()`, `iter_pages()`, `default_chembl_data_client()`
- Module: `data_client.py`, `factories.py`
- Pipeline: `src/bioetl/pipelines/chembl/activity/extract.py`
- Test: `tests/bioetl/pipelines/chembl/activity/test_extract.py`

Invalid:

- Class: `chemblDataClient`, `Data_Client`
- Function: `FetchOne()`, `getData()`
- Module: `DataClient.py`, `data-client.py`

## REFERENCE

See `_docs/styleguide/new/02-new-entity-naming-policy.md` for detailed policy.
