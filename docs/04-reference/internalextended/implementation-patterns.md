# Implementation Patterns

*Status: Active | Class: internal | Last Updated: 2026-04-24*

## Overview

This document describes common implementation patterns used in the internal/extended material. These patterns provide consistency and maintainability across the codebase.

## Registry Pattern

### Purpose

The registry pattern is used to manage collections of related objects (providers, pipelines, services) with lookup and discovery capabilities.

### Implementation

```python
from typing import Dict, Type, Protocol

class Registry(TypedDict):
    name: str
    factory: Callable[..., Any]
    config_schema: Type[BaseModel]

class ProviderRegistry:
    """Registry for provider definitions and factory functions."""
    
    def __init__(self):
        self._providers: Dict[str, Registry] = {}
        self._aliases: Dict[str, str] = {}
    
    def register(self, name: str, factory: Callable, config_schema: Type[BaseModel], aliases: list[str] = None):
        """Register a provider with optional aliases."""
        self._providers[name] = {
            'name': name,
            'factory': factory,
            'config_schema': config_schema
        }
        
        if aliases:
            for alias in aliases:
                self._aliases[alias] = name
    
    def get(self, name: str) -> Registry:
        """Get provider registry entry by name or alias."""
        actual_name = self._aliases.get(name, name)
        return self._providers[actual_name]
    
    def list_providers(self) -> list[str]:
        """List all registered provider names."""
        return list(self._providers.keys())
```

### Usage Example

```python
# Registration
registry = ProviderRegistry()
registry.register('chembl', ChemblAdapterFactory, ChemblConfig, aliases=['ch', 'chembl_db'])

# Lookup
chembl_registry = registry.get('chembl')
adapter = chembl_registry['factory'](config)
```

## Factory Pattern

### Purpose

The factory pattern is used to create complex objects with dependencies, encapsulating the creation logic.

### Implementation

```python
class PipelineFactory:
    """Factory for creating pipeline instances."""
    
    def __init__(self, registry: ProviderRegistry, config_resolver: ConfigResolver):
        self.registry = registry
        self.config_resolver = config_resolver
    
    def create_pipeline(self, provider: str, entity_type: str, config: dict) -> Pipeline:
        """Create a pipeline instance."""
        # Resolve provider
        provider_registry = self.registry.get(provider)
        
        # Create data source
        data_source_config = self.config_resolver.resolve_data_source_config(config)
        data_source = provider_registry['factory'](data_source_config)
        
        # Create transformer
        transformer = self._create_transformer(provider, entity_type, config)
        
        # Assemble pipeline
        return Pipeline(data_source, transformer, config)
    
    def _create_transformer(self, provider: str, entity_type: str, config: dict) -> Transformer:
        """Internal: Create transformer instance."""
        # Transformer creation logic
        ...
```

### Usage Example

```python
factory = PipelineFactory(registry, config_resolver)
pipeline = factory.create_pipeline('chembl', 'activity', chembl_config)
```

## Adapter Pattern

### Purpose

The adapter pattern is used to standardize interactions with different external APIs through a common interface.

### Implementation

```python
class DataSourcePort(Protocol):
    """Standard interface for data sources."""
    
    async def fetch(self, limit: int | None = None) -> list[dict]:
        """Fetch records from the data source."""
        ...
    
    async def health_check(self) -> bool:
        """Check if the data source is available."""
        ...

class ChemblAdapter(DataSourcePort):
    """ChEMBL API adapter implementing DataSourcePort."""
    
    def __init__(self, config: ChemblConfig, http_client: HttpClient):
        self.config = config
        self.http_client = http_client
    
    async def fetch(self, limit: int | None = None) -> list[dict]:
        """Fetch records from ChEMBL API."""
        # ChEMBL-specific implementation
        ...
    
    async def health_check(self) -> bool:
        """Check ChEMBL API availability."""
        # ChEMBL-specific health check
        ...
```

### Usage Example

```python
# Use adapter through standard interface
async def process_data(source: DataSourcePort):
    if await source.health_check():
        records = await source.fetch(limit=100)
        # Process records
    else:
        # Handle unavailable source

# Works with any DataSourcePort implementation
chembl_adapter = ChemblAdapter(chembl_config, http_client)
await process_data(chembl_adapter)
```

## Configuration Pattern

### Purpose

The configuration pattern provides a consistent way to handle configuration across different components.

### Implementation

```python
class ConfigResolver:
    """Resolve and validate configuration for different components."""
    
    def __init__(self, schemas: Dict[str, Type[BaseModel]]):
        self.schemas = schemas
    
    def resolve(self, component_type: str, raw_config: dict) -> dict:
        """Resolve and validate configuration."""
        schema = self.schemas[component_type]
        
        # Apply defaults
        config = self._apply_defaults(component_type, raw_config)
        
        # Validate
        validated_config = schema(**config)
        
        return validated_config.dict()
    
    def _apply_defaults(self, component_type: str, config: dict) -> dict:
        """Internal: Apply component-specific defaults."""
        defaults = self._get_defaults(component_type)
        
        # Merge with defaults
        return {**defaults, **config}
```

### Usage Example

```python
resolver = ConfigResolver({
    'pipeline': PipelineConfig,
    'data_source': DataSourceConfig,
    'transformer': TransformerConfig
})

pipeline_config = resolver.resolve('pipeline', raw_pipeline_config)
```

## Related Documentation

- [Composition Layer Architecture](../../../02-architecture/05-composition-layer.md)
- [Design Patterns in BioETL](../../../02-architecture/design-patterns.md)
- [Internal/Extended Index](index.md)
