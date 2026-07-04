import os

import polars as pl
from deltalake import DeltaTable

table_path = "data/output/silver/chembl/molecule"

try:
    print(f"Loading table: {table_path}")
    dt = DeltaTable(table_path)
    print(f"Table version: {dt.version()}")
    print(f"Table files: {len(dt.files())}")

    # Try reading it with polars
    df = pl.read_delta(table_path)
    print(f"Polars read successful: {df.shape}")
except Exception as e:
    print(f"ERROR: {e}")
