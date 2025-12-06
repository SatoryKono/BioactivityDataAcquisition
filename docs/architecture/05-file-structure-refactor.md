# 05 File Structure Refactor

## Scope and goals
- Fix current layout against target layered architecture (domain, application, infrastructure, interfaces).
- Keep public API (imports, CLI `bioetl`) stable via aliases where needed.
- Produce actionable move plan that can run incrementally without blocking ongoing work.

## Current layout (high level)
```
root/
  configs/ (pipelines, profiles, naming exceptions)
  docs/ (architecture, pipelines, reference, guides)
  src/bioetl/
    core/ (pipeline_base.py, contracts.py, models.py)
    pipelines/chembl/*/run.py, base.py, registry.py
    clients/chembl/* (request_builder.py, paginator.py, impl/http_client.py)
    services/chembl_extraction_service.py
    transform/, validation/, output/, logging/, schemas/, config/
    cli.py, __main__.py
  tests/ (mirrors core/clients/pipelines/etc.)
```
- Domain concepts are embedded in transform/validation/config without a dedicated `domain/` package.
- Infrastructure and orchestration live together in `core/`, `pipelines/chembl/base.py`, `services/chembl_extraction_service.py`.
- CLI (`bioetl`) and registries are at package root instead of under interfaces/application.

## Mapping to target layers
| Current module/folder | Target layer | Comment |
| --- | --- | --- |
| `core/pipeline_base.py`, `pipelines/chembl/base.py` | application | Orchestration/run lifecycle; needs separation from hashing/meta/hooks helpers.
| `pipelines/chembl/*/run.py` | interfaces/application | Pipeline entry points using use-cases; should depend on registries/services only.
| `clients/*`, `services/chembl_extraction_service.py` | infrastructure | HTTP clients, pagination, parsing.
| `transform/`, `validation/`, `schemas/`, `output/`, `logging/`, `config/` | infrastructure | Data shaping, schema registry, IO, logging, config resolution.
| `cli.py`, `__main__.py` | interfaces | CLI surface should be isolated from provider specifics.
| (absent) | domain | Domain models and pure rules to be introduced.

## Target structure (proposed)
```
src/bioetl/
  domain/
    entities/ (assay.py, activity.py, target.py, testitem.py, document.py)
    services/ (business_rules.py, keys.py)
  application/
    pipelines/ (pipeline_service.py, hooks.py, hashing.py)
    registries/ (pipeline_registry.py, provider_registry.py)
    mappers/
  infrastructure/
    clients/
      chembl/ (contracts.py, factories.py, impl/http_client.py, paginator.py, request_builder.py, response_parser.py)
      base/ (contracts.py, factories.py, impl/*, abc_registry.yaml, abc_impls.yaml)
    services/ (chembl_extraction_service.py)
    transform/
    validation/
    schemas/
    output/
    logging/
    config/
  interfaces/
    cli/ (cli.py, __main__.py, adapters)
    pipelines/chembl/* (thin run/adapter modules)
```
- Tests mirror the package layout: `tests/bioetl/<layer>/...` plus integration under `tests/integration/`.
- Docs keep existing directories; architecture index references this plan.

## Move plan (stepwise)
1) **Introduce layer shells**: add `domain/`, `application/`, `infrastructure/`, `interfaces/` packages with `__init__.py`; re-export existing modules via thin proxies to preserve imports.
2) **Move orchestration**: relocate `core/pipeline_base.py` to `application/pipelines/pipeline_service.py`; move hashing/meta/hooks helpers into dedicated modules; keep shim in `core/__init__.py` and `core/pipeline_base.py` importing from new path.
3) **Isolate CLI**: move `cli.py` and `__main__.py` to `interfaces/cli/`; keep stub modules in old locations importing the new CLI to retain `bioetl` entrypoint.
4) **Refine clients/services**: move `services/chembl_extraction_service.py` to `infrastructure/services/`; normalize `clients/chembl/*` under `infrastructure/clients/chembl/` while respecting ABC/Default/Impl policy and YAML registries; update imports/registry paths.
5) **Pipelines as adapters**: move `pipelines/chembl/*/run.py` under `interfaces/pipelines/chembl/*/run.py`, keeping thin adapters calling application use-cases; add deprecated imports in old paths for compatibility until tests/docs updated.
6) **Domain introduction**: create `domain/entities/*` and mappers in `application/mappers/`; gradually redirect transforms/validation to use domain models (non-breaking by staging optional conversion).
7) **Config and schemas**: move `config/` into `infrastructure/config/`; keep `config/__init__.py` as proxy; ensure schema registry paths updated.
8) **Tests and docs**: realign test paths with new layout; update docs and examples to reference new module paths; maintain compatibility layer until downstream changes land.

## Import/public-surface risks
- Dynamic imports via registry strings (`pipelines/registry.py`, `schemas/registry.py`) can break if module paths change; add proxy modules and update registry values in the same commit.
- CLI entrypoint (`bioetl`) depends on `bioetl.cli:cli`; preserve old path with an alias module until consumers migrate.
- YAML config values that embed module paths (e.g., ABC registries) must be updated atomically with file moves; consider temporary aliases in `bioetl/clients/base/__init__.py`.
- Tests referencing old paths should be updated together with proxies to avoid brittle imports; run full pytest after each wave of moves.
- Tools reading files from `configs/` or `docs/` by relative paths are sensitive to working directory; avoid relocating configuration roots.
