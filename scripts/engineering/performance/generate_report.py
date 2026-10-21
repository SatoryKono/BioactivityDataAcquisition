"""Build the eager-vs-lazy measurement report from committed raw logs."""

from __future__ import annotations

import os
from pathlib import Path
from typing import NamedTuple

LOG_DIR = Path("reports/performance/raw_logs")
REPORT_PATH = Path("reports/performance/merge_service_eager_vs_lazy_measurements.md")
DATASET_SIZES = (1_000_000, 2_000_000, 5_000_000)
WALL_BOTTLENECK_SECONDS = 0.5
WALL_BOTTLENECK_PERCENT = 10.0
RSS_BOTTLENECK_PERCENT = 10.0
PEAK_RSS_MARKER = "Maximum resident set size"


class _Side(NamedTuple):
    rss: str
    wall: str
    rows: str
    digest: str


def _marked_value(path: Path, marker: str) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if marker not in line:
            continue
        _, separator, value = line.partition(":")
        if separator:
            return value.strip()
        return line.strip()
    return "N/A"


def _require(path: Path, marker: str) -> str:
    value = _marked_value(path, marker)
    if value == "N/A" or not value:
        raise ValueError(f"Missing {marker!r} in {path}")
    return value


def _require_row_count(path: Path, marker: str, *, expected: int) -> str:
    raw = _require(path, marker)
    if int(raw) != expected:
        raise ValueError(f"{path} {marker} is {raw}, expected {expected}")
    return f"{int(raw):,}"


def _hash_status(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped in {"HASHES_MATCH", "HASH_MISMATCH"}:
            return stripped
    return "N/A"


def _require_matching_hashes(path: Path) -> tuple[str, str]:
    eager = _require(path, "EAGER_HASH:")
    lazy = _require(path, "LAZY_HASH:")
    if eager != lazy or _hash_status(path) != "HASHES_MATCH":
        raise ValueError(f"Eager and lazy hashes differ in {path}")
    return eager, lazy


def _table_row(
    *,
    size: int,
    file_size: int,
    strategy: str,
    rss: str,
    wall: str,
    rows_read: str,
    digest: str,
) -> str:
    return (
        f"| {size:,} | {file_size:,} bytes | {strategy} | {rss} | {wall} | "
        f"{rows_read} | `{digest}` |"
    )


def _side(
    path: Path,
    *,
    wall_marker: str,
    rows_marker: str,
    expected_rows: int,
    digest: str,
) -> _Side:
    return _Side(
        rss=_require(path, PEAK_RSS_MARKER),
        wall=_require(path, wall_marker),
        rows=_require_row_count(path, rows_marker, expected=expected_rows),
        digest=digest,
    )


def _load_size(size: int, log_dir: Path) -> tuple[int, _Side, _Side]:
    file_size = (log_dir / f"measure_merge_silver_{size}.parquet").stat().st_size
    eager_digest, lazy_digest = _require_matching_hashes(log_dir / f"hash_{size}.txt")
    eager = _side(
        log_dir / f"eager_{size}.txt",
        wall_marker="EAGER_WALL_TIME:",
        rows_marker="EAGER_ROWS:",
        expected_rows=size,
        digest=eager_digest,
    )
    lazy = _side(
        log_dir / f"lazy_{size}.txt",
        wall_marker="LAZY_WALL_TIME:",
        rows_marker="LAZY_ROWS:",
        expected_rows=size,
        digest=lazy_digest,
    )
    return file_size, eager, lazy


def _rows_for(size: int, file_size: int, eager: _Side, lazy: _Side) -> list[str]:
    return [
        _table_row(
            size=size,
            file_size=file_size,
            strategy="Eager",
            rss=eager.rss,
            wall=eager.wall,
            rows_read=eager.rows,
            digest=eager.digest,
        ),
        _table_row(
            size=size,
            file_size=file_size,
            strategy="Lazy",
            rss=lazy.rss,
            wall=lazy.wall,
            rows_read=lazy.rows,
            digest=lazy.digest,
        ),
    ]


def measurement_rows(size: int, *, log_dir: Path = LOG_DIR) -> list[str]:
    """Return the eager and lazy table rows for one dataset size."""
    file_size, eager, lazy = _load_size(size, log_dir)
    return _rows_for(size, file_size, eager, lazy)


def _wall_gain(eager_wall: str, lazy_wall: str) -> tuple[float, float]:
    eager = float(eager_wall)
    lazy = float(lazy_wall)
    if eager <= 0 or lazy >= eager:
        return 0.0, 0.0
    gain = eager - lazy
    return gain, 100.0 * gain / eager


def _rss_drop_percent(eager_rss: str, lazy_rss: str) -> float:
    eager = int(eager_rss)
    lazy = int(lazy_rss)
    if eager <= 0 or lazy >= eager:
        return 0.0
    return 100.0 * (eager - lazy) / eager


class _Peaks(NamedTuple):
    wall_gain: float
    wall_percent: float
    rss_drop: float
    wall_proven: bool


def _prefer_wall(
    gain: float, percent: float, best_gain: float, best_percent: float
) -> bool:
    if gain > best_gain:
        return True
    return gain == best_gain and percent > best_percent


def _wall_clears(gain: float, percent: float) -> bool:
    return gain >= WALL_BOTTLENECK_SECONDS and percent >= WALL_BOTTLENECK_PERCENT


def _metric_peaks(sides: list[tuple[_Side, _Side]]) -> _Peaks:
    best_gain = 0.0
    best_percent = 0.0
    max_rss_drop = 0.0
    wall_proven = False
    for eager, lazy in sides:
        gain, percent = _wall_gain(eager.wall, lazy.wall)
        if _prefer_wall(gain, percent, best_gain, best_percent):
            best_gain = gain
            best_percent = percent
        wall_proven = wall_proven or _wall_clears(gain, percent)
        drop = _rss_drop_percent(eager.rss, lazy.rss)
        if drop > max_rss_drop:
            max_rss_drop = drop
    return _Peaks(best_gain, best_percent, max_rss_drop, wall_proven)


def _conclusion(proven: bool) -> str:
    if proven:
        return (
            "A bottleneck has been proven. "
            "Eager mode is no longer required by DOMAIN_STOP."
        )
    return (
        "A bottleneck has **not been proven**. "
        "The eager execution mode remains the default until a reduction "
        "clears those thresholds."
    )


def _verdict(sides: list[tuple[_Side, _Side]]) -> str:
    peaks = _metric_peaks(sides)
    proven = peaks.wall_proven or peaks.rss_drop >= RSS_BOTTLENECK_PERCENT
    conclusion = _conclusion(proven)
    return f"""## Verdict on DOMAIN_STOP
The `DOMAIN_STOP` rule forbids lazy-refactoring without a measured bottleneck.

Thresholds for a proven bottleneck: lazy wall time lower by at least {WALL_BOTTLENECK_SECONDS:.1f} s and {WALL_BOTTLENECK_PERCENT:.0f}%, or lazy peak RSS lower by at least {RSS_BOTTLENECK_PERCENT:.0f}%.

Based on the measurements:
- Maximum lazy wall-time reduction: {peaks.wall_gain:.4f} s ({peaks.wall_percent:.1f}%).
- Maximum lazy peak-RSS reduction: {peaks.rss_drop:.1f}%.
- **Conclusion:** {conclusion}
"""


def _expected_logs(log_dir: Path) -> list[Path]:
    return sorted(
        log_dir / f"{kind}_{size}.txt"
        for size in DATASET_SIZES
        for kind in ("eager", "lazy")
    )


def _timed_lines(path: Path) -> list[str]:
    if not path.is_file():
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if "Command being timed:" in line
    ]


