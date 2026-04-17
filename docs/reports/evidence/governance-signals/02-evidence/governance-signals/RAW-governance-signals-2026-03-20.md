# Raw Governance Signals Snapshot

Date: 2026-03-21

## Method

- Checked current complexity governance with:
  - `./.venv/Scripts/python.exe -m scripts.engineering.qa check-c901`
- Read ratchet and registry policy from:
  - `configs/quality/debt_scorecard.yaml`
  - `configs/quality/architecture_metric_exemptions.yaml`
  - `tests/architecture/test_regression_metrics.py`
- Reused raw source-tree hotspot inventory from:
- `docs/reports/evidence/dependency-hotspots/02-evidence/dependency-hotspots/RAW-dependency-hotspot-metrics-2026-03-20.md`
- Captured ad hoc duplication snapshots with:
  - `./.venv/Scripts/python.exe -m pylint --disable=all --enable=duplicate-code src/bioetl/composition`
  - `./.venv/Scripts/python.exe -m pylint --disable=all --enable=duplicate-code src/bioetl/application`

## Current C901 Governance Output

```text
C901 Governance Report
  Current violations: 0
  Baseline violations: 7
  New violations: 0
  Resolved vs baseline: 7
  Folder budgets:
    - src/bioetl/application: 0/4
    - src/bioetl/composition: 0/1
    - src/bioetl/infrastructure: 0/1
    - src/bioetl/interfaces: 0/1

Result: OK (no new C901 structural debt)
```

## Size-Hotspot Snapshot Reused From Existing Evidence

From `RAW-dependency-hotspot-metrics-2026-03-20.md`:

- Total Python files under `src/bioetl`: `1235`
- Files `>10 KB`: `82`
- Files `>350 LOC`: `10`
- Files exceeding both thresholds: `10`

Layer distribution for files `>10 KB`:

- `application`: `31`
- `infrastructure`: `28`
- `composition`: `13`
- `domain`: `6`
- `interfaces`: `4`

Layer distribution for files `>350 LOC`:

- `infrastructure`: `5`
- `application`: `3`
- `interfaces`: `2`
- `composition`: `0`
- `domain`: `0`

## Scorecard / Ratchet Facts

From `configs/quality/debt_scorecard.yaml`:

- Enforceable baseline:
  - `file_size_limits: 0`
  - `function_complexity: 0`
- Historical baseline:
  - `file_size_limits: 6`
  - `function_complexity: 2`
- `baseline_policy.enforceable_section: baseline`
- `baseline_policy.registry_sync_source: baseline`
- Burn-down priority registries:
  - `file_size_limits`
  - `class_size`
  - `god_object`
- Named hotspot budget:
  - `core_orchestration`
  - `path_prefixes: src/bioetl/application/core/`
  - `registry_budgets.file_size_limits: 1`
  - `registry_budgets.class_size: 1`
  - `registry_budgets.god_object: 1`

From `configs/quality/architecture_metric_exemptions.yaml`:

- `file_size_limits: {}`
- `function_complexity: {}`
- only `god_object` currently contains one entry (`ProviderRegistry`)

From `tests/architecture/test_regression_metrics.py`:

- `test_file_size_exemption_count()` compares actual `file_size_limits` registry count to `_resolve_registry_budget("file_size_limits")`
- `test_scorecard_baseline_matches_exemption_registry()` asserts registry sync is anchored to `baseline`, not `historical_baseline`
- `test_scorecard_hotspot_budgets_cover_priority_registries()` requires named hotspot budgets to cover burn-down priority registries

## Duplication Governance Coverage

From `Makefile`:

```make
check-duplication:
	$(RUN) pylint --disable=all --enable=duplicate-code src/bioetl/infrastructure/adapters
```

There is no matching default duplication target for `src/bioetl/composition` or `src/bioetl/application`.

## Ad Hoc Duplication Snapshots

### Composition

- `R0801` occurrences counted from the scan output: `31`
- Representative duplicate clusters:
  - `composition._services` vs `composition.services_api`
  - `composition.providers._creation` vs `composition.providers.provider_registry`
  - `composition.factories.pipeline.assembler` vs `composition.factories.pipeline.factory_method_helpers`
  - `composition.bootstrap.runtime.composite_bootstrap_builders` vs `composition.bootstrap.runtime.runtime_basics`

### Application

- `R0801` occurrences counted from the scan output: `88`
- Representative duplicate clusters:
  - `application.core.batch_transformer_orchestration` vs `application.core.transformer_runtime.orchestration`
  - `application.pipelines.uniprot.extractors._comment_facets` vs `application.pipelines.uniprot.transformer_business_data_mixin`
  - `application.core.publication_term_extraction_mixin` vs `application.core.publication_term_filtering_mixin`
  - `application.composite.runner_pkg.runner_stage_support_mixin` vs `application.composite.runner_pkg.runner_stage_support_types`

## Notes

- The size-hotspot inventory and the file-size ratchet are related but not identical controls.
- The current duplication evidence for `composition` and `application` is a live snapshot, not a time-series trend with an enforceable budget.
