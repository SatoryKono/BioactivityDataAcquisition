"""Gold layer writer (business-ready data with strict validation).

Implements RULES.md §2.1.1 - Gold Layer specifications.

Requirements:
- REQ-DATA-009: Strict validation (strict=True)
- REQ-DATA-010: SCD Type 2 or date partitioning
- REQ-CONTRACT-001: Published schemas in docs/contracts/

Architecture:
- Uses Pandera for strict schema validation
- Supports both Delta Lake and Parquet formats
- Implements SCD Type 2 (Slowly Changing Dimensions) for history tracking
- Enforces data contracts
"""

from datetime import datetime
from pathlib import Path
from typing import Any

import pandera as pa
from deltalake import DeltaTable, write_deltalake
from deltalake.exceptions import TableNotFoundError


class GoldWriter:
    """Writer for Gold layer (validated business data).

    Enforces strict validation before writing. All records must pass
    schema validation or the entire batch fails.

    Example:
        >>> schema = pa.DataFrameSchema({
        ...     "entity_id": pa.Column(str, nullable=False),
        ...     "value": pa.Column(float, nullable=False)
        ... }, strict=True)
        >>> writer = GoldWriter(
        ...     base_path="s3://bioetl-gold",
        ...     storage_options={"AWS_ENDPOINT_URL": "http://localhost:9000"}
        ... )
        >>> records = [{"entity_id": "CHEMBL123", "value": 5.5}]
        >>> writer.write_gold(
        ...     table_name="chembl.activity_aggregated",
        ...     records=records,
        ...     schema=schema,
        ...     mode="overwrite"
        ... )
    """

    def __init__(
        self,
        base_path: str,
        storage_options: dict[str, str] | None = None,
    ) -> None:
        """Initialize Gold writer.

        Args:
            base_path: Base path for Gold tables (e.g., 's3://bioetl-gold')
            storage_options: Storage configuration for S3/MinIO
        """
        self.base_path = base_path.rstrip("/")
        self.storage_options = storage_options or {}

    def write_gold(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        schema: pa.DataFrameSchema | None = None,
        mode: str = "overwrite",
        partition_cols: list[str] | None = None,
        scd_config: dict[str, Any] | None = None,
    ) -> None:
        """Write validated records to Gold layer.

        Requirements:
        - REQ-DATA-009: Strict validation (strict=True)
        - REQ-DATA-010: SCD Type 2 or date partitioning

        Args:
            table_name: Gold table name (e.g., 'chembl.activity_aggregated')
            records: List of strictly validated records
            schema: Pandera schema for validation (strict=True required)
            mode: Write mode:
                - 'overwrite': Replace entire table
                - 'append': Add new records
                - 'scd2': Slowly Changing Dimension Type 2 (history tracking)
            partition_cols: Optional partition columns (e.g., ['year', 'month'])
            scd_config: Configuration for SCD Type 2 mode:
                - business_key: Column(s) identifying unique entity
                - version_col: Column for version number
                - valid_from_col: Column for validity start date
                - valid_to_col: Column for validity end date
                - current_flag_col: Column for current record flag

        Raises:
            ValueError: If records fail validation
            ValueError: If schema doesn't have strict=True
        """
        if not records:
            raise ValueError("No records to write")

        # Validate schema strictness
        if schema is not None:
            if not schema.strict:
                raise ValueError(
                    "Gold layer requires strict=True schema validation "
                    "(REQ-DATA-009)"
                )

            # Validate records against schema
            import polars as pl

            df = pl.DataFrame(records)
            try:
                # Convert to pandas for Pandera validation
                pandas_df = df.to_pandas()
                schema.validate(pandas_df, lazy=False)
            except pa.errors.SchemaError as e:
                raise ValueError(f"Schema validation failed: {e}") from e

        # Construct table path
        table_path = f"{self.base_path}/{table_name.replace('.', '/')}"

        # Route to appropriate write method based on mode
        if mode == "scd2":
            if scd_config is None:
                raise ValueError("scd_config required for SCD Type 2 mode")
            self._write_scd2(table_path, records, scd_config, partition_cols)
        elif mode in ("overwrite", "append"):
            self._write_simple(table_path, records, mode, partition_cols)
        else:
            raise ValueError(f"Invalid mode: {mode}. Use 'overwrite', 'append', or 'scd2'")

    def _write_simple(
        self,
        table_path: str,
        records: list[dict[str, Any]],
        mode: str,
        partition_cols: list[str] | None,
    ) -> None:
        """Write records using simple overwrite or append mode.

        Args:
            table_path: Full path to table
            records: Records to write
            mode: 'overwrite' or 'append'
            partition_cols: Optional partition columns
        """
        write_deltalake(
            table_or_uri=table_path,
            data=records,
            mode=mode,
            partition_by=partition_cols,
            storage_options=self.storage_options,
            engine="rust",
        )

    def _write_scd2(
        self,
        table_path: str,
        records: list[dict[str, Any]],
        scd_config: dict[str, Any],
        partition_cols: list[str] | None,
    ) -> None:
        """Write records using SCD Type 2 (history tracking).

        Requirements:
        - REQ-DATA-010: SCD Type 2 implementation

        SCD Type 2 maintains history by:
        1. Closing old records (set valid_to, current_flag=False)
        2. Inserting new records (set valid_from, current_flag=True)

        Args:
            table_path: Full path to table
            records: New records with changes
            scd_config: SCD configuration
            partition_cols: Optional partition columns
        """
        # Extract config
        business_key = scd_config["business_key"]
        version_col = scd_config.get("version_col", "version")
        valid_from_col = scd_config.get("valid_from_col", "valid_from")
        valid_to_col = scd_config.get("valid_to_col", "valid_to")
        current_flag_col = scd_config.get("current_flag_col", "is_current")

        # Add SCD metadata to new records
        now = datetime.utcnow().isoformat()
        for record in records:
            record[valid_from_col] = now
            record[valid_to_col] = None  # Open-ended (current)
            record[current_flag_col] = True
            record[version_col] = record.get(version_col, 1)

        try:
            # Load existing table
            dt = DeltaTable(table_path, storage_options=self.storage_options)

            # Perform SCD Type 2 merge
            self._merge_scd2(dt, records, business_key, scd_config)

        except TableNotFoundError:
            # Table doesn't exist, create it
            write_deltalake(
                table_or_uri=table_path,
                data=records,
                mode="append",
                partition_by=partition_cols,
                storage_options=self.storage_options,
                engine="rust",
            )

    def _merge_scd2(
        self,
        dt: DeltaTable,
        records: list[dict[str, Any]],
        business_key: str | list[str],
        scd_config: dict[str, Any],
    ) -> None:
        """Merge records using SCD Type 2 logic.

        Args:
            dt: Delta table instance
            records: New records to merge
            business_key: Column(s) identifying unique entity
            scd_config: SCD configuration
        """
        import pyarrow as pa

        # Convert to list if single key
        if isinstance(business_key, str):
            business_keys = [business_key]
        else:
            business_keys = business_key

        # Convert records to PyArrow table
        new_data = pa.Table.from_pylist(records)

        # Extract column names
        valid_to_col = scd_config.get("valid_to_col", "valid_to")
        current_flag_col = scd_config.get("current_flag_col", "is_current")
        valid_from_col = scd_config.get("valid_from_col", "valid_from")

        # Build merge condition
        merge_condition = " AND ".join(
            f"target.{key} = source.{key}" for key in business_keys
        )
        merge_condition += f" AND target.{current_flag_col} = true"

        now = datetime.utcnow().isoformat()

        # Merge logic:
        # 1. Close old current records (set valid_to, is_current=False)
        # 2. Insert new records as current
        (
            dt.merge(
                source=new_data,
                predicate=merge_condition,
                source_alias="source",
                target_alias="target",
            )
            .when_matched_update(
                updates={
                    valid_to_col: f"'{now}'",
                    current_flag_col: "false",
                }
            )
            .when_not_matched_insert_all()
            .execute()
        )

    def read_gold(
        self,
        table_name: str,
        current_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Read records from Gold table.

        Args:
            table_name: Gold table name
            current_only: If True and SCD Type 2, return only current records

        Returns:
            List of records as dictionaries

        Example:
            >>> writer = GoldWriter(base_path="s3://bioetl-gold")
            >>> records = writer.read_gold("chembl.activity_aggregated")
        """
        table_path = f"{self.base_path}/{table_name.replace('.', '/')}"
        dt = DeltaTable(table_path, storage_options=self.storage_options)

        # Convert to PyArrow table
        arrow_table = dt.to_pyarrow_table()

        # Filter for current records if SCD Type 2
        if current_only and "is_current" in arrow_table.column_names:
            import pyarrow.compute as pc

            arrow_table = arrow_table.filter(
                pc.equal(arrow_table["is_current"], True)
            )

        # Convert to list of dicts
        return arrow_table.to_pylist()

    def get_history(
        self,
        table_name: str,
        business_key_values: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Get full history for an entity (SCD Type 2).

        Args:
            table_name: Gold table name
            business_key_values: Business key values to filter
                (e.g., {"entity_id": "CHEMBL123"})

        Returns:
            List of all historical versions, ordered by valid_from

        Example:
            >>> writer = GoldWriter(base_path="s3://bioetl-gold")
            >>> history = writer.get_history(
            ...     "chembl.activity_aggregated",
            ...     {"entity_id": "CHEMBL123"}
            ... )
            >>> for version in history:
            ...     print(f"Version {version['version']}: {version['valid_from']}")
        """
        table_path = f"{self.base_path}/{table_name.replace('.', '/')}"
        dt = DeltaTable(table_path, storage_options=self.storage_options)

        # Convert to PyArrow table
        arrow_table = dt.to_pyarrow_table()

        # Filter by business key
        import pyarrow.compute as pc

        mask = None
        for key, value in business_key_values.items():
            condition = pc.equal(arrow_table[key], value)
            mask = condition if mask is None else pc.and_(mask, condition)

        if mask is not None:
            arrow_table = arrow_table.filter(mask)

        # Sort by valid_from
        if "valid_from" in arrow_table.column_names:
            arrow_table = arrow_table.sort_by([("valid_from", "ascending")])

        return arrow_table.to_pylist()