def _timed_commands(log_dir: Path) -> str:
    commands: list[str] = []
    for path in _expected_logs(log_dir):
        matches = _timed_lines(path)
        if not matches:
            raise ValueError(f"Missing timed command in {path}")
        commands.extend(f"- `{path.name}`: {line}" for line in matches)
    return "\n".join(commands)


def render_report(*, log_dir: Path = LOG_DIR) -> str:
    """Render the measurement report from raw logs and parquet sizes."""
    loaded = [_load_size(size, log_dir) for size in DATASET_SIZES]
    rows: list[str] = []
    sides: list[tuple[_Side, _Side]] = []
    for size, (file_size, eager, lazy) in zip(DATASET_SIZES, loaded, strict=True):
        sides.append((eager, lazy))
        rows.extend(_rows_for(size, file_size, eager, lazy))
    environment = (log_dir / "env.txt").read_text(encoding="utf-8").strip()
    table = "\n".join(rows)
    verdict = _verdict(sides).rstrip()
    timed = _timed_commands(log_dir)
    return f"""# MergeService Eager vs Lazy Reading Measurements

## Objective
Measure the resource consumption (Peak RSS and Wall Time) and ensure semantic equivalence when reading Silver tables using eager reading (`pl.read_parquet`) vs lazy plan collection (`pl.scan_parquet().collect()`) to address the DOMAIN_STOP constraint.

## Methodology
- **Data Generation:** Simulated production-like ChEMBL Activity table data with corresponding columns, types, and sizes.
- **Sizes:** 1,000,000 rows (approx 3.9 MB disk space for parquet), 2,000,000 rows (approx 7.9 MB), and 5,000,000 rows (approx 20.1 MB).
- **Measurement Tooling:** `scripts/engineering/performance/measure_merge_eager.py` and `scripts/engineering/performance/run_measurements.sh`.
- Peak RSS was measured in an isolated run (without creating in-memory CSVs which polluted previous results). Hash checking was performed externally using `scripts/engineering/performance/check_hash.py`.
- Each size was measured once, eager then lazy. That order does not separate file-cache effects from the read API.

## Environment
```
{environment}
```

## Provenance
The raw logs are the immutable snapshot of that run. `/usr/bin/time` recorded the command that actually executed. Later hardening of `run_measurements.sh` to `uv run --frozen --no-build` does not rewrite those lines.

{timed}

## Measurements Table

| Dataset Size | File Size on Disk | Strategy | Peak RSS (KB) | Wall Time (s) | Rows Read | SHA-256 Hash of Output (df.hash_rows()) |
| --- | --- | --- | --- | --- | --- | --- |
{table}

## Semantic Equivalence
For all sizes (1M, 2M, 5M rows), the eager and lazy execution methods produced identical outputs:
- **Number of rows:** Matched the requested size in both `EAGER_ROWS` and `LAZY_ROWS`.
- **Data Content / Hashes:** `EAGER_HASH` and `LAZY_HASH` matched, and the hash log contains `HASHES_MATCH`.
- **Discrepancies:** None. Generation raises if a marker, row count, or hash check is missing or inconsistent.

{verdict}
"""


def write_report(path: Path = REPORT_PATH, *, log_dir: Path = LOG_DIR) -> None:
    """Atomically replace the measurement report."""
    payload = render_report(log_dir=log_dir)
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(payload, encoding="utf-8")
    os.replace(temporary, path)


def main() -> None:
    write_report()


if __name__ == "__main__":
    main()
