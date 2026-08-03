# Derived Timeline Events

This directory is the preferred rebuild-only output lane for deterministic
timeline JSONL projections. Generated `*.jsonl` files must not be committed.

Use a temporary output root for task-scoped refreshes. The legacy
`src/memory/timeline/events/` lane remains a read-compatible fallback during
migration.
