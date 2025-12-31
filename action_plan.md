# Action Plan

## Priority P1 (High)
1. **Fix Code Coverage**
   - **Target**: Increase from 77% to >85%.
   - **Scope**: `src/bioetl/interfaces/cli` and `src/bioetl/infrastructure/storage`.
   - **Action**: Write unit tests for CLI commands and Writers.

## Priority P2 (Medium)
2. **Standardize Logging Schema**
   - **Target**: Add `dataset` field to `UnifiedLogger`.
   - **Scope**: `src/bioetl/infrastructure/observability`.
   - **Action**: Update `UnifiedLogger` methods to accept and log `dataset`.

## Priority P3 (Low)
3. **Remove Dead Code**
   - **Target**: `src/bioetl/infrastructure/storage/base_delta_writer.py`.
   - **Action**: Delete the file.
