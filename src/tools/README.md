# BioETL Tools

Utility scripts for BioETL project maintenance and development.

## Structure and conventions

- **Canonical repository helpers** live under `scripts/` and are grouped by domain
  (`scripts.docs`, `scripts.schema`, `scripts.engineering.repo`, etc.).
- **`src/tools`** contains specialized helper utilities and supporting scripts that are
  not the main operational entry surface for contributors.
- **Environment setup** is `uv`-first: use `uv sync --extra dev --extra tests --extra tracing`.
- **Legacy wrappers** should be kept minimal and removed once all call-sites are
  migrated to canonical grouped entrypoints.
- Legacy `src/tools/scripts/check_*.py` validators should migrate toward
  grouped commands under `scripts.engineering.qa` / `scripts.schema`, with the old direct
  paths kept only as thin compatibility facades during the migration window.
- **Temporary files** (e.g., `_gen*.py`, `.cursor_tmp_*`) should be reviewed and cleaned up
  explicitly as part of a dedicated cleanup pass.

## Available Tools

### generate_docs_export.py

Manifest-driven generator for `docs/exports/*.merged.md` artifacts with legacy path
resolution for moved documentation trees.

**Location:** `src/tools/generate_docs_export.py`

**Typical usage:**

```bash
python src/tools/generate_docs_export.py --rewrite-manifest
```

**What it does:**

- Resolves legacy `docs/**` paths after folder migrations
- Rewrites the export manifest with normalized current paths
- Regenerates `docs/exports/full-documentation-no-plans-reports-skills.merged.md`
- Reports removed historical entries that are intentionally skipped

**Repository policy:**

- The merged export is a generated convenience artifact, not a normative source.
- It may be generated on demand and is not required to stay committed in git.

### file_merger.py

A versatile file merging and project analysis tool with multiple operation modes.

**Location:** `src/tools/file_merger.py`

**Requirements:** Python 3.11+ (standard library only)

#### Usage Modes

##### 1. Standard Mode - Merge files from any directory

```bash
# Merge Python and Markdown files from a directory
python src/tools/file_merger.py -i ./src -o combined.txt

# Merge only markdown files with custom sorting
python src/tools/file_merger.py -i ./docs -e md -o docs.md --sort by_extension

# Multiple extensions with custom exclude list
python src/tools/file_merger.py -i ./src -e py,yaml,json --exclude-dirs tests,__pycache__
```

##### 2. Project Code Mode - Merge by architectural layers

Creates 5 separate files, one for each architectural layer:

```bash
python src/tools/file_merger.py --merge_project_code
```

**Output files:**

- `interfaces_merged.md` - CLI and observability interfaces
- `infrastructure_merged.md` - Adapters and external integrations
- `domain_merged.md` - Core business logic and protocols
- `composition_merged.md` - DI container and factories
- `application_merged.md` - Pipeline logic and use cases

##### 3. Documentation Mode - Merge all documentation

Merges all markdown files from `docs/` directory:

```bash
# Default output: documentation_merged.md
python src/tools/file_merger.py --merge_documentation

# Custom output file
python src/tools/file_merger.py --merge_documentation -o my_docs.md
```

##### 4. Configs Mode - Merge all configuration files

Merges all YAML files from `configs/` directory:

```bash
# Default output: configs_merged.md
python src/tools/file_merger.py --merge_configs

# Custom output file
python src/tools/file_merger.py --merge_configs -o my_configs.md
```

##### 5. Project Structure Mode - Generate file tree

Creates ASCII tree visualization of entire project:

```bash
# Default output: project_structure.md
python src/tools/file_merger.py --project_structure

# Custom output file
python src/tools/file_merger.py --project_structure -o structure.md
```

By default, project structure generation skips common generated or duplicated
directories such as `.venv`, `.git`, `.worktrees`, `.cache`, `.pytest_cache`,
`reports`, `logs`, `output`, `data`, and `node_modules`. Symlinked directories
are listed but not traversed recursively.

**Example output:**

```
./
├── .claude/
│   ├── prompts/
│   └── PROJECT_CONTEXT.md
├── configs/
│   └── pipelines/
└── src/
    └── bioetl/
        ├── application/
        ├── domain/
        └── infrastructure/
```

#### Options

| Option             | Description                | Default                                                                                            |
| ------------------ | -------------------------- | -------------------------------------------------------------------------------------------------- |
| `-i, --input-dir`  | Input directory to scan    | Required for standard mode                                                                         |
| `-o, --output`     | Output file path           | `merged_output.txt`                                                                                |
| `-e, --extensions` | Comma-separated extensions | `md,py`                                                                                            |
| `--encoding`       | File encoding              | `utf-8`                                                                                            |
| `--exclude-dirs`   | Directories to exclude     | `__pycache__,.git,.venv,node_modules,.ai,data,.worktrees,.cache,.pytest_cache,reports,logs,output` |
| `--sort`           | Sorting method             | `alphabetical` (also: `by_extension`, `none`)                                                      |

