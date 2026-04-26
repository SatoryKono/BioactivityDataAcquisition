______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Phased Migration Support

## Overview

The Phased Migration Support system enables safe, controlled adoption of breaking changes in the BioETL pipeline. It provides tools for managing backward compatibility, version transitions, and gradual rollout of new features.

## Core Concepts

### Migration Phase Configuration

```python
from dataclasses import dataclass
from typing import Literal, Optional


@dataclass(frozen=True)
class MigrationPhaseConfig:
    """Configuration for a migration phase."""

    # Unique identifier for this phase
    phase_name: str

    # Version range for this phase
    start_version: str
    end_version: Optional[str] = None  # None means current phase

    # Compatibility characteristics
    backward_compatible: bool = True

    # How to transition to this phase
    migration_strategy: Literal["immediate", "gradual", "optional"] = "gradual"

    # What to do when issues arise
    fallback_behavior: Literal["warn", "error", "silent"] = "warn"
```

### Version Comparison

```python
def version_compare(v1: str, v2: str) -> int:
    """
    Compare semantic versions (-1 if v1<v2, 0 if equal, 1 if v1>v2).

    Handles different version lengths (e.g., "1.2" vs "1.2.3").
    Missing components are treated as zero.

    Args:
        v1: First version string
        v2: Second version string

    Returns:
        -1 if v1 < v2, 0 if equal, 1 if v1 > v2

    Examples:
        version_compare("1.2", "1.2.3")  # Returns -1 (1.2.0 < 1.2.3)
        version_compare("2.0", "1.9.9") # Returns 1 (2.0.0 > 1.9.9)
        version_compare("1.0", "1.0")   # Returns 0 (equal)
    """
    # Implementation handles:
    # - Different number of components
    # - Non-numeric components
    # - Pre-release versions
    # - Build metadata
    pass
```

## API Reference

### PhasedMigrationSupportService

```python
from bioetl.domain.services.phased_migration_support import (
    PhasedMigrationSupportService,
)

service = PhasedMigrationSupportService()
```

#### get_current_migration_status() -> MigrationStatus

Gets the current migration phase and version information.

**Returns:**

- `MigrationStatus`: Current migration status

**Example:**

```python
status = service.get_current_migration_status()
print(f"Current phase: {status.current_phase}")
print(f"Current version: {status.current_version}")
print(f"Supported phases: {status.supported_phases}")
print(f"Migration warnings: {status.migration_warnings}")
```

#### check_backward_compatibility(config: dict, target_phase: Optional[str] = None) -> dict

Checks if a configuration is backward compatible with a target phase.

**Parameters:**

- `config`: Configuration dictionary to check
- `target_phase`: Optional target phase name (default: current phase)

**Returns:**

- `dict`: Compatibility issues (empty if compatible)

**Example:**

```python
config = {"aggregation": {"group_by": ["field1"]}}
issues = service.check_backward_compatibility(config, "v1.1")

if issues:
    print(f"⚠️  Compatibility issues: {issues}")
    # Handle issues (warn user, apply fallbacks, etc.)
else:
    print("✅ Configuration is backward compatible")
```

#### apply_migration_fallback(config: dict, target_phase: str, fallback_behavior: Literal["warn", "error", "silent"] = "warn") -> tuple[dict, list]

Applies migration fallbacks to make configuration compatible with target phase.

**Parameters:**

- `config`: Configuration dictionary to migrate
- `target_phase`: Target phase name
- `fallback_behavior`: How to handle fallback issues

**Returns:**

- `tuple[dict, list]`: (modified_config, warnings)

**Example:**

```python
config = {"aggregation": {}}  # Missing required fields

modified_config, warnings = service.apply_migration_fallback(
    config, "v1.0", fallback_behavior="warn"
)

if warnings:
    print(f"⚠️  Applied fallbacks: {warnings}")

# Use modified config
process_pipeline(modified_config)
```

#### get_migration_guide(from_phase: str, to_phase: str) -> dict

Generates a migration guide between two phases.

**Parameters:**

- `from_phase`: Source phase name
- `to_phase`: Target phase name

**Returns:**

- `dict`: Migration guide with steps and considerations

**Example:**

