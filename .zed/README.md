# Zed Editor Configuration for BioETL

## Overview

This directory contains Zed editor configuration optimized for BioETL development workflow.

## Configuration Files

- `settings.json` - Main editor settings, LSP configuration, tasks, and agent profiles
- `keymap.json` - Keyboard shortcuts and bindings
- `snippets/` - BioETL scaffolds (prefix `bioetl-`: value objects, ports, pipeline stages, tests, Click commands, YAML configs)

## Recent Improvements

### 1. Python Auto-Formatting Enabled
- `languages.Python.format_on_save: on` (was `off` before Wave 1) — uses Ruff as formatter with `source.organizeImports.ruff: true`
- `soft_wrap: preferred_line_length` (88, matches `pyproject.toml max_line_length` + `.editorconfig max_line_length 88`)
- `Markdown.format_on_save: off` intentionally — preserves `requirements-traceability-crosswalk` tables
- `YAML/JSON/Docker Compose: on` — consistent with `.editorconfig indent_size 2` for those types

### 2. Project-Specific Tasks (SSOT: `.zed/tasks.json`)
SSOT — `.zed/tasks.json` (24 lanes). `settings.json` holds no `tasks` section (Zed merges both, `tasks.json` wins). Access via `Ctrl+Shift+P` → "Tasks" or `Ctrl+Shift+T`:

- **Format: code / Check: lint / Check: format / Check: types / Test: current file** + full lanes: `smoke`, `unit-fast`, `architecture-fast`, `integration-replay`, `contracts`, `security`, `e2e-smoke`, `coverage-local`, `architecture imports`, `dead code`, `complexity`, `dependencies`, `MCP manifests`
- `Check: format` is read-only (`ruff format --check .`): fast pre-commit gate, unlike mutating `Format: code`
- Legacy short list in `settings.json` kept for back-compat until 2026-08, now `tasks.json` only

### 3. Code Lenses Enabled
- Test code lenses for quick test execution
- Go-to-definition code lenses for navigation
- Code actions shown in gutter

### 4. Editor UX Improvements
- Inline completions always shown
- Trailing whitespace visible
- Indentation and bracket pair guides enabled
- Scrollbar set to auto
- Project panel with file/folder icons and indent guides

