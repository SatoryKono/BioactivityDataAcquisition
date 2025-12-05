> Scope:
> - USE WHEN writing files or serializing data; require stable sorting, UTC, canonical JSON, atomic writes, meta.yaml
> - Use when editing files matching: `src/**/*.py`, `data/**/*.csv`, `data/**/*.json`, `docs/**/*.md`
# DETERMINISM
- Sort rows by business keys with stable sort; preserve schema-defined column order.
- Timestamps in UTC ISO-8601 only.
- JSON with sorted keys; CSV preserves schema order.
- All writes use temp → fsync → atomic rename.

# QC SIDECAR
- For each output, write `*.meta.yaml` with checksums, row_count, pipeline_version, git_commit, generated_at_utc.
- Business keys explicit; use BLAKE2 for composite key/hash derivations.

# REFERENCE
See [docs/styleguide/04-deterministic-io.md](../../docs/styleguide/04-deterministic-io.md) for detailed documentation.