```python
guide = service.get_migration_guide("v1.0", "v1.1")

print("Migration Guide:")
print(f"Steps: {guide['steps']}")
print(f"Breaking Changes: {guide['breaking_changes']}")
print(f"New Features: {guide['new_features']}")
print(f"Deprecations: {guide['deprecations']}")
```

#### get_supported_phases() -> list[dict]

Gets list of all supported migration phases.

**Returns:**

- `list[dict]`: List of supported phases with details

**Example:**

```python
phases = service.get_supported_phases()
for phase in phases:
    print(f"Phase: {phase['phase_name']}")
    print(f"  Version: {phase['start_version']} -> {phase['end_version'] or 'current'}")
    print(f"  Strategy: {phase['migration_strategy']}")
    print(f"  Fallback: {phase['fallback_behavior']}")
```

### MigrationStatus

```python
@dataclass(frozen=True)
class MigrationStatus:
    """Current migration status information."""

    current_phase: str  # Current migration phase
    supported_phases: list[str]  # All supported phase names
    current_version: str  # Current version string
    migration_warnings: list[str]  # Any migration warnings
    is_migration_mode: bool = False  # Whether in active migration
```

## Usage Patterns

### 1. Safe Configuration Migration

```python
# Migrate configuration safely between versions
def safe_migrate_config(config: dict, target_version: str) -> dict:
    """Safely migrate configuration to target version"""
    service = PhasedMigrationSupportService()

    # Check current status
    status = service.get_current_migration_status()
    print(f"Migrating from {status.current_version} to {target_version}")

    # Check compatibility
    issues = service.check_backward_compatibility(config, target_version)

    if issues:
        print(f"⚠️  Compatibility issues found: {issues}")

        # Apply automatic fallbacks
        modified_config, warnings = service.apply_migration_fallback(
            config, target_version, fallback_behavior="warn"
        )

        if warnings:
            print(f"⚠️  Applied fallbacks: {warnings}")

        return modified_config

    # Configuration is already compatible
    print("✅ Configuration is compatible")
    return config


# Usage during pipeline initialization
migrated_config = safe_migrate_config(original_config, "v1.1")
process_pipeline(migrated_config)
```

### 2. Version-Aware Pipeline Execution

```python
# Execute pipeline with version awareness
def run_pipeline_with_version_awareness(pipeline_config: dict):
    """Run pipeline with migration awareness"""
    service = PhasedMigrationSupportService()
    status = service.get_current_migration_status()

    print(f"Running pipeline in phase: {status.current_phase}")
    print(f"Version: {status.current_version}")

    # Check for migration warnings
    if status.migration_warnings:
        print(f"⚠️  Migration warnings: {status.migration_warnings}")

    # Apply phase-specific configurations
    if status.current_phase == "v1.0":
        # v1.0 specific logic
        pipeline_config = apply_v1_config(pipeline_config)
    elif status.current_phase == "v1.1":
        # v1.1 specific logic
        pipeline_config = apply_v1_1_config(pipeline_config)

    # Check compatibility with latest version
    latest_issues = service.check_backward_compatibility(pipeline_config, "latest")

    if latest_issues:
        print(f"⚠️  Configuration not ready for latest version: {latest_issues}")

    # Run pipeline
    return execute_pipeline(pipeline_config)


# Usage
results = run_pipeline_with_version_awareness(base_config)
```

### 3. Migration Testing

```python
# Test migration between versions
def test_migration(from_version: str, to_version: str, test_config: dict):
    """Test migration path between versions"""
    service = PhasedMigrationSupportService()

    print(f"Testing migration: {from_version} -> {to_version}")

    # Get migration guide
    guide = service.get_migration_guide(from_version, to_version)

    if guide["breaking_changes"]:
        print(f"⚠️  Breaking changes: {guide['breaking_changes']}")

    if guide["deprecations"]:
        print(f"ℹ️  Deprecations: {guide['deprecations']}")

    # Apply migration
    migrated_config, warnings = service.apply_migration_fallback(
        test_config, to_version, fallback_behavior="error"
    )

    # Validate migrated configuration
    validation_result = validate_config(migrated_config, to_version)

    if validation_result.is_valid():
        print("✅ Migration successful")
        return True, migrated_config
    else:
        print(f"❌ Migration failed: {validation_result.issues}")
        return False, validation_result.issues


# Test all migration paths
migration_tests = [
    ("v1.0", "v1.1", base_v1_config),
    ("v1.1", "v1.2", base_v1_1_config),
    ("v1.0", "v1.2", base_v1_config),  # Skip v1.1
]

for from_ver, to_ver, config in migration_tests:
    success, result = test_migration(from_ver, to_ver, config)
    if not success:
        print(f"❌ Migration {from_ver}->{to_ver} failed")
```

