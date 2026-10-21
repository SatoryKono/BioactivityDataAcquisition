"""Guards for the eager-versus-lazy measurement report."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from scripts.engineering.performance import check_hash, generate_report

pytestmark = pytest.mark.unit

_TIMED = '\tCommand being timed: "uv run python measure.py eager 1"\n'


def _write_side(
    path: Path,
    *,
    wall_marker: str,
    wall: str,
    rows_marker: str,
    rows: int,
    rss: str = "1000",
) -> None:
    path.write_text(
        f"{wall_marker} {wall}\n"
        f"{rows_marker} {rows}\n"
        f"\tMaximum resident set size (kbytes): {rss}\n"
        f"{_TIMED}",
        encoding="utf-8",
    )


def _seed(
    log_dir: Path,
    *,
    row_count: int | None = None,
    eager_wall: str = "2.0000",
    lazy_wall: str = "1.0000",
    eager_rss: str = "1000",
    lazy_rss: str = "1000",
    eager_hash: str = "a" * 64,
) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "env.txt").write_text(
        "=== ENVIRONMENT ===\nPython: test\n",
        encoding="utf-8",
    )
    for size in generate_report.DATASET_SIZES:
        actual_rows = size if row_count is None else row_count
        (log_dir / f"measure_merge_silver_{size}.parquet").write_bytes(b"pq")
        (log_dir / f"hash_{size}.txt").write_text(
            f"EAGER_HASH: {eager_hash}\nLAZY_HASH: {eager_hash}\nHASHES_MATCH\n",
            encoding="utf-8",
        )
        _write_side(
            log_dir / f"eager_{size}.txt",
            wall_marker="EAGER_WALL_TIME:",
            wall=eager_wall,
            rows_marker="EAGER_ROWS:",
            rows=actual_rows,
            rss=eager_rss,
        )
        _write_side(
            log_dir / f"lazy_{size}.txt",
            wall_marker="LAZY_WALL_TIME:",
            wall=lazy_wall,
            rows_marker="LAZY_ROWS:",
            rows=actual_rows,
            rss=lazy_rss,
        )


def test_format_hash_report_fails_closed_on_mismatch() -> None:
    matched, code = check_hash.format_hash_report("abc", "abc")
    assert code == 0
    assert "HASHES_MATCH" in matched
    mismatched, failed = check_hash.format_hash_report("abc", "def")
    assert failed == 1
    assert "HASH_MISMATCH" in mismatched


def test_check_hash_usage_error_returns_one() -> None:
    assert check_hash.main([]) == 1


def test_committed_report_matches_raw_logs(tmp_path: Path) -> None:
    recorded_sizes = {
        1_000_000: 3_928_205,
        2_000_000: 7_978_772,
        5_000_000: 20_157_108,
    }
    for source in generate_report.LOG_DIR.iterdir():
        if source.is_file():
            shutil.copy(source, tmp_path / source.name)
    for size, nbytes in recorded_sizes.items():
        parquet = tmp_path / f"measure_merge_silver_{size}.parquet"
        parquet.write_bytes(b"")
        os.truncate(parquet, nbytes)
    rendered = generate_report.render_report(log_dir=tmp_path)
    committed = generate_report.REPORT_PATH.read_text(encoding="utf-8")
    assert rendered == committed


def test_hash_mismatch_blocks_the_report(tmp_path: Path) -> None:
    _seed(tmp_path)
    hash_path = tmp_path / "hash_1000000.txt"
    hash_path.write_text(
        "EAGER_HASH: a\nLAZY_HASH: b\nHASH_MISMATCH\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="hashes differ"):
        generate_report.measurement_rows(1_000_000, log_dir=tmp_path)


def test_wrong_row_count_blocks_the_report(tmp_path: Path) -> None:
    _seed(tmp_path, row_count=1)
    with pytest.raises(ValueError, match="EAGER_ROWS"):
        generate_report.measurement_rows(1_000_000, log_dir=tmp_path)


def test_missing_peak_rss_blocks_the_report(tmp_path: Path) -> None:
    _seed(tmp_path)
    path = tmp_path / "eager_1000000.txt"
    path.write_text(
        "EAGER_WALL_TIME: 1.0000\nEAGER_ROWS: 1000000\n" + _TIMED,
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Maximum resident set size"):
        generate_report.measurement_rows(1_000_000, log_dir=tmp_path)


def test_verdict_follows_wall_and_rss_thresholds(tmp_path: Path) -> None:
    _seed(tmp_path, eager_wall="2.0000", lazy_wall="1.0000")
    by_wall = generate_report.render_report(log_dir=tmp_path)
    assert "A bottleneck has been proven." in by_wall
    assert "remains the default" not in by_wall
    _seed(
        tmp_path,
        eager_wall="1.0000",
        lazy_wall="1.0000",
        eager_rss="1000",
        lazy_rss="800",
    )
    by_rss = generate_report.render_report(log_dir=tmp_path)
    assert "A bottleneck has been proven." in by_rss
    assert "remains the default" not in by_rss
    _seed(
        tmp_path,
        eager_wall="1.0000",
        lazy_wall="0.9900",
        eager_rss="1000",
        lazy_rss="999",
    )
    unproven = generate_report.render_report(log_dir=tmp_path)
    assert "A bottleneck has **not been proven**." in unproven
    assert "remains the default" in unproven


def test_wall_thresholds_stay_on_one_measurement(tmp_path: Path) -> None:
    _seed(tmp_path, eager_wall="1.0000", lazy_wall="1.0000")
    _write_side(
        tmp_path / "eager_1000000.txt",
        wall_marker="EAGER_WALL_TIME:",
        wall="20.0000",
        rows_marker="EAGER_ROWS:",
        rows=1_000_000,
    )
    _write_side(
        tmp_path / "lazy_1000000.txt",
        wall_marker="LAZY_WALL_TIME:",
        wall="19.0000",
        rows_marker="LAZY_ROWS:",
        rows=1_000_000,
    )
    _write_side(
        tmp_path / "eager_2000000.txt",
        wall_marker="EAGER_WALL_TIME:",
        wall="1.0000",
        rows_marker="EAGER_ROWS:",
        rows=2_000_000,
    )
    _write_side(
        tmp_path / "lazy_2000000.txt",
        wall_marker="LAZY_WALL_TIME:",
        wall="0.8000",
        rows_marker="LAZY_ROWS:",
        rows=2_000_000,
    )
    report = generate_report.render_report(log_dir=tmp_path)
    assert "A bottleneck has **not been proven**." in report
    assert "1.0000 s (5.0%)" in report


def test_each_log_needs_a_timed_command(tmp_path: Path) -> None:
    _seed(tmp_path)
    path = tmp_path / "lazy_5000000.txt"
    path.write_text(
        "LAZY_WALL_TIME: 1.0000\n"
        "LAZY_ROWS: 5000000\n"
        "\tMaximum resident set size (kbytes): 1000\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Missing timed command"):
        generate_report.render_report(log_dir=tmp_path)
