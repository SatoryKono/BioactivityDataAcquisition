# Extending BioETL: Providers and Pipelines

*Synchronized with RULES.md v5.23 | Updated: 2026-03-03*

This document is the governance playbook for extending BioETL.

Canonical guides:
- [Add a new provider](../../03-guides/add-new-source.md)
- [Add pipeline for existing provider](../../03-guides/add-pipeline-existing-source.md)
- [Pipeline configuration](../../03-guides/pipeline-configuration.md)

Canonical templates:
- [Unified entity config template](../../04-reference/templates/config.yaml.tpl)
- [Provider source config template](../../04-reference/templates/provider.yaml.tpl)
- [Adapter template](../../04-reference/templates/source_adapter.py.tpl)
- [Transformer template](../../04-reference/templates/pipeline.py.tpl)
- [Pipeline factory registration template](../../04-reference/templates/factory.py.tpl)

---

## 1. Extension Paths

Choose one path:

1. New provider + first entity pipeline.
2. New entity pipeline for existing provider.

Both paths require:
- config updates under `configs/`
- composition registration updates
- tests + docs sync

---

## 2. Mandatory Artifacts

### 2.1 New provider

- `configs/providers/{provider}.yaml`
- `src/bioetl/infrastructure/adapters/{provider}/client.py`
- `src/bioetl/composition/providers/registration.py` updates
- at least one entity pipeline (`configs/entities/{provider}/{entity}.yaml` + transformer + registry)

### 2.2 New pipeline (existing provider)

- `configs/entities/{provider}/{entity}.yaml`
- transformer under `src/bioetl/application/pipelines/{provider}/`
- `register_all_transformers()` entry
- `PIPELINE_CONFIGS` entry in `pipeline_factories.py`
- Silver schema + Gold contract exports

---

## 3. Governance Rules

MUST:
- follow snake_case naming for provider/entity/pipeline IDs
- keep unified entity config sections complete (`pipeline/schema/quality/filters/contracts`)
- keep provider/entity values consistent between top-level and `pipeline.*`
- use constructor DI, no concrete dependency creation in domain/application
- register pipelines declaratively through `PIPELINE_CONFIGS`

MUST NOT:
- add legacy config-tree folders for pipelines/sources/schemas in the config root
- add `BasePipeline` subclasses for standard provider pipelines (use `GenericPipeline` + transformer)
- keep secrets in YAML/config files

---

## 4. Required Validation

Run before PR:

```bash
python scripts/validate_pipeline_configs.py --verbose
python -m pytest tests/architecture/test_registry_contracts.py -q
python -m pytest tests/architecture/test_source_config_usage.py -q
```

Then run targeted unit tests for changed provider/pipeline.

---

## 5. Review Checklist

- [ ] Provider/entity names follow naming policy.
- [ ] Unified entity config added and validated.
- [ ] Provider config updated (`entities`, `entity_notes`, rate limits).
- [ ] Transformer implemented with DI and deterministic identity/hash.
- [ ] `transformer_factory.py` updated.
- [ ] `pipeline_factories.py` updated (`PIPELINE_CONFIGS`, imports).
- [ ] Silver/Gold schemas updated and exported.
- [ ] Unit/integration docs updated.