### 4. Rollback Planning

```python
# Plan rollback strategy
def create_rollback_plan(current_version: str) -> dict:
    """Create rollback plan for current version"""
    service = PhasedMigrationSupportService()

    # Get current status
    status = service.get_current_migration_status()

    # Determine fallback versions
    fallback_versions = []

    if status.current_phase == "v1.2":
        fallback_versions = ["v1.1", "v1.0"]
    elif status.current_phase == "v1.1":
        fallback_versions = ["v1.0"]

    # Create rollback plan
    plan = {
        "current_version": current_version,
        "fallback_versions": fallback_versions,
        "rollback_steps": [],
        "risk_assessment": "low",
    }

    # Add rollback steps for each fallback version
    for fallback_version in fallback_versions:
        guide = service.get_migration_guide(current_version, fallback_version)

        step = {
            "target_version": fallback_version,
            "breaking_changes": guide["breaking_changes"],
            "estimated_impact": "medium" if guide["breaking_changes"] else "low",
            "steps": guide["steps"],
        }

        plan["rollback_steps"].append(step)

        if guide["breaking_changes"]:
            plan["risk_assessment"] = "high"

    return plan


# Usage during deployment planning
rollback_plan = create_rollback_plan("v1.2")
print("Rollback Plan:")
print(f"Current: {rollback_plan['current_version']}")
print(f"Fallbacks: {rollback_plan['fallback_versions']}")
print(f"Risk: {rollback_plan['risk_assessment']}")

for i, step in enumerate(rollback_plan["rollback_steps"], 1):
    print(f"\nStep {i}: Rollback to {step['target_version']}")
    print(f"  Impact: {step['estimated_impact']}")
    print(f"  Breaking changes: {len(step['breaking_changes'])}")
```

## Migration Strategies

### Immediate Migration

**Use Case**: Critical security fixes, urgent bug fixes

**Characteristics**:

- All users migrate at once
- No backward compatibility
- Requires coordinated deployment

**Implementation**:

```python
# Force immediate migration
service = PhasedMigrationSupportService()

# Get current phase
status = service.get_current_migration_status()

if status.current_phase != "v2.0":
    # Apply immediate migration
    migrated_config = service.apply_migration_fallback(
        current_config, "v2.0", fallback_behavior="error"
    )

    # Deploy immediately
    deploy_pipeline(migrated_config)

    # No fallback period
    disable_old_versions()
```

### Gradual Migration

**Use Case**: Major feature releases, architectural changes

**Characteristics**:

- Phased rollout over weeks/months
- Both old and new versions supported
- Monitoring and feedback collection

**Implementation**:

```python
# Gradual migration with monitoring
service = PhasedMigrationSupportService()

# Phase 1: Enable new version
service.update_migration_phase(
    {
        "phase_name": "v2.0_gradual",
        "start_version": "2.0.0",
        "migration_strategy": "gradual",
        "fallback_behavior": "warn",
    }
)

# Phase 2: Monitor and collect feedback
monitoring_results = monitor_migration(
    {"old_version": "1.5.0", "new_version": "2.0.0", "duration": "P7D"}  # 7 days
)

# Phase 3: Analyze results
if monitoring_results["error_rate"] < 0.01:
    # Proceed with full migration
    complete_migration()
else:
    # Rollback or extend gradual period
    extend_gradual_period()

# Phase 4: Complete migration
service.complete_migration_phase("v2.0_gradual")
disable_old_versions()
```

### Optional Migration

**Use Case**: Experimental features, non-critical enhancements

**Characteristics**:

- Users opt-in to new version
- Old version remains fully supported
- No forced migration timeline

**Implementation**:

