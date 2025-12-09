# Refactoring Plan: Object Groups & Interfaces Unification

Based on the detailed analysis and requirements, here is the plan to unify interfaces and refactor object groups.

## 1. RecordSource Unification
**Goal**: Standardize `RecordSource` as an ABC and unify implementations.
*   **Action**: Convert `RecordSource` (currently a `Protocol` in `src/bioetl/domain/record_source.py`) to an abstract base class (`ABC`).
*   **Action**: Update `InMemoryRecordSource`, `ApiRecordSource`, `CsvRecordSourceImpl`, and `IdListRecordSourceImpl` to inherit from `RecordSourceABC`.
*   **Action**: Unify `iter_records` signature (already largely consistent).
*   **Strategy**: Keep specific `__init__` parameters for now but ensure factories in `PipelineContainer` handle the construction logic, hiding differences from the application layer.

## 2. Loader & OutputWriter Unification
**Goal**: Consolidate `LoaderABC` and `OutputWriterABC` to reduce redundancy.
*   **Action**: Update `UnifiedOutputWriterImpl` (Infrastructure) to implement `LoaderABC` directly.
    *   Implement `load(self, df, output_path, context, ...)` in `UnifiedOutputWriterImpl` by aliasing/wrapping `write_result`.
*   **Action**: Update `PipelineContainerABC` to expose `get_loader()` returning `LoaderABC` (or update `get_output_writer` to return a type that satisfies `LoaderABC`).
*   **Outcome**: Allows removing `OutputWriterLoaderAdapter` in the future and using `UnifiedOutputWriterImpl` directly in pipelines.

## 3. Normalization Interface Cleanup
**Goal**: Remove redundant method aliases.
*   **Action**: In `NormalizationServiceABC` and `ChemblNormalizationServiceImpl`, mark `apply_normalize_fields` as deprecated or remove it, standardizing on `apply_normalize_dataframe` (or vice versa, ensuring one clear method name).

## 4. Verification
*   **Action**: Run existing tests to ensure no regressions.
*   **Action**: Verify that `ChemblPipelineBase` and other consumers work correctly with the updated interfaces.

## Migration Strategy
1.  **Non-breaking Changes**: Add `LoaderABC` support to `UnifiedOutputWriterImpl` without removing `write_result` immediately.
2.  **Code Updates**: Refactor `RecordSource` inheritance.
3.  **Cleanup**: Remove unused adapters if possible.
