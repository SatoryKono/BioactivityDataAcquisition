# scripts/diagnostics — Debug & Diagnostics

Manual probes, debug helpers, and one-off diagnostic tools.

## Unified Entry Point

```bash
python -m scripts.engineering.diagnostics --help
python -m scripts.engineering.diagnostics <command> [args...]
```

## Commands

| Command           | Script                                                    | Description                                    |
| ----------------- | --------------------------------------------------------- | ---------------------------------------------- |
| `cleanup`         | `scripts/engineering/diagnostics/cleanup_project.py`      | Clean caches, build artifacts, and temp files  |
| `cleanup-audit`   | `scripts/engineering/diagnostics/cleanup_consolidate.py`  | Consolidated cleanup and quality audit         |
| `audit-structure` | `scripts/engineering/diagnostics/audit_structure.py`      | Validate project structure against file policy |
| `ast-inventory`   | `scripts/engineering/diagnostics/ast_inventory.py`        | AST-based code inventory                       |
| `debug-pandera`   | `scripts/engineering/diagnostics/debug_pandera.py`        | Debug Pandera schema validation                |
| `debug-storage`   | `scripts/engineering/diagnostics/debug_storage_health.py` | Debug storage health checks                    |
| `inspect-vcr`     | `scripts/engineering/diagnostics/_tmp_inspect_vcr.py`     | Temporary VCR cassette inspector               |

## When to Use

| Command           | When                                                                                                                                                                         | Trigger                      |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------- |
| `cleanup`         | Disk space issues or stale caches; cleans `.pyc`, `__pycache__`, build artifacts, forbidden root output dirs like `.coverage-sharded/`, `node_modules/`, `test-output/`, and temp files. Use `--apply` to execute (dry-run by default), `--purge-logs` for full cleanup | Manual, periodic maintenance |
| `cleanup-audit`   | Comprehensive project hygiene check; finds unused YAML configs, duplicate functions, unused imports, stale dependencies                                                      | Manual, periodic audit       |
| `audit-structure` | After restructuring directories or adding new modules; validates project layout against `03-file-policy.md`. Use `--strict` for SHOULD violations, `--json` for CI           | Manual or CI gate            |
| `ast-inventory`   | When you need a complete inventory of classes, functions, and constants by layer; generates JSON report in `reports/inventory/`                                              | Manual, code analysis        |
| `debug-pandera`   | When Pandera DataFrame validation fails unexpectedly; helps isolate schema vs data issues                                                                                    | Manual, troubleshooting      |
| `debug-storage`   | When storage operations fail; checks writability of data storage directories                                                                                                 | Manual, troubleshooting      |
| `inspect-vcr`     | When VCR cassette contents need examination for debugging test failures                                                                                                      | Manual, troubleshooting      |

`inspect-vcr` is intentionally a temporary diagnostic surface backed by
`_tmp_inspect_vcr.py`; repository-local references to it should be treated as
legacy troubleshooting evidence rather than as proof of a stable long-term
workflow command.

## Other Files

| File                                                                       | Description                                                                  |
| -------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `scripts/engineering/diagnostics/generate_src_bioetl_refactor_evidence.py` | Generate evidence artifacts for focused `src/bioetl` refactor investigations |
