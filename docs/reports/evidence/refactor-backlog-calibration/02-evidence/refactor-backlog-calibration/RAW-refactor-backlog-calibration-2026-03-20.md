# Raw Evidence: refactor-backlog-calibration

**Date:** 2026-03-21

## Commands

### Governance gates

```text
./.venv/Scripts/python.exe -m scripts.engineering.qa check-c901
Current violations: 0
Baseline violations: 7
New violations: 0
Resolved vs baseline: 7
Result: OK (no new C901 structural debt)
```

```text
./.venv/Scripts/python.exe -m scripts.engineering.qa check-naming --check
Total violations: 0
OK: No violations found. All naming conventions are followed.
```

```text
./.venv/Scripts/python.exe -m scripts.engineering.repo check-inventory --check
[FAIL] Scripts inventory drift detected:
configs/quality/scripts_inventory_manifest.json
Run with --update to refresh manifest.
```

```text
./.venv/Scripts/python.exe -m scripts.engineering.repo check-inventory
[INFO] scripts=189 active=89 unknown=14 orphan=80 legacy=6
```

### Composition hotspot sizing

```text
wc -l \
  src/bioetl/composition/providers/registration_biblio.py \
  src/bioetl/composition/providers/_registration_biblio_profiles.py \
  src/bioetl/composition/factories/services/pipeline_builder.py \
  src/bioetl/composition/bootstrap/runtime/composite_support_service_builders.py

282 src/bioetl/composition/providers/registration_biblio.py
100 src/bioetl/composition/providers/_registration_biblio_profiles.py
271 src/bioetl/composition/factories/services/pipeline_builder.py
226 src/bioetl/composition/bootstrap/runtime/composite_support_service_builders.py
```

### Provider registry runtime seam

```text
rg -n "ensure_providers_loaded|ensure_providers_loaded_fn" \
  src/bioetl/composition/_pipeline_execution.py \
  src/bioetl/composition/bootstrap/runtime/pipeline.py \
  src/bioetl/composition/factories/pipeline/runner.py \
  src/bioetl/composition/runtime_builders/runner_builder.py

src/bioetl/composition/_pipeline_execution.py:51:    ensure_providers_loaded()
src/bioetl/composition/runtime_builders/runner_builder.py:57:    ensure_providers_loaded_fn()
src/bioetl/composition/factories/pipeline/runner.py:86:            self._ensure_providers_loaded_fn()
src/bioetl/composition/bootstrap/runtime/pipeline.py:64:    ensure_providers_loaded()
```

## Referenced Guardrails

- `tests/architecture/test_compatibility_freeze_guards.py`
- `tests/architecture/test_provider_registry_decomposition.py`
- `tests/architecture/test_registry_contracts.py`
- `tests/architecture/test_domain_public_api.py`
- `tests/architecture/test_composite_cli_runtime_config_boundaries.py`
- `tests/unit/composition/factories/services/test_pipeline_record_processor_builder.py`
- `tests/unit/composition/factories/services/test_pipeline_builder_batch_executor.py`
- `docs/reports/evidence/provider-registry-runtime-ownership/SUMMARY.md`
- `docs/00-project/RULES.md`
- `docs/02-architecture/01-domain-layer.md`
