# Graph Memory

`src/memory/graph/` is the canonical implementation home for the deterministic
BioETL graph used for Neo4j-backed topology, ownership, and impact analysis.

Current state:

- `sync.py` builds and optionally applies the graph snapshot
- `query.py` exposes operator-facing query shortcuts over the canonical graph
- `scripts/memory/` still exists as a compatibility surface for legacy callers

Primary entrypoints:

```bash
python -m memory.graph sync --help
python -m memory.graph query --help
python -m memory.graph.sync --help
python -m memory.graph.query --help
```
