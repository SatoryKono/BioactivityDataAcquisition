# scripts/diagnostics — Debug & Diagnostics

Manual probes, debug helpers, and one-off diagnostic tools.

## Unified Entry Point

```bash
python -m scripts.diagnostics --help
python -m scripts.diagnostics <command> [args...]
```

## Commands

| Command | Script | Description |
|---------|--------|-------------|
| `cleanup` | `cleanup_project.py` | Clean caches, build artifacts, and temp files |
| `cleanup-audit` | `cleanup_consolidate.py` | Consolidated cleanup and quality audit |
| `audit-structure` | `audit_structure.py` | Validate project structure against file policy |
| `ast-inventory` | `ast_inventory.py` | AST-based code inventory |
| `debug-pandera` | `debug_pandera.py` | Debug Pandera schema validation |
| `debug-storage` | `debug_storage_health.py` | Debug storage health checks |
| `inspect-vcr` | `_tmp_inspect_vcr.py` | Temporary VCR cassette inspector |