#### Output Format

Each merged file includes:

```
================================================================================
File: example.py
Path: relative/path/to/example.py
================================================================================
<file contents>
```

Statistics are printed at the end:

- Total files processed
- Total size (human-readable)
- Breakdown by extension

#### Error Handling

- **Encoding errors**: Skipped with warning (UnicodeDecodeError)
- **Permission errors**: Skipped gracefully
- **Missing directories**: Clear error messages

#### Use Cases

1. **Code Review**: Merge layer code for AI/LLM analysis
1. **Documentation**: Create unified doc for external sharing
1. **Debugging**: Quick overview of configuration state
1. **Project Analysis**: Understand project structure at a glance
1. **Context Building**: Generate context files for AI assistants

______________________________________________________________________

## Adding New Tools

When adding new tools to this directory:

1. **Use Python 3.11+** type hints and Google-style docstrings
1. **Make it executable**: `chmod +x your_tool.py`
1. **Add shebang**: `#!/usr/bin/env python3`
1. **Document in this README** with usage examples
1. **Follow project patterns**: See `file_merger.py` as reference

## Tool Guidelines

- Prefer standard library over external dependencies
- Include `--help` with clear examples
- Handle errors gracefully with informative messages
- Output statistics when processing multiple files
- Use `get_project_root()` pattern for path resolution

______________________________________________________________________

## Scripts

### apply_entity_naming_rename_plan.py

Manual architecture refactor helper for applying precomputed entity naming waves.

**Location:** `src/tools/apply_entity_naming_rename_plan.py`

**Typical usage:**

```bash
python src/tools/apply_entity_naming_rename_plan.py --wave W1-domain-entities
python src/tools/apply_entity_naming_rename_plan.py --wave W2-gold-contract-schemas --apply
```

### create_pipeline.py

Legacy pipeline scaffolding helper retained as a specialized manual tool.

**Location:** `src/tools/create_pipeline.py`

**Typical usage:**

```bash
python src/tools/create_pipeline.py --provider <name> --entity <name> --dry-run
```

Prefer the maintained project workflow for new pipelines when possible; use this helper only for targeted legacy scaffolding cases.

### apply_elk_layout.py

Diagram-layout helper for adding or auditing ELK layout hints in Mermaid sources.

**Location:** `src/tools/apply_elk_layout.py`

**Typical usage:**

```bash
python src/tools/apply_elk_layout.py --dry-run
python src/tools/apply_elk_layout.py
```

### differentiate_linkstyle.py

Diagram semantics helper for assigning differentiated Mermaid `linkStyle` classes.

**Location:** `src/tools/differentiate_linkstyle.py`

**Typical usage:**

```bash
python src/tools/differentiate_linkstyle.py --dry-run
python src/tools/differentiate_linkstyle.py
```

### scripts/config_matrix_generator.py

Generates a cross-config comparison matrix and discrepancy report for entity and composite YAMLs.

**Location:** `src/tools/scripts/config_matrix_generator.py`

**Typical usage:**

```bash
python -m scripts.schema generate-config-matrix
```

The direct legacy path remains available only as a thin compatibility wrapper
during the migration window, but the canonical command above should be used for
new integrations.

### scripts/validate_unified_configs.py

Legacy standalone validator for unified entity YAML configs.

**Location:** `src/tools/scripts/validate_unified_configs.py`

**Typical usage:**

```bash
python -m scripts.schema validate-unified-configs
```

The direct legacy path remains available only as a thin compatibility wrapper
during the migration window, but the canonical command above should be used for
new integrations.

Use `python -m scripts.schema validate-configs` only for the maintained JSON
Schema / agent-canonical validation flow.

### Legacy architecture/dependency check scripts

The following direct paths remain available for compatibility, but new
integrations should prefer the grouped QA entrypoints:

- `python -m scripts.engineering.qa check-architecture`
- `python -m scripts.engineering.qa check-app-deps`
- `python -m scripts.engineering.qa check-constructor-args`

### duplicate_function_analyzer.py

AST-анализатор дубликатов функций в выбранной области (по умолчанию `src/bioetl/application/**/utils.py`,
`src/bioetl/infrastructure/**/utils.py`).

**Location:** `src/tools/scripts/duplicate_function_analyzer.py`

#### Usage

```bash
# Default scope
python -m scripts.engineering.qa analyze-duplicate-functions

# Custom scope
python -m scripts.engineering.qa analyze-duplicate-functions \
  --pattern src/bioetl/application/**/utils.py \
  --pattern src/bioetl/infrastructure/**/utils.py \
  --report reports/duplicate_function_report.md
```

The direct legacy path remains available for compatibility during the migration
window, but the canonical command above should be used for new integrations.
