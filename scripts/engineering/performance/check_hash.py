"""Compare eager and lazy parquet reads by a stable row-hash digest."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import polars as pl


def read_eager(path: Path) -> pl.DataFrame:
    return pl.read_parquet(path)


def read_lazy(path: Path) -> pl.DataFrame:
    return pl.scan_parquet(path).collect()


def dataframe_sha256(frame: pl.DataFrame) -> str:
    """Hash column names and ``hash_rows`` bytes without building a CSV."""
    digest = hashlib.sha256()
    for column in frame.columns:
        digest.update(column.encode("utf-8"))
    digest.update(frame.hash_rows().to_numpy().tobytes())
    return digest.hexdigest()


def format_hash_report(eager_hash: str, lazy_hash: str) -> tuple[str, int]:
    """Return the hash log text and a non-zero code when the digests differ."""
    matched = eager_hash == lazy_hash
    status = "HASHES_MATCH" if matched else "HASH_MISMATCH"
    report = f"EAGER_HASH: {eager_hash}\nLAZY_HASH: {lazy_hash}\n{status}\n"
    return report, 0 if matched else 1


def compare_reads(path: Path) -> tuple[str, int]:
    return format_hash_report(
        dataframe_sha256(read_eager(path)),
        dataframe_sha256(read_lazy(path)),
    )


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("usage: check_hash.py <parquet>", file=sys.stderr)
        return 1
    report, code = compare_reads(Path(args[0]))
    sys.stdout.write(report)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
