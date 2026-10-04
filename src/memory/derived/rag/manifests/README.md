# Derived RAG manifests

This is the preferred local output lane for the rebuild-only RAG catalog/chunk
pair. Git tracks only this README and `.gitignore`; generated
`corpus_catalog.json` and `chunks.jsonl` must be rebuilt from current repository
sources.

Build and validate a canonical full corpus:

```bash
python -m memory.rag.indexing --build-scope full --print-summary
python -m memory.rag.validation \
  --manifest-dir src/memory/derived/rag/manifests \
  --require-build-scope full
```

Workflow-scoped manifests are ephemeral and must use a temporary or external
output directory. They are never a canonical full-corpus replacement.
