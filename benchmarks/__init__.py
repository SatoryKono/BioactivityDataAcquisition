"""Performance benchmarks for BioETL storage writers.

This package contains benchmarks for measuring performance of:
- Bronze layer writes (JSONL + zstd compression)
- Delta Lake writes (Silver/Gold layers)

Usage:
    pytest benchmarks/ --benchmark-only
    pytest benchmarks/ --benchmark-compare --benchmark-compare-fail=mean:15%

See docs/contracts/observability.md for performance thresholds.
"""
