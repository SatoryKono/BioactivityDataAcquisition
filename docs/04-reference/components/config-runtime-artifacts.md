______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Configuration Runtime Artifacts

## Overview

The Configuration Runtime Artifacts system captures immutable snapshots of pipeline configurations to ensure reproducibility, debugging, and change tracking. It provides a comprehensive framework for managing configuration state throughout the pipeline lifecycle.

## Core Concepts

### EffectiveConfigArtifact

An `EffectiveConfigArtifact` represents the complete, resolved configuration state at a specific point in time. It includes:

- All DQ contracts and policies
- Pipeline-specific configurations
- Environment settings
- Provenance information
- Cryptographic hash for change detection

```yaml
# Complete EffectiveConfigArtifact Example
effective_config:
  # Metadata
  version: "1.0.0"
  timestamp: "2024-03-25T14:30:00.123456Z"
  pipeline_name: "chembl_molecule_etl"
  execution_id: "abc-123-def-456"

  # Provenance
  provenance:
    git_commit: "a1b2c3d4e5f67890"
    git_branch: "main"
    git_status: "clean"
    build_timestamp: "2024-03-25T13:45:00Z"
    config_files:
      - "configs/providers/chembl.yaml"
      - "configs/entities/molecule.yaml"
      - "configs/composites/molecule_pipeline.yaml"

  # Environment
  environment:
    name: "production"
    region: "us-east-1"
    deployment_id: "prod-chembl-20240325"

  # DQ Contracts
  dq_contracts:
    - contract_id: "molecule_schema_validation"
      version: "2.1.0"
      hash: "a1b2c3d4e5f67890abcdef1234567890"
      disposition: "fail"
      rule_count: 12
      last_updated: "2024-03-20T10:15:00Z"

    - contract_id: "molecule_content_validation"
      version: "1.3.2"
      hash: "1234567890abcdefa1b2c3d4e5f67890"
      disposition: "warn"
      rule_count: 8
      last_updated: "2024-03-18T09:30:00Z"

    - contract_id: "cross_source_consistency"
      version: "1.0.5"
      hash: "fedcba0987654321fedcba0987654321"
      disposition: "quarantine"
      rule_count: 5
      last_updated: "2024-03-15T16:20:00Z"

  # Pipeline Configuration
  pipeline_config:
    sources: ["chembl", "pubchem", "bindingdb"]
    target_entity: "molecule"
    merge_strategy: "prioritize"
    batch_size: 1000
    parallel_workers: 8

    aggregation:
      group_by: ["molecule_id", "assay_type"]
      aggregations:
        mean_pchembl: {field: "pchembl_value", method: "mean"}
        count_assays: {field: "assay_id", method: "count"}

    cross_validation:
      pairs:
        - chembl: ["pubchem", "bindingdb"]
        - pubchem: ["chembl", "bindingdb"]
      rules:
        strict: ["molecule_id", "smiles"]
        lenient: ["assay_description"]

    field_priorities:
      molecule_id: {priority: 1, source: "chembl"}
      smiles: {priority: 1, source: "pubchem"}
      assay_type: {priority: 2, source: "chembl"}

  # Performance Settings
  performance:
    cache_ttl: 3600
    max_memory_mb: 4096
    timeout_seconds: 300
    retry_attempts: 3

  # Monitoring
  monitoring:
    metrics_enabled: true
    logging_level: "INFO"
    trace_sample_rate: 0.1

# Hash for change detection
hash: "a1b2c3...finalhash...7890"
```

## API Reference

### EffectiveConfigService

```python
from bioetl.domain.behavior.effective_config_service import EffectiveConfigService

service = EffectiveConfigService()
```

#### create_artifact(config: dict) -> EffectiveConfigArtifact

Creates an immutable configuration artifact from current configuration.

**Parameters:**

- `config`: Current pipeline configuration dictionary

**Returns:**

- `EffectiveConfigArtifact`: Immutable configuration snapshot

**Example:**

```python
artifact = service.create_artifact(
    {
        "pipeline_name": "chembl_molecule_etl",
        "sources": ["chembl", "pubchem"],
        "dq_contracts": [...],
    }
)
```

#### serialize_config(artifact: EffectiveConfigArtifact) -> str

Serializes configuration artifact to JSON string.

**Parameters:**

- `artifact`: EffectiveConfigArtifact to serialize

**Returns:**

- `str`: JSON serialized configuration

**Example:**

```python
json_string = service.serialize_config(artifact)
# Store in database or file system
```

#### deserialize_config(json_str: str) -> EffectiveConfigArtifact

Deserializes configuration artifact from JSON string.

**Parameters:**

- `json_str`: JSON serialized configuration

**Returns:**

- `EffectiveConfigArtifact`: Deserialized artifact

