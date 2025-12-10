# Cleanup Policy

This document defines deterministic cleanup rules and automation for removing caches, build artifacts and temporary files.

## Whitelist Patterns

- Python caches: `**/__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `**/*.pyc`, `**/*.pyo`, `**/*.pyd`
- Coverage: `.coverage*`, `coverage.xml`, `htmlcov/`
- Build/dist: `build/`, `dist/`, `**/*.egg-info/`
- Logs/temp: `**/*.log`, `**/*.tmp`, `**/*report*.txt`, `full_log.txt`, `final_report*.txt`, `project_rules_failures.txt`
- IDE/OS: `.idea/workspace.xml`, `.DS_Store`, `Thumbs.db`, `.ipynb_checkpoints/`
- JS: `node_modules/`, `.next/`, `web/dist/`
- Vercel cache: `.vercel/cache/` (keep `.vercel/project.json`)

## Exclusions

Do not remove:

- Source code `src/**`, configs `configs/**`, tests `tests/**`, documentation `docs/**`
- Golden data `qc/golden/**`
- Input datasets `data/input/**`
- Infra settings `.gitignore`, `.pre-commit-config.yaml`, `.vscode/settings.json`, `.windsurf/**`, `.trae/**`, `.cursor/rules/**`

## Automation

- `.gitignore` includes all whitelist patterns
- Script `src/tools/cleanup_project.py`:
  - `--dry-run` prints candidates and sizes
  - `--apply` deletes candidates
  - `--archive-logs` moves logs to `reports/` instead of deleting
  - `--purge-logs` forces deletion of logs
  - Structured logging via UnifiedLogger

## Verification

- Run `pytest -q` without network; golden tests stay green
- Class inventory baseline (`tests/project_rules/class_inventory_baseline.json`) remains unchanged
- Optional smoke-run of one pipeline shows identical artifacts before/after

## Commands

- Dry-run: `python src/tools/cleanup_project.py`
- Apply with log archive: `python src/tools/cleanup_project.py --apply --archive-logs`
- Full purge: `python src/tools/cleanup_project.py --apply --purge-logs`

## CI & Pre-commit

- Pre-commit hook forbids committing `*.pyc` and `__pycache__` (see `.pre-commit-config.yaml`)
- CI workflow `compiled-artifacts-block.yml` fails builds if compiled artifacts are present