```python
# Optional migration with user choice
service = PhasedMigrationSupportService()

# Enable optional version
service.add_optional_version(
    {
        "version": "2.1.0",
        "description": "Experimental feature release",
        "migration_strategy": "optional",
        "fallback_behavior": "silent",
    }
)

# Let users choose version
user_preference = get_user_preference()

if user_preference == "experimental":
    # Use new version
    config = service.apply_migration_fallback(
        base_config, "2.1.0", fallback_behavior="silent"
    )
else:
    # Use stable version
    config = base_config

# Monitor adoption rate
adoption_rate = monitor_optional_adoption("2.1.0")

if adoption_rate > 0.5:  # 50%+ adoption
    # Consider promoting to stable
    consider_promotion_to_stable()
```

## Best Practices

### 1. Semantic Versioning

Follow semantic versioning for all configurations:

```python
# MAJOR.MINOR.PATCH
# - MAJOR: Breaking changes
# - MINOR: Backward-compatible features
# - PATCH: Backward-compatible bug fixes

versions = {
    "breaking": "2.0.0",  # Major version bump
    "feature": "1.5.0",  # Minor version bump
    "bugfix": "1.4.1",  # Patch version bump
}
```

### 2. Backward Compatibility

Always maintain backward compatibility within major versions:

```python
# ✅ GOOD: Add new optional fields
config_v2 = {
    **config_v1,  # Keep all v1 fields
    "new_feature": "disabled",  # New field with safe default
}

# ❌ BAD: Remove or rename fields
config_v2 = {
    # "old_field": removed  # Breaks compatibility!
    "renamed_field": value  # Breaks compatibility!
}
```

### 3. Deprecation Policy

Use formal deprecation process for removing features:

```python
# Deprecation timeline example
deprecation_plan = {
    "feature": "legacy_api",
    "deprecation_version": "1.5.0",  # First marked as deprecated
    "removal_version": "2.0.0",  # Will be removed in 2.0.0
    "replacement": "new_api",
    "warnings": [
        {
            "version": "1.5.0",
            "message": "legacy_api is deprecated, use new_api instead",
        },
        {"version": "1.6.0", "message": "legacy_api will be removed in 2.0.0"},
    ],
}
```

### 4. Migration Testing

Comprehensive testing for all migration paths:

```python
# Test matrix for migration
migration_tests = {
    "direct": {
        "from": "1.0.0",
        "to": "1.1.0",
        "type": "minor",
        "expected": "automatic",
    },
    "skip_version": {
        "from": "1.0.0",
        "to": "1.2.0",
        "type": "minor_skip",
        "expected": "automatic_with_warnings",
    },
    "major": {
        "from": "1.5.0",
        "to": "2.0.0",
        "type": "major",
        "expected": "manual_with_fallbacks",
    },
}

# Run all migration tests
for test_name, test_config in migration_tests.items():
    result = run_migration_test(test_config)
    assert result == test_config["expected"], f"{test_name} failed"
```

### 5. User Communication

Clear communication about migrations:

```python
# Migration announcement template
announcement = {
    "title": "Upcoming Migration to v2.0.0",
    "summary": "Major version update with breaking changes",
    "timeline": {
        "announcement": "2024-04-01",
        "testing_period": "2024-04-15 to 2024-05-15",
        "migration_date": "2024-05-30",
        "fallback_end": "2024-06-30",
    },
    "breaking_changes": [
        "Removed legacy_api endpoint",
        "Changed authentication mechanism",
    ],
    "migration_guide": {
        "steps": [
            "Update client libraries",
            "Test in staging environment",
            "Deploy to production",
        ],
        "resources": ["Migration documentation", "API reference", "Support contact"],
    },
    "support": {
        "email": "support@bioetl.org",
        "slack": "#migration-support",
        "office_hours": "Mon-Fri 9am-5pm UTC",
    },
}
```

## Performance Considerations

### Caching Migration Results

```python
# Cache migration checks to avoid repeated processing
from functools import lru_cache


@lru_cache(maxsize=100)
def check_migration_cached(config_hash: str, target_phase: str) -> dict:
    """Cached migration compatibility check"""
    service = PhasedMigrationSupportService()
    config = get_config_by_hash(config_hash)
    return service.check_backward_compatibility(config, target_phase)


# Usage
issues = check_migration_cached("abc123", "v1.1")
```

