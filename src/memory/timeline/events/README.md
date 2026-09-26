# Timeline Events

This directory stores deterministic JSONL event projections for the project
memory subsystem.

Generate artifacts with:

```bash
python -m memory.timeline.ingest_runs
python -m memory.timeline.ingest_ci
python -m memory.timeline.ingest_incidents
```

Current MVP surfaces:

- `runs.jsonl` from control-plane manifests and ledgers
- `ci.jsonl` from GitHub workflow definitions
- `incidents.jsonl` from active incident/failure runbooks
