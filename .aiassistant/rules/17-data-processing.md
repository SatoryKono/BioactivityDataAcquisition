# 17. Data Processing Standards (Skills: Polars, Delta Lake, Pandera)

## Overview
This document outlines the standard practices for data acquisition, transformation, and loading (ETL) using Polars, Delta Lake, and Pandera.

## 1. Polars: High-Performance Transformation (Skill: Polars Lazy API)

### 1.1 Lazy Evaluation (Required)
Always prefer the Lazy API (`pl.scan_parquet`, `pl.lazy`) for ETL tasks.
-   **Why**: Optimizes query plan and minimizes memory usage (critical for millions of rows).
-   **Pattern**:
    ```python
    import polars as pl
    
    def transform_pipeline(input_path: str) -> pl.DataFrame:
        query = (
            pl.scan_parquet(input_path)
            .filter(pl.col("value") > 0)
            .with_columns(
                (pl.col("value") * 1000).alias("value_nm")
            )
        )
        # Collect only at the end
        return query.collect()
    ```

### 1.2 Type Safety & Expressions
-   **Expressions**: Use `pl.col("name")` instead of string literals.
-   **Casting**: Explicitly cast types (`pl.cast(pl.Float64)`).
-   **Aggregation**: Use `.group_by()` with `.agg()` for summary statistics.

## 2. Delta Lake: Reliable Storage (Skill: Delta Lake Management)

### 2.1 Write Operations
-   **Mode**: `append` for Bronze (raw logs), `merge` (upsert) for Silver (cleaned entities).
-   **Merge Logic**: Always merge on unique business keys (e.g., `content_hash`, `mol_reg_no`).
-   **Partitioning**: Partition by `ingestion_date` (YYYY-MM-DD) or high-cardinality columns (e.g., `source_db`) if > 1GB data.

### 2.2 Maintenance (Vacuum & Optimize)
-   **Vacuum**: Run periodically (e.g., weekly) to remove old files based on retention policy (default 7 days).
    ```python
    delta_table.vacuum(retention_hours=168)
    ```
-   **Optimize**: Run after significant writes to compact small files (Z-Ordering optional for read-heavy tables).
    ```python
    delta_table.optimize().execute_compaction()
    ```

## 3. Pandera: Schema Validation (Skill: Pandera Validation)

### 3.1 Schema Definition
Define schemas as `pa.DataFrameModel` classes.
-   **Strictness**: Use `strict=True` to reject unknown columns.
-   **Coercion**: Use `coerce=True` to automatically convert compatible types.

### 3.2 Runtime Validation
Apply validation decorators or explicit checks before saving to Silver/Gold layers.
-   **Example**:
    ```python
    import pandera as pa
    from pandera.typing import DataFrame, Series

    class BioactivitySchema(pa.DataFrameModel):
        compound_id: Series[str] = pa.Field(check_name=True)
        value_nm: Series[float] = pa.Field(ge=0.0) # Greater or equal to 0

        class Config:
            strict = True
            coerce = True

    @pa.check_types
    def save_silver(df: DataFrame[BioactivitySchema]) -> None:
        ...
    ```

## 4. Medallion Architecture Flow (Skill: Medallion Data Flow)

1.  **Bronze (Raw)**:
    -   Format: JSONL (compressed zstd) or Parquet.
    -   Schema: Flexible (allow extra columns).
    -   Action: Append-only. No updates.
2.  **Silver (Refined)**:
    -   Format: Delta Lake.
    -   Schema: Enforced (Pandera). Cleaned types, standardized units (nM), normalized text.
    -   Action: Merge (Upsert). Deduplicated.
3.  **Gold (Aggregated)**:
    -   Format: Delta Lake / Parquet.
    -   Schema: Business-ready (Star Schema). Aggregated metrics (avg_pchembl, count_targets).
    -   Action: Overwrite (Full refresh) or Incremental.
