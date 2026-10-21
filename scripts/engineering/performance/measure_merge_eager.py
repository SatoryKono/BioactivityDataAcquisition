from __future__ import annotations

import os
import sys
import time

import polars as pl


def create_dataset(path: str, rows: int):
    # Using more columns based roughly on chembl activity schema to match production volume
    df = pl.DataFrame(
        {
            "source_batch_id": pl.Series(
                [f"batch_{i % 10}" for i in range(rows)], dtype=pl.Utf8
            ),
            "state": pl.Series(["active"] * rows, dtype=pl.Utf8),
            "activity_id": pl.Series([f"ACT_{i}" for i in range(rows)], dtype=pl.Utf8),
            "assay_id": pl.Series(
                [f"ASSAY_{i % 1000}" for i in range(rows)], dtype=pl.Utf8
            ),
            "molecule_id": pl.Series(
                [f"CHEMBL_{i % 10000}" for i in range(rows)], dtype=pl.Utf8
            ),
            "target_id": pl.Series(
                [f"TGT_{i % 500}" for i in range(rows)], dtype=pl.Utf8
            ),
            "publication_id": pl.Series(
                [f"PUB_{i % 2000}" for i in range(rows)], dtype=pl.Utf8
            ),
            "standard_relation": pl.Series(["="] * rows, dtype=pl.Utf8),
            "standard_value": pl.Series(
                [float(i) / 2.0 for i in range(rows)], dtype=pl.Float64
            ),
            "standard_units": pl.Series(["nM"] * rows, dtype=pl.Utf8),
            "standard_type": pl.Series(["IC50"] * rows, dtype=pl.Utf8),
            "standard_flag": pl.Series([1] * rows, dtype=pl.Int64),
            "pchembl_value": pl.Series(
                [5.0 + (i % 5) for i in range(rows)], dtype=pl.Float64
            ),
            "data_validity_comment": pl.Series([None] * rows, dtype=pl.Utf8),
            "potential_duplicate": pl.Series([0] * rows, dtype=pl.Int64),
            "bao_endpoint": pl.Series(["BAO_0000190"] * rows, dtype=pl.Utf8),
            "uo_units": pl.Series(["UO_0000065"] * rows, dtype=pl.Utf8),
            "src_id": pl.Series([1] * rows, dtype=pl.Int64),
            "record_id": pl.Series(range(rows), dtype=pl.Int64),
            "activity_relation": pl.Series(["="] * rows, dtype=pl.Utf8),
            "activity_value": pl.Series(
                [float(i) / 2.0 for i in range(rows)], dtype=pl.Float64
            ),
            "units": pl.Series(["nM"] * rows, dtype=pl.Utf8),
            "canonical_smiles": pl.Series(
                ["C" * (10 + i % 20) for i in range(rows)], dtype=pl.Utf8
            ),
            "target_organism": pl.Series(["Homo sapiens"] * rows, dtype=pl.Utf8),
            "target_taxonomy_id": pl.Series([9606] * rows, dtype=pl.Int64),
            "assay_type": pl.Series(["B"] * rows, dtype=pl.Utf8),
            "assay_description": pl.Series(
                [f"Assay desc {i % 1000}" for i in range(rows)], dtype=pl.Utf8
            ),
            "bao_format": pl.Series(["BAO_0000357"] * rows, dtype=pl.Utf8),
            "bao_label": pl.Series(["single protein format"] * rows, dtype=pl.Utf8),
            "journal": pl.Series(
                [f"Journal of {i % 100}" for i in range(rows)], dtype=pl.Utf8
            ),
            "publication_year": pl.Series(
                [2000 + i % 25 for i in range(rows)], dtype=pl.Int64
            ),
        }
    )

    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.write_parquet(path)


def read_eager(path: str) -> pl.DataFrame:
    # Mimic eager reading logic from MergeService
    return pl.read_parquet(path)


def read_lazy(path: str) -> pl.DataFrame:
    # Lazy API equivalent
    return pl.scan_parquet(path).collect()


def main():
    if len(sys.argv) < 3:
        sys.exit(1)

    mode = sys.argv[1]
    rows = int(sys.argv[2])
    path = f"reports/performance/raw_logs/measure_merge_silver_{rows}.parquet"

    if mode == "prepare":
        create_dataset(path, rows)
    elif mode == "eager":
        start_time = time.time()
        df = read_eager(path)
        wall_time = time.time() - start_time
        print(f"EAGER_WALL_TIME: {wall_time:.4f}")
        print(f"EAGER_ROWS: {len(df)}")
    elif mode == "lazy":
        start_time = time.time()
        df = read_lazy(path)
        wall_time = time.time() - start_time
        print(f"LAZY_WALL_TIME: {wall_time:.4f}")
        print(f"LAZY_ROWS: {len(df)}")


if __name__ == "__main__":
    main()