### 5. Keyboard Shortcuts (keymap.json)
Comprehensive keymap with:
- Standard VS Code-like bindings (Ctrl+P, Ctrl+Shift+F, etc.)
- Navigation shortcuts (Alt+Left/Right for back/forward)
- Multi-cursor editing (Ctrl+Alt+Up/Down)
- Terminal toggles (Ctrl+Enter, Ctrl+`)
- Task management (F9 rerun, Ctrl+F9 cancel, `Ctrl+K T` test current file, `Ctrl+K L` lint, `Ctrl+K Y` types, `Ctrl+K F` format selection)

## Agent Profiles

### bioetl-ask (Read-Only)
- Default profile for code review and analysis
- Cannot edit files, run terminal commands, or create directories
- Can read files, search code, and use web search

### bioetl-write (Write-Capable)
- For code changes and refactoring
- Full write access with safety guards
- Protected from editing `.env` files and secrets

## LSP Configuration

### Python
- **basedpyright**: Strict type checking (Python 3.12)
- **ruff**: Linting, formatting, and import organization
- **pylsp**: Explicitly disabled

### Other Languages
- **YAML**: Auto-format on save
- **JSON/JSONC**: Auto-format on save
- **Docker Compose**: Auto-format on save with docker-compose LSP

## Terminal Configuration

- Environment variables set automatically:
  - `PYTHONDONTWRITEBYTECODE=1`, `VCR_RECORD_MODE=none`, `VIRTUAL_ENV=.venv-win` (Windows-first resolution; `detect_venv` still lists per-OS dirs: `.venv-win` / `.venv` / `.venv-wsl`)
- Font: JetBrains Mono, size 14 — Line height: Comfortable — Auto-detects virtual environments (see `AGENTS.md` routes)

## File Scan Exclusions

Large directories and caches are excluded from file scanning for performance (Wave 1 extended):
- `.git`, `.svn`, `.hg`, `.jj`, `CVS`
- `node_modules`, `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`
- `.venv*`, `venv`, `env`, `.env*`
- `dist`, `build`, `coverage`, `htmlcov` (single entry), `reports/coverage`, `reports`, `reports/audit-runs` (80+ dirs), `logs`, `data`, `.codex`, `.claude`, `.junie`, `.devin`, `.opencode`, `.cursor`, `.gemini`, `.grok`, `.qodo`, `.muse`
- `target`, `generated`, `data/debug_exports`, `.benchmarks`, `test-output`, `.import_linter_cache`

## Helper Scripts

The following scripts in `scripts/engineering/dev/` are Zed-safe wrappers:

- `zed_pytest_lane.py` - Run pytest with marker expressions (Windows-safe)
- `zed_lint_imports.py` - Run import-linter with `.importlinter` config
- `zed_mypy.py` - Run mypy matching CI scope (`src/bioetl` only)
- `zed_run.py` - Run local pipeline
- `zed_env_doctor.py` - Environment health checks

## Usage Tips

### Quick Test Execution
1. Open a test file
2. Click the code lens above the test function
3. Or use `Ctrl+Shift+T` → "Test: Current File"

### Type Checking
1. Use `Ctrl+Shift+T` → "Type Check (mypy)" (or `Ctrl+K Y`)
2. Results match CI gate: `mypy --config-file pyproject.toml --strict --no-incremental src/bioetl`

### Verify Before Commit
Fast read-only sequence, no mutations: `Check: format` → `Check: lint` → `Check: types` → `Test: unit-fast`.
Rerun the last task with `F9` instead of reopening the picker.

### Import Organization
- Automatic on save via Ruff
- Can also trigger manually via code actions (`Ctrl+Space`)

### Git Graph (built-in, Zed ≥ 0.231)

Git Graph is native (not a VS Code extension). It **does not poll on a timer**.
It reloads when HEAD or the branch list changes — after `git: fetch` / pull /
local commit, or when you reopen the tab.

| Action | Shortcut |
| --- | --- |
| Git Panel | `Ctrl+Shift+G` |
| Open Git Graph | `Ctrl+Alt+Shift+G` |
| Fetch remotes (refresh graph) | `Ctrl+Alt+F` |
| Go to line | `Ctrl+;` |

Or Command Palette: `git graph: Open`, `git: Fetch`.

Also: Git Panel → History / the graph button at the **bottom** of the panel.

`Ctrl+G` is **not** remapped here so Zed's git chord (`ctrl-g ctrl-g` fetch,
`ctrl-g d` diff) still works. Go-to-line is `Ctrl+;`.

On this repo (`/mnt/e/...`) `git status` can be slow; if the graph spins,
fetch from a native NTFS worktree or wait for the scan to finish.

## Troubleshooting

### Tasks Not Showing
- Ensure `.zed/tasks.json` is valid JSON (SSOT for tasks; no `tasks` section in `settings.json`)
- Check that `$ZED_WORKTREE_ROOT` resolves to the project root (`$ZED_FILE` / `$ZED_SYMBOL` for file tasks)

### LSP Not Working
- Verify a venv exists (`.venv-win` / `.venv` / `.venv-wsl`) — `terminal.detect_venv` resolves per-OS
- Check that `basedpyright` and `ruff` are installed
- Run `python -m scripts.engineering.dev.zed_env_doctor` to diagnose (or the `Environment: verify` task)

### Format on Save Not Working
- Check that `format_on_save` is set to `on` for the language
- Verify Ruff is installed and configured
- Check for syntax errors in the file

## Further Customization

To add more tasks, edit `.zed/tasks.json`:

```json
{
  "label": "My Custom Task",
  "command": "$ZED_WORKTREE_ROOT/.venv-win/Scripts/python.exe",
  "args": ["scripts/engineering/dev/zed_run.py", "-m", "my.module"],
  "cwd": "$ZED_WORKTREE_ROOT",
  "reveal": "no_focus",
  "hide": "never",
  "save": "all",
  "allow_concurrent_runs": false
}
```

New tasks must keep the repo contract (`tests/unit/repo_backed/scripts/test_zed_workspace_config.py`):
unique `label`, `cwd` = `$ZED_WORKTREE_ROOT`, venv-python `command`, explicit
`save`/`reveal`/`hide`/`allow_concurrent_runs`.

To add more keybindings, edit `keymap.json`:

```json
{
  "bindings": {
    "ctrl-k ctrl-m": "my_custom_action"
  }
}
```

## References

- Zed Documentation: https://zed.dev/docs
- BioETL Development Guide: `docs/00-project/RULES.md`
- BioETL AI Runtime: `docs/00-project/ai/agents/`