**Example:**

```python
artifact = service.deserialize_config(json_string)
```

#### compute_hash(artifact: EffectiveConfigArtifact) -> str

Computes cryptographic hash of configuration artifact.

**Parameters:**

- `artifact`: EffectiveConfigArtifact to hash

**Returns:**

- `str`: SHA-256 hash of configuration

**Example:**

```python
config_hash = service.compute_hash(artifact)
# Use for change detection and compatibility checking
```

#### is_checkpoint_compatible(saved_hash: str, current_config: dict) -> bool

Checks if saved checkpoint is compatible with current configuration.

**Parameters:**

- `saved_hash`: Hash of saved configuration
- `current_config`: Current configuration dictionary

**Returns:**

- `bool`: True if compatible, False otherwise

**Example:**

```python
compatible = service.is_checkpoint_compatible(
    saved_hash="a1b2c3...", current_config=current_config
)
if not compatible:
    # Handle incompatibility (reprocess data, notify user, etc.)
    pass
```

#### get_config_drift(saved_artifact: EffectiveConfigArtifact, current_artifact: EffectiveConfigArtifact) -> ConfigDriftReport

Analyzes differences between two configuration artifacts.

**Parameters:**

- `saved_artifact`: Previous configuration artifact
- `current_artifact`: Current configuration artifact

**Returns:**

- `ConfigDriftReport`: Detailed report of changes

**Example:**

```python
report = service.get_config_drift(old_artifact, new_artifact)
if report.has_changes():
    print(f"Configuration changed: {report.change_summary()}")
    for change in report.changes:
        print(f"  - {change.field}: {change.old_value} -> {change.new_value}")
```

### EffectiveConfigArtifact Methods

```python
artifact = service.create_artifact(config)
```

#### compute_hash() -> str

Computes the cryptographic hash of this artifact.

**Returns:**

- `str`: SHA-256 hash

**Example:**

```python
hash_value = artifact.compute_hash()
```

#### get_hash() -> str

Returns the pre-computed hash (if available).

**Returns:**

- `str`: Pre-computed hash or None

**Example:**

```python
hash_value = artifact.get_hash()
```

#### validate() -> bool

Validates the configuration artifact structure.

**Returns:**

- `bool`: True if valid, False otherwise

**Example:**

```python
if not artifact.validate():
    raise ValueError("Invalid configuration artifact")
```

#### get_metadata() -> dict

Returns metadata about the artifact.

**Returns:**

- `dict`: Metadata dictionary

**Example:**

```python
metadata = artifact.get_metadata()
print(f"Created: {metadata['timestamp']}")
print(f"Pipeline: {metadata['pipeline_name']}")
```

## Usage Patterns

### 1. Checkpoint Compatibility

```python
# Before processing data with saved checkpoint
def should_reprocess_data(saved_hash: str, current_config: dict) -> bool:
    """Check if data needs reprocessing due to config changes"""
    service = EffectiveConfigService()

    # Create artifact for current configuration
    current_artifact = service.create_artifact(current_config)
    current_hash = current_artifact.compute_hash()

    # Compare with saved hash
    if saved_hash != current_hash:
        print(f"Configuration changed: {saved_hash} -> {current_hash}")
        return True

    return False


# Usage in pipeline
if should_reprocess_data(saved_checkpoint_hash, current_config):
    print("⚠️  Configuration changed, reprocessing data...")
    reprocess_data()
else:
    print("✅ Configuration unchanged, using saved results")
    use_saved_results()
```

### 2. Configuration Versioning

```python
# Track configuration changes over time
def log_configuration_version(config: dict, context: dict):
    """Log configuration version for audit trail"""
    service = EffectiveConfigService()

    # Create artifact
    artifact = service.create_artifact(config)

    # Store in version history
    version_log = {
        "timestamp": artifact.metadata["timestamp"],
        "pipeline": artifact.metadata["pipeline_name"],
        "hash": artifact.compute_hash(),
        "environment": context.get("environment", "unknown"),
        "user": context.get("user", "system"),
        "config_size": len(service.serialize_config(artifact)),
    }

    # Write to version history database
    save_to_version_history(version_log)

    return version_log


# Usage during pipeline initialization
version_info = log_configuration_version(
    pipeline_config, {"environment": "production", "user": "pipeline-runner"}
)
print(f"Configuration version logged: {version_info['hash']}")
```

### 3. Debugging with Configuration Artifacts

