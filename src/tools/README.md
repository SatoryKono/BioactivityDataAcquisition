# BioETL Tools

Utility scripts for BioETL project maintenance and development.

## Structure and conventions

- **Canonical tools** live under `src/tools` and `src/tools/scripts`.
- **Environment setup** uses `./scripts/dev/dev_setup.sh` as the primary entrypoint.
- **Root `scripts/`** should be treated as thin wrappers or legacy entrypoints; prefer
  `python src/tools/scripts/<tool>.py` (or `PYTHONPATH=src python -m tools.scripts.<tool>`).
- **Compatibility wrappers** currently include:
  - `scripts/lint_terminology.py` → `src/tools/scripts/lint_terminology.py`
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

| Option | Description | Default |
|--------|-------------|---------|
| `-i, --input-dir` | Input directory to scan | Required for standard mode |
| `-o, --output` | Output file path | `merged_output.txt` |
| `-e, --extensions` | Comma-separated extensions | `md,py` |
| `--encoding` | File encoding | `utf-8` |
| `--exclude-dirs` | Directories to exclude | `__pycache__,.git,.venv,node_modules` |
| `--sort` | Sorting method | `alphabetical` (also: `by_extension`, `none`) |

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
2. **Documentation**: Create unified doc for external sharing
3. **Debugging**: Quick overview of configuration state
4. **Project Analysis**: Understand project structure at a glance
5. **Context Building**: Generate context files for AI assistants

---

## Adding New Tools

When adding new tools to this directory:

1. **Use Python 3.11+** type hints and Google-style docstrings
2. **Make it executable**: `chmod +x your_tool.py`
3. **Add shebang**: `#!/usr/bin/env python3`
4. **Document in this README** with usage examples
5. **Follow project patterns**: See `file_merger.py` as reference

## Tool Guidelines

- Prefer standard library over external dependencies
- Include `--help` with clear examples
- Handle errors gracefully with informative messages
- Output statistics when processing multiple files
- Use `get_project_root()` pattern for path resolution

---

## Scripts

### duplicate_function_analyzer.py

AST-анализатор дубликатов функций в выбранной области (по умолчанию `src/bioetl/application/**/utils.py`,
`src/bioetl/infrastructure/**/utils.py`).

**Location:** `src/tools/scripts/duplicate_function_analyzer.py`

#### Usage

```bash
# Default scope
python src/tools/scripts/duplicate_function_analyzer.py

# Custom scope
python src/tools/scripts/duplicate_function_analyzer.py \
  --pattern src/bioetl/application/**/utils.py \
  --pattern src/bioetl/infrastructure/**/utils.py \
  --report reports/duplicate_function_report.md
```
