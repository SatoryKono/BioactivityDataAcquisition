"""Template for registering a pipeline in composition factories.

Location: src/bioetl/composition/factories/pipeline_factories.py
"""

# 1) Add imports near existing provider imports:
# from bioetl.application.pipelines.{{provider}}.{{entity}}_transformer import {{Provider}}{{Entity}}Transformer
# from bioetl.domain.contracts import {{Provider}}{{Entity}}GoldSchema
# from bioetl.domain.schemas.{{provider}}.{{entity}} import {{Provider}}{{Entity}}Schema
# from bioetl.infrastructure.schemas.silver import {{PROVIDER}}_{{ENTITY}}_SCHEMA

# 2) Add entry to PIPELINE_CONFIGS tuple:
PipelineFactoryConfig(
    pipeline_name="{{provider}}_{{entity}}",
    provider="{{provider}}",
    entity_type="{{entity}}",
    transformer_class={{Provider}}{{Entity}}Transformer,
    silver_schema={{PROVIDER}}_{{ENTITY}}_SCHEMA,
    gold_schema={{Provider}}{{Entity}}GoldSchema,
    pandera_silver_schema={{Provider}}{{Entity}}Schema,
    # data_source_provider="{{provider_override}}",  # optional
)

# 3) Register transformer in transformer_factory.py:
# register_transformer("{{provider}}", "{{entity}}", {{Provider}}{{Entity}}Transformer)