```python
# Debug pipeline issues using configuration artifacts
def debug_with_artifact(issue_context: dict):
    """Create debug bundle with configuration artifact"""
    service = EffectiveConfigService()

    # Get current configuration
    current_config = get_current_pipeline_config()
    artifact = service.create_artifact(current_config)

    # Create debug bundle
    debug_bundle = {
        "issue_id": issue_context["issue_id"],
        "timestamp": issue_context["timestamp"],
        "configuration": {
            "artifact": service.serialize_config(artifact),
            "hash": artifact.compute_hash(),
            "metadata": artifact.get_metadata(),
        },
        "environment": get_environment_info(),
        "logs": get_relevant_logs(issue_context["time_range"]),
        "metrics": get_relevant_metrics(issue_context["time_range"]),
    }

    # Save debug bundle
    save_debug_bundle(debug_bundle)

    return debug_bundle


# Usage when debugging pipeline issues
try:
    run_pipeline()
except Exception as e:
    debug_bundle = debug_with_artifact(
        {
            "issue_id": f"error-{uuid.uuid4()}",
            "timestamp": datetime.now().isoformat(),
            "time_range": "PT1H",  # Last 1 hour
        }
    )
    print(f"🐛 Debug bundle created: {debug_bundle['issue_id']}")
    raise  # Re-raise exception after creating debug bundle
```

### 4. Configuration Rollback

```python
# Rollback to previous configuration
def rollback_configuration(target_hash: str):
    """Rollback pipeline configuration to previous version"""
    service = EffectiveConfigService()

    # Retrieve target configuration from history
    target_config_json = get_config_from_history(target_hash)
    if not target_config_json:
        raise ValueError(f"Configuration with hash {target_hash} not found")

    # Deserialize and validate
    target_artifact = service.deserialize_config(target_config_json)
    if not target_artifact.validate():
        raise ValueError("Target configuration is invalid")

    # Apply rollback
    current_config = get_current_pipeline_config()
    current_artifact = service.create_artifact(current_config)

    # Log rollback event
    log_rollback_event(
        {
            "from_hash": current_artifact.compute_hash(),
            "to_hash": target_hash,
            "timestamp": datetime.now().isoformat(),
            "user": get_current_user(),
        }
    )

    # Apply new configuration
    apply_pipeline_config(target_artifact)

    return {
        "success": True,
        "from_hash": current_artifact.compute_hash(),
        "to_hash": target_hash,
        "timestamp": datetime.now().isoformat(),
    }


# Usage for configuration rollback
rollback_result = rollback_configuration("a1b2c3...previous_hash...")
print(f"🔄 Configuration rolled back to: {rollback_result['to_hash']}")
```

## Configuration Management Best Practices

### 1. Immutable Configuration

**Principle**: Treat configuration as immutable once deployed

```python
# ✅ GOOD: Create new artifact for each change
config_v1 = {"version": "1.0", "batch_size": 1000}
artifact_v1 = service.create_artifact(config_v1)

config_v2 = {"version": "1.1", "batch_size": 2000}  # Changed
artifact_v2 = service.create_artifact(config_v2)  # New artifact

# ❌ BAD: Modify existing configuration
config_v1["batch_size"] = 2000  # Don't do this!
```

### 2. Hash-Based Identification

**Principle**: Use cryptographic hashes to identify configurations

```python
# ✅ GOOD: Use hash for references
config = get_current_config()
artifact = service.create_artifact(config)
config_hash = artifact.compute_hash()

# Store reference by hash
save_checkpoint(config_hash, pipeline_results)

# Later retrieve by hash
results = load_checkpoint(config_hash)
```

### 3. Configuration History

**Principle**: Maintain complete history of all configurations

```python
# ✅ GOOD: Log every configuration change
def on_config_change(new_config: dict):
    artifact = service.create_artifact(new_config)

    # Store in history database
    save_to_config_history(
        {
            "hash": artifact.compute_hash(),
            "timestamp": datetime.now().isoformat(),
            "config": service.serialize_config(artifact),
            "user": get_current_user(),
            "context": get_change_context(),
        }
    )


# Call on every configuration change
on_config_change(new_pipeline_config)
```

### 4. Compatibility Checking

**Principle**: Always check compatibility before using saved results

```python
# ✅ GOOD: Check compatibility before using checkpoint
def safe_load_checkpoint(checkpoint_hash: str):
    current_config = get_current_pipeline_config()
    service = EffectiveConfigService()

    if service.is_checkpoint_compatible(checkpoint_hash, current_config):
        return load_checkpoint(checkpoint_hash)
    else:
        print("⚠️  Checkpoint incompatible, reprocessing...")
        return reprocess_data()


# Always use safe loading
data = safe_load_checkpoint(saved_hash)
```

## Performance Optimization

### Caching Strategies

```python
# Cache configuration artifacts to avoid repeated parsing
from functools import lru_cache


@lru_cache(maxsize=100)
def get_cached_artifact(config_dict: frozenset) -> EffectiveConfigArtifact:
    """Cache artifacts based on frozen config dictionary"""
    service = EffectiveConfigService()
    # Convert dict to frozenset for hashability
    frozen_config = frozenset(config_dict.items())
    return service.create_artifact(dict(frozen_config))


# Usage
config = {"batch_size": 1000, "sources": ["chembl"]}
artifact = get_cached_artifact(frozenset(config.items()))
```

