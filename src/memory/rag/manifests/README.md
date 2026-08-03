# RAG Manifests

This legacy directory is a compatibility fallback for deterministic RAG corpus
artifacts. New local builds default to
`src/memory/derived/rag/manifests/` and neither lane commits generated JSON or
JSONL files.

```bash
python -m memory.rag.indexing --print-summary
```

Rebuild-only artifacts:

- `corpus_catalog.json`
- `chunks.jsonl`

The current MVP indexes deterministic sources from:

- `docs/00-project/`
- `docs/02-architecture/decisions/`
- `docs/05-operations/runbooks/`
- `src/bioetl/`
- `tests/`
- `configs/`

Archive and generated-report surfaces are excluded by policy.

Validate a generated pair before use:

```bash
python -m memory.rag.validation \
  --manifest-dir src/memory/derived/rag/manifests \
  --require-build-scope full
```
