# Graph Memory

`src/memory/graph/` is the canonical implementation home for the deterministic
BioETL graph used for Neo4j-backed topology, ownership, and impact analysis.

Current state:

- `sync.py` builds and optionally applies the graph snapshot
- `query.py` exposes operator-facing query shortcuts over the canonical graph
- `importers/expanded_json.py` imports file-level relation projections from
  optional expanded graph snapshots
- `mappings.yaml` is the canonical graph mapping/configuration surface
- `ontology.yaml` records the high-signal ontology families and invariants
- `projections/` and `indexes/` are rebuild-only output locations for compact
  relation artifacts such as `file_references.jsonl` and `file_relations.json`
- `scripts/memory/` still exists as a compatibility surface for legacy callers

Primary entrypoints:

```bash
python -m memory.graph sync --help
python -m memory.graph query --help
python -m memory.graph.sync --help
python -m memory.graph.query --help
python -m memory.graph.importers.expanded_json --help
```