### Batch Processing

```python
# Process multiple configurations efficiently
def process_config_batch(configs: list) -> list:
    """Process batch of configurations with shared resources"""
    service = EffectiveConfigService()
    results = []

    for config in configs:
        try:
            artifact = service.create_artifact(config)
            results.append(
                {
                    "config": config,
                    "artifact": artifact,
                    "hash": artifact.compute_hash(),
                    "valid": artifact.validate(),
                }
            )
        except Exception as e:
            results.append(
                {
                    "config": config,
                    "error": str(e),
                    "artifact": None,
                    "hash": None,
                    "valid": False,
                }
            )

    return results


# Usage
batch_results = process_config_batch([config1, config2, config3])
```

## Troubleshooting

### Common Issues and Solutions

#### Issue: Configuration Hash Mismatch

**Symptoms:**

- Checkpoint compatibility failures
- "Configuration changed" warnings
- Unexpected reprocessing

**Solutions:**

1. **Regenerate Artifacts**:

```python
# Force regenerate both artifacts and compare
current_artifact = service.create_artifact(current_config)
saved_artifact = service.deserialize_config(saved_json)

current_hash = current_artifact.compute_hash()
saved_hash = saved_artifact.compute_hash()

print(f"Current: {current_hash}")
print(f"Saved: {saved_hash}")
```

2. **Check for Uncommitted Changes**:

```bash
# Check git status for uncommitted config changes
git status configs/
```

3. **Review Migration Status**:

```python
from bioetl.domain.behavior.phased_migration_support import (
    PhasedMigrationCoordinator,
)

service = PhasedMigrationCoordinator()
status = service.get_current_migration_status()
print(f"Current phase: {status.current_phase}")
print(f"Migration warnings: {status.migration_warnings}")
```

#### Issue: Serialization Errors

**Symptoms:**

- `JSONSerializationError`
- Corrupted configuration artifacts
- Deserialization failures

**Solutions:**

1. **Validate Before Serialization**:

```python
artifact = service.create_artifact(config)
if not artifact.validate():
    raise ValueError("Invalid configuration, cannot serialize")

json_string = service.serialize_config(artifact)
```

2. **Use Canonical JSON**:

```python
# Ensure consistent serialization
import json


def canonical_json(obj: dict) -> str:
    """Serialize with consistent formatting"""
    return json.dumps(obj, sort_keys=True, indent=2, separators=(",", ": "))


config_json = canonical_json(config_dict)
```

3. **Handle Large Configurations**:

```python
# For large configs, use streaming or chunked processing
CHUNK_SIZE = 1024 * 1024  # 1MB chunks


def serialize_large_config(artifact: EffectiveConfigArtifact, file_path: str):
    """Serialize large config to file in chunks"""
    json_str = service.serialize_config(artifact)

    with open(file_path, "w") as f:
        for i in range(0, len(json_str), CHUNK_SIZE):
            f.write(json_str[i : i + CHUNK_SIZE])
```

#### Issue: Performance Degradation

**Symptoms:**

- Slow configuration loading
- High memory usage
- Pipeline delays

**Solutions:**

1. **Enable Caching**:

```python
# Cache frequently used configurations
from functools import lru_cache


@lru_cache(maxsize=50)
def get_cached_config(config_id: str) -> EffectiveConfigArtifact:
    config = load_config_from_database(config_id)
    service = EffectiveConfigService()
    return service.create_artifact(config)
```

2. **Lazy Loading**:

```python
# Load configuration only when needed
def get_config_lazy(config_id: str):
    if not hasattr(get_config_lazy, "cache"):
        get_config_lazy.cache = {}

    if config_id not in get_config_lazy.cache:
        get_config_lazy.cache[config_id] = load_config_from_database(config_id)

    return get_config_lazy.cache[config_id]
```

3. **Optimize Validation**:

```python
# Skip validation for trusted configurations
artifact = service.create_artifact(config, validate=False)
# Manual validation when needed
if not artifact.validate():
    raise ValueError("Invalid configuration")
```

## Related Components

- [DQ Contract System](dq-contract-system.md)
- [Phased Migration Support](phased-migration.md)
- [Composite Validation Service](composite-validation-service.md)
- [Observability Architecture](../../02-architecture/decisions/ADR-017-observability-architecture.md)

## Revision History

- **1.0** (2024-03-25): Initial documentation
- **1.1** (2024-03-28): Added usage patterns and examples
- **1.2** (2024-04-01): Incorporated performance optimization section
