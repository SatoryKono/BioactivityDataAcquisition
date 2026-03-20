# scripts/schema — Schema & Config Validation

Schema generation, validation contracts, and config invariants tooling.

## Unified Entry Point

```bash
python -m scripts.schema --help
python -m scripts.schema <command> [args...]
```

## Contract Source Of Truth

- Shared config-governance constants live in `src/bioetl/infrastructure/config/config_ci_contract.py`.
- `scripts/schema/check_config_invariants.py` and [test_config_ci_invariants.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/architecture/test_config_ci_invariants.py) import the same active/retired/transitional contract from that module.
- `scripts/schema/validate_pipeline_configs.py` is an officially supported compatibility wrapper around the canonical validator in `docs/00-project/ai/agents/scripts/py-config-bot-2.py`.
- Wrapper and canonical validator must not drift in behavior; if the validation contract changes, update the shared module first, then the docs.

## Commands

| Command | Script | Description |
|---------|--------|-------------|
| `check-invariants` | `check_config_invariants.py` | Validate config CI invariants (naming, schemas, auth, keys) |
| `check-config-paths` | `lint_config_paths.py` | Check for legacy dq/filter config path references |
| `generate-pipeline` | `generate_pipeline_schema.py` | Generate pipeline JSON schema |
| `generate-artifacts` | `generate_schema_artifacts.py` | Generate schema artifacts |
| `generate-pubtype` | `generate_publication_type_classification_artifacts.py` | Generate publication type classification artifacts |
| `generate-contracts` | `generate_contracts.py` | Generate contracts |
| `validate-configs` | `validate_pipeline_configs.py` | Validate unified pipeline YAML configs against JSON Schema |
| `analyze-gaps` | `config_gap_analysis.py` | Config gap analysis between configs and code |

## When to Use

| Command | When | Trigger |
|---------|------|---------|
| `check-invariants` | After modifying any YAML config under `configs/`; validates naming, entity sections, auth, unknown keys | Pre-commit hook (on config changes) |
| `check-config-paths` | After modifying configs, source code, or docs; detects legacy `dq/`/`filter/` path references | Pre-commit hook |
| `generate-pipeline` | After changing `PipelineYamlConfig` or `CompositeConfigFileSchema` Pydantic models; use `--check` to verify freshness | Manual, after model changes |
| `generate-artifacts` | After changing domain models (enums, lookup tables) | Manual, after model changes |
| `generate-pubtype` | After changing publication type classification logic | Manual, after classification changes |
| `generate-contracts` | Before release; auto-generates JSON contracts from Pandera DataFrameModel schemas | Manual, pre-release |
| `validate-configs` | After editing any entity YAML config; validates against JSON Schema | Pre-commit hook (on config changes) |
| `analyze-gaps` | When adding new pipelines; identifies missing entity configs or inconsistencies | Manual, on-demand |
