import sys
import polars as pl
import hashlib


def read_eager(path: str) -> pl.DataFrame:
    return pl.read_parquet(path)


def read_lazy(path: str) -> pl.DataFrame:
    return pl.scan_parquet(path).collect()


def get_hash(df: pl.DataFrame) -> str:
    m = hashlib.sha256()
    for col in df.columns:
        m.update(col.encode())
        # Instead of hash_rows which is expr only, use df.hash_rows()
        # To avoid memory blow up, hash rows by small chunk if possible, or just hash column representation
        # It's a DataFrame, let's just hash the whole dataframe hash_rows result directly
    m.update(df.hash_rows().to_numpy().tobytes())
    return m.hexdigest()


path = sys.argv[1]
eager_hash = get_hash(read_eager(path))
lazy_hash = get_hash(read_lazy(path))
print(f"EAGER_HASH: {eager_hash}")
print(f"LAZY_HASH: {lazy_hash}")
if eager_hash == lazy_hash:
    print("HASHES_MATCH")
else:
    print("HASH_MISMATCH")
