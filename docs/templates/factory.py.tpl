"""
Template for adding a pipeline factory in v5.1.
Location: src/bioetl/composition/factories/pipeline_factories.py
"""
from bioetl.application.pipelines.{{provider}}.{{entity}} import {{Provider}}{{Entity}}Pipeline
from bioetl.composition.factories.generic_factory import GenericPipelineFactory
from bioetl.infrastructure.schemas.silver import {{PROVIDER}}_{{ENTITY}}_SCHEMA
from bioetl.infrastructure.schemas.gold import {{Provider}}{{Entity}}GoldSchema

# 1. Define the factory instance
{{provider}}_{{entity}}_factory = GenericPipelineFactory(
    pipeline_name="{{provider}}_{{entity}}",
    pipeline_class={{Provider}}{{Entity}}Pipeline,
    provider="{{provider}}",
    silver_schema={{PROVIDER}}_{{ENTITY}}_SCHEMA,
    gold_schema={{Provider}}{{Entity}}GoldSchema, # Optional
)

# 2. Add to register_all_pipelines() function
def register_all_pipelines() -> None:
    # ... existing registrations ...
    PipelineRegistry.register_factory({{provider}}_{{entity}}_factory)