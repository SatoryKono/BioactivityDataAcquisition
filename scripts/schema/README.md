# scripts/schema — Schema & Config Validation

Schema generation, validation contracts, and config invariants tooling.

## Unified Entry Point

```bash
python -m scripts.schema --help
python -m scripts.schema <command> [args...]
```

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