### Batch Migration

```python
# Process multiple configurations efficiently
def migrate_config_batch(configs: list, target_phase: str) -> list:
    """Migrate batch of configurations"""
    service = PhasedMigrationSupportService()
    results = []

    for config in configs:
        try:
            migrated, warnings = service.apply_migration_fallback(
                config, target_phase, fallback_behavior="warn"
            )
            results.append(
                {
                    "original": config,
                    "migrated": migrated,
                    "warnings": warnings,
                    "success": True,
                }
            )
        except Exception as e:
            results.append(
                {
                    "original": config,
                    "migrated": None,
                    "error": str(e),
                    "success": False,
                }
            )

    return results


# Usage
batch_results = migrate_config_batch(user_configs, "v1.1")
```

### Parallel Migration

```python
# Use threading for independent migrations
import concurrent.futures


def parallel_migrate(configs: list, target_phase: str, workers: int = 4) -> list:
    """Migrate configurations in parallel"""
    service = PhasedMigrationSupportService()

    def migrate_one(config):
        try:
            migrated, warnings = service.apply_migration_fallback(
                config, target_phase, fallback_behavior="warn"
            )
            return {
                "config": config,
                "migrated": migrated,
                "warnings": warnings,
                "success": True,
            }
        except Exception as e:
            return {"config": config, "error": str(e), "success": False}

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(migrate_one, configs))

    return results


# Usage for large-scale migrations
parallel_results = parallel_migrate(large_config_set, "v1.1", workers=8)
```

## Troubleshooting

### Common Migration Issues

#### Issue: Version Conflict

**Symptoms:**

- `VersionConflictError` during migration
- Incompatible configuration versions
- Pipeline failures after migration

**Solutions:**

1. **Check Migration Guide**:

```python
guide = service.get_migration_guide("v1.0", "v1.1")
print(f"Breaking changes: {guide['breaking_changes']}")
```

2. **Apply Fallbacks**:

```python
migrated_config, warnings = service.apply_migration_fallback(
    config, "v1.1", fallback_behavior="warn"
)
```

3. **Manual Intervention**:

```python
# Manually resolve conflicts
if warnings:
    for warning in warnings:
        if "field_renamed" in warning:
            config["new_field"] = config.pop("old_field")
```

#### Issue: Fallback Loop

**Symptoms:**

- Infinite fallback attempts
- Configuration oscillates between versions
- Migration never completes

**Solutions:**

1. **Set Fallback Limit**:

```python
max_attempts = 3
attempt = 0

while attempt < max_attempts:
    migrated, warnings = service.apply_migration_fallback(
        config, target_phase, fallback_behavior="warn"
    )

    if not warnings:
        break

    attempt += 1
    config = migrated

if attempt == max_attempts:
    raise RuntimeError("Migration failed after max fallback attempts")
```

2. **Manual Resolution**:

```python
# After max attempts, manually resolve
final_config = manual_resolve_conflicts(config)
```

#### Issue: Performance Degradation

**Symptoms:**

- Slow migration processing
- High CPU/memory usage
- Timeout errors

**Solutions:**

1. **Batch Processing**:

```python
# Process in batches
batch_size = 100
for i in range(0, len(configs), batch_size):
    batch = configs[i : i + batch_size]
    results = migrate_config_batch(batch, target_phase)
    process_results(results)
```

2. **Parallel Processing**:

```python
# Use parallel migration
results = parallel_migrate(large_config_set, target_phase, workers=8)
```

3. **Optimize Configuration**:

```python
# Remove unnecessary fields before migration
optimized_config = remove_deprecated_fields(config)
migrated = service.apply_migration_fallback(optimized_config, target_phase)
```

## Related Components

- [DQ Contract System](dq-contract-system.md)
- [Configuration Runtime Artifacts](config-runtime-artifacts.md)
- [Composite Validation Service](composite-validation-service.md)
- [Observability Architecture](../../02-architecture/decisions/ADR-017-observability-architecture.md)

## Revision History

- **1.0** (2024-03-25): Initial documentation
- **1.1** (2024-03-28): Added migration strategies and examples
- **1.2** (2024-04-01): Incorporated performance optimization section
