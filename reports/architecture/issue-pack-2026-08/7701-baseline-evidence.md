# #7701 Baseline evidence (2026-08-05)

Branch: `refactor/arch-ref-7701-7711`  
Evidence for ARCH-REF step 0 / GitHub issue **#7701**.

## Dependency map regen

- Command: `python -m scripts.engineering.qa report-dep-map`
- Outputs:
  - `docs/02-architecture/generated/module-dependency-map.md`
  - `docs/02-architecture/generated/module-dependency-map.json`
- Result: **layer policy violations = 0**
  (`summary.violations == 0`, `violations: []` in JSON)

## Family / hotspot baseline regen

- Command: `python -m scripts.engineering.qa report-family-baseline --update`
- Outputs:
  - `reports/quality/hotspot-family-baseline.json`
  - `reports/quality/hotspot-family-baseline.md`
- Result: artifacts rewritten successfully; scorecard-linked family budgets
  remain non-growing (no debt budget increases).

## Live removable-complexity residual (`measure_residual.py`)

Command:

```bash
source .venv/bin/activate && export PYTHONPATH=src:.
python reports/architecture/issue-pack-2026-08/measure_residual.py
```

| Family | Live `ge250` | Scorecard budget `files_ge_250_loc` | Fan-in budget | Headroom |
| --- | ---: | ---: | ---: | --- |
| `adapter_layer` (`src/bioetl/infrastructure/adapters/`) | **22** | **22** | 31 | at budget (flat, not over) |
| `composite_layer` (`src/bioetl/application/composite/`) | **19** | **21** | 25 | −2 under budget |

Adapter ge250 files (LOC rank, live):

```
 343 src/bioetl/infrastructure/adapters/health_check_mixin.py
 332 src/bioetl/infrastructure/adapters/http/client_retry_mixin.py
 317 src/bioetl/infrastructure/adapters/openalex/client_runtime_helpers.py
 309 src/bioetl/infrastructure/adapters/chembl/protein_classification_graph.py
 293 src/bioetl/infrastructure/adapters/base.py
 290 src/bioetl/infrastructure/adapters/pubchem/fetch_strategies.py
 284 src/bioetl/infrastructure/adapters/common/fetch_resilience_template.py
 281 src/bioetl/infrastructure/adapters/chembl/models_common.py
 280 src/bioetl/infrastructure/adapters/chembl/health.py
 275 src/bioetl/infrastructure/adapters/common/api_request_collector.py
 275 src/bioetl/infrastructure/adapters/chembl/client.py
 274 src/bioetl/infrastructure/adapters/openalex/client.py
 273 src/bioetl/infrastructure/adapters/pubmed/adapter.py
 271 src/bioetl/infrastructure/adapters/error_handling.py
 271 src/bioetl/infrastructure/adapters/crossref/client.py
 269 src/bioetl/infrastructure/adapters/openalex/cursor_flow.py
 268 src/bioetl/infrastructure/adapters/pubmed/models.py
 266 src/bioetl/infrastructure/adapters/uniprot/client.py
 261 src/bioetl/infrastructure/adapters/decorators/retry.py
 254 src/bioetl/infrastructure/adapters/chembl/entity_mapper.py
 253 src/bioetl/infrastructure/adapters/crossref/models.py
 251 src/bioetl/infrastructure/adapters/pubchem/models.py
```

Composite ge250 files (LOC rank, live):

```
 338 src/bioetl/application/composite/dependency_key_resolvers.py
 335 src/bioetl/application/composite/checkpoint/load_service.py
 328 src/bioetl/application/composite/_preflight_orchestration.py
 324 src/bioetl/application/composite/coordinator.py
 322 src/bioetl/application/composite/dependency_coordinator.py
 321 src/bioetl/application/composite/join_planner_helpers.py
 314 src/bioetl/application/composite/runner_pkg/runner_merge_stage_mixin.py
 300 src/bioetl/application/composite/dependency_joiner.py
 291 src/bioetl/application/composite/runner_pkg/runner_observability_mixin.py
 290 src/bioetl/application/composite/runner_pkg/runner.py
 280 src/bioetl/application/composite/column_service.py
 278 src/bioetl/application/composite/merger_orchestration.py
 276 src/bioetl/application/composite/checkpoint/_checkpoint_runtime.py
 273 src/bioetl/application/composite/runner_pkg/runner_stage_mixin.py
 273 src/bioetl/application/composite/lifecycle_observer_service.py
 271 src/bioetl/application/composite/cross_validator.py
 263 src/bioetl/application/composite/runner_pkg/runner_support_runtime.py
 260 src/bioetl/application/composite/preflight_validator.py
 257 src/bioetl/application/composite/runner_pkg/runner_support_mixin.py
```

## Guardrails observed

- No product behavior changes in this evidence step.
- No tech-debt budget increases (scorecard `removable_complexity` numbers not edited).
- Adapter/composite large refactors intentionally out of scope for this pack lane.

## Related pack work captured on the same branch

| Issue | Status notes |
| --- | --- |
| #7706 | Ports inventory generator + RULES sync + arch gate |
| #7708 | Composition API → factory map + public entrypoint freeze test |
| #7710 | Diagrams / architecture-index observability truth |
| #7711 | Scripts inventory hold-flat policy note |
