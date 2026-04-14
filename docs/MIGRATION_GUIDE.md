# Migration Guide: Compatibility Shims Deprecation

## Overview

This guide documents the deprecation of compatibility shims in the BioETL project. These shims were introduced to maintain backward compatibility during the transition to new naming conventions. They are now being deprecated in favor of the new, more consistent names.

## Deprecation Timeline

- **v1.x**: Deprecation warnings added (current version)
- **v2.0**: Complete removal of old names

## Deprecated Classes and Their Replacements

### 1. Checkpoint Management

**Deprecated:** `CheckpointManager`
**Use instead:** `CheckpointManagerService`

```python
# Old (deprecated)
from bioetl.application.core.lifecycle.checkpoint_manager import CheckpointManager
manager = CheckpointManager("run_type", "run_id", storage, resume=True)

# New (recommended)
from bioetl.application.core.lifecycle.checkpoint_manager import CheckpointManagerService
manager = CheckpointManagerService("run_type", "run_id", storage, resume=True)
```

### 2. Composite Checkpoint Management

**Deprecated:** `CompositeCheckpointManager`
**Use instead:** `CompositeCheckpointService`

```python
# Old (deprecated)
from bioetl.application.composite.checkpoint.service import CompositeCheckpointManager
manager = CompositeCheckpointManager("composite_name", "run_id", storage, logger)

# New (recommended)
from bioetl.application.composite.checkpoint.service import CompositeCheckpointService
manager = CompositeCheckpointService("composite_name", "run_id", storage, logger)
```

### 3. Preflight Validation

**Deprecated:** `CompositePreflightValidator`
**Use instead:** `CompositePreflightValidationService`

```python
# Old (deprecated)
from bioetl.application.composite.preflight_validator import CompositePreflightValidator
validator = CompositePreflightValidator(config, logger, metrics)

# New (recommended)
from bioetl.application.composite.preflight_validator import CompositePreflightValidationService
validator = CompositePreflightValidationService(config, logger, metrics)
```

### 4. Pipeline Runner

**Deprecated:** `CompositePipelineRunnerService`
**Use instead:** `CompositePipelineRunner`

```python
# Old (deprecated)
from bioetl.application.composite.runner_pkg.runner import CompositePipelineRunnerService
runner = CompositePipelineRunnerService(...)

# New (recommended)
from bioetl.application.composite.runner_pkg.runner import CompositePipelineRunner
runner = CompositePipelineRunner(...)
```

### 5. Deduplication

**Deprecated:** `EnricherDeduplicator`
**Use instead:** `EnricherDeduplicatorService`

```python
# Old (deprecated)
from bioetl.application.composite.deduplication import EnricherDeduplicator
deduplicator = EnricherDeduplicator(config, logger)

# New (recommended)
from bioetl.application.composite.deduplication import EnricherDeduplicatorService
deduplicator = EnricherDeduplicatorService(config, logger)
```

### 6. FSM State Helper

**Deprecated:** `FSMStateHelper`
**Use instead:** `FSMStateHelperService`

```python
# Old (deprecated)
from bioetl.application.composite.fsm_helper import FSMStateHelper
helper = FSMStateHelper(state, config)

# New (recommended)
from bioetl.application.composite.fsm_helper import FSMStateHelperService
helper = FSMStateHelperService(state, config)
```

### 7. Batch Metrics

**Deprecated:** `BatchMetricsRecorder`
**Use instead:** `BatchMetricsRecorderService`

```python
# Old (deprecated)
from bioetl.application.core.batch_metrics import BatchMetricsRecorder
recorder = BatchMetricsRecorder(logger, metrics)

# New (recommended)
from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
recorder = BatchMetricsRecorderService(logger, metrics)
```

### 8. Data Source Creator

**Deprecated:** `DataSourceCreatorPort`
**Use instead:** `DataSourceCreatorProtocol`

```python
# Old (deprecated)
from bioetl.composition.factories import DataSourceCreatorPort
port = DataSourceCreatorPort(...)

# New (recommended)
from bioetl.composition.factories import DataSourceCreatorProtocol
port = DataSourceCreatorProtocol(...)
```

## Migration Steps

### For Library Users

1. **Identify usage**: Search your codebase for imports of the deprecated classes
2. **Update imports**: Change imports to use the new class names
3. **Test**: Run your tests to ensure everything works with the new names
4. **Update CI**: Ensure your CI/CD pipeline doesn't use the old names

### For Library Maintainers

1. **Update internal code**: Replace all internal usage of old names with new ones
2. **Update tests**: Ensure all tests use the new names
3. **Update examples**: Update all documentation and examples
4. **Monitor usage**: Track deprecation warnings in production

## Automated Migration Tools

You can use the following script to help identify deprecated usage in your codebase:

```bash
# Find all usages of deprecated classes
grep -r "CheckpointManager\|CompositeCheckpointManager\|CompositePreflightValidator\|CompositePipelineRunnerService\|EnricherDeduplicator\|FSMStateHelper\|BatchMetricsRecorder\|DataSourceCreatorPort" your_project_dir/
```

## Support

If you encounter any issues during migration, please:
1. Check the deprecation warnings for specific guidance
2. Consult this migration guide
3. Open an issue in the project repository with details about your problem

## Benefits of Migration

- **Cleaner code**: Removes technical debt and improves code quality
- **Better maintainability**: Simpler code structure with fewer aliases
- **Future-proof**: Aligns with modern naming conventions
- **Performance**: Slight improvement from reduced alias overhead

## Backward Compatibility

The old class names will continue to work with deprecation warnings until v2.0, giving you ample time to migrate your code.