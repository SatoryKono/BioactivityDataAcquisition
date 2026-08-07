# scripts/schema — Schema & Config Validation

Schema generation, validation contracts, and config invariants tooling.


## Package layout

```
scripts/schema/
├── validation/   # config validation and path/optionality gates
├── generation/   # schema/contracts/codegen artifact generators
├── analysis/     # config matrix, unified map, field diagnostics
├── __main__.py   # unified CLI: python -m scripts.schema <command>
└── README.md
```

Public entrypoint remains `python -m scripts.schema <command>` (stable command names).

## Unified Entry Point

```bash
python -m scripts.schema --help
python -m scripts.schema <command> [args...]
```

## Contract Source Of Truth

- Shared config-governance constants live in `src/bioetl/infrastructure/config/config_ci_contract.py`.
- `scripts/schema/validation/check_config_invariants.py` and [test_config_ci_invariants.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/architecture/test_config_ci_invariants.py) import the same active/retired/transitional contract from that module.
- `check-invariants` is also the fail-fast YAML parse gate for all `configs/**/*.yaml` governance surfaces, including `configs/contracts/**/*.yaml`.
- `scripts/schema/validation/validate_pipeline_configs.py` is the canonical validator for `validate-configs`.
- `docs/00-project/ai/agents/scripts/py-config-bot-2.py` is a compatibility wrapper only; runtime behavior must be updated in `scripts/schema/validation/validate_pipeline_configs.py` first.

## Commands

| Command                      | Script                                                                 | Description                                                                            |
| ---------------------------- | ---------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| `check-invariants`           | `scripts/schema/validation/check_config_invariants.py`                            | Validate config CI invariants and YAML parse safety (naming, schemas, auth, keys)      |
| `check-required-fields`      | `scripts/schema/validation/check_required_filter_fields.py`                       | Validate `silver_filters.required_fields` cover explicit YAML required/not-null fields |
| `audit-optionality`          | `scripts/schema/validation/audit_effective_optionality.py`                        | Audit or validate `effective_optional_v1` derived from current config surface          |
| `check-config-paths`         | `scripts/schema/validation/lint_config_paths.py`                                  | Check for legacy dq/filter config path references                                      |
| `generate-pipeline`          | `scripts/schema/generation/generate_pipeline_schema.py`                           | Generate pipeline JSON schema                                                          |
| `generate-artifacts`         | `scripts/schema/generation/generate_schema_artifacts.py`                          | Generate schema artifacts                                                              |
| `generate-pubtype`           | `scripts/schema/generation/generate_publication_type_classification_artifacts.py` | Generate publication type classification artifacts                                     |
| `generate-protein-class`     | `scripts/schema/generation/generate_protein_class_l1_target_type_artifacts.py`      | Generate protein class L1 → target type artifacts                                      |
| `generate-typed-arrow`       | `scripts/schema/generation/generate_typed_arrow_schema_sources.py`                | Generate typed Arrow schema source modules                                             |
| `generate-contracts`         | `scripts/schema/generation/generate_contracts.py`                                 | Generate contracts                                                                     |
| `generate-config-matrix`     | `scripts/schema/analysis/generate_config_matrix.py`                             | Canonical entity/composite config comparison matrix generator                          |
| `generate-unified-map`       | `scripts/schema/analysis/generate_unified_schema_map.py`                        | Generate unified Bronze→Silver→Gold schema map CSV                                     |
| `generate-field-diagnostics` | `scripts/schema/analysis/generate_field_level_diagnostics.py`                   | Generate field-level schema drift diagnostics CSV                                      |
| `generate-field-spec`        | `scripts/schema/analysis/generate_field_transformation_spec.py`                 | Generate deterministic per-field transformation specification CSV                      |
| `validate-configs`           | `scripts/schema/validation/validate_pipeline_configs.py`                          | Validate unified pipeline YAML configs against JSON Schema                             |
| `validate-unified-configs`   | `scripts/schema/validation/validate_unified_configs.py`                           | Canonical structural unified-config validator retained for compatibility use cases     |
| `analyze-gaps`               | `scripts/schema/analysis/config_gap_analysis.py`                                | Config gap analysis between configs and code                                           |

## When to Use

| Command                      | When                                                                                                                                               | Trigger                                         |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| `check-invariants`           | After modifying any YAML config under `configs/`; validates parse safety, naming, entity sections, auth, unknown keys                              | Pre-commit hook (on config changes)             |
| `check-required-fields`      | After modifying entity YAML quality/filter sections; ensures explicit required/not-null YAML fields are listed in `silver_filters.required_fields` | CI/config regression gate                       |
| `audit-optionality`          | After changing config semantics or structural policy; audits and validates how `effective_optional_v1` resolves from current YAML/config signals   | CI/config regression gate, local contract audit |
| `check-config-paths`         | After modifying configs, source code, or docs; detects legacy `dq/`/`filter/` path references                                                      | Pre-commit hook                                 |
| `generate-pipeline`          | After changing `PipelineYamlConfig` or `CompositeConfigFileSchema` Pydantic models; use `--check` to verify freshness                              | Manual, after model changes                     |
| `generate-artifacts`         | After changing domain models (enums, lookup tables)                                                                                                | Manual, after model changes                     |
| `generate-pubtype`           | After changing publication type classification logic                                                                                               | Manual, after classification changes            |
| `generate-contracts`         | Before release; auto-generates JSON contracts from Pandera DataFrameModel schemas                                                                  | Manual, pre-release                             |
| `generate-config-matrix`     | When you need the older comparison matrix/report for entity and composite YAMLs through the canonical schema entrypoint                            | Manual, audit/reporting                         |
| `generate-unified-map`       | When you need one reproducible cross-layer inventory of entity configs, Silver schemas, and Gold contracts                                         | Manual, audit/reporting                         |
| `generate-field-diagnostics` | When you need per-field type drift, JSON storage pattern, nullable conflicts, or alias redundancy diagnostics across Bronze/Silver/Gold            | Manual, audit/reporting                         |
| `generate-field-spec`        | When you need deterministic per-field normalization specs with canonical JSON/DOI/PMID/date rules and conservative hash impact flags               | Manual, audit/reporting                         |
| `validate-configs`           | After editing any entity YAML config; validates against JSON Schema                                                                                | Pre-commit hook (on config changes)             |
| `validate-unified-configs`   | When you need the older structure-oriented unified entity config audit without switching validator semantics                                       | Manual, migration/compatibility use             |
| `analyze-gaps`               | When adding new pipelines; identifies missing entity configs or inconsistencies                                                                    | Manual, on-demand                               |

## `effective_optional_v1` Precedence

Runtime optionality currently resolves in this order:

1. Explicit `field_policy.<field>.optional`
1. Derived required signals from current config surface:
   - `silver_filters.required_fields`
   - DQ `required`
   - DQ `not_null`
   - DQ `key_nullability(nullable=false)`
1. Default optional

Validator distinction:

- `python -m scripts.schema validate-configs` is the maintained JSON Schema validator.
- `python -m scripts.schema validate-unified-configs` is the canonical entrypoint for the older standalone structural validator kept for compatibility use cases.
- `python -m scripts.schema generate-config-matrix` is the canonical entrypoint for the older comparison-matrix generator kept for compatibility use cases.
- Keep them separate until their contracts are intentionally unified.

This keeps structural policy compatible with today's configs while allowing
incremental migration toward explicit field-level policy overlays.
