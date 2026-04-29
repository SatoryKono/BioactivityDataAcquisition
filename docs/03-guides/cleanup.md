# Repository Cleanup Guide

This guide documents the cleanup procedures and best practices for maintaining the BioETL repository hygiene.

## 🗑️ Cleanup Procedures

Before cleaning retention-sensitive surfaces, use
[Retention-Sensitive Cleanup](../05-operations/runbooks/retention-sensitive-cleanup.md).
Blanket deletion is prohibited for `data/**`, control-plane artifacts,
`tests/fixtures/**`, `tests/fixtures/vcr/**`, `docs/reports/**`, `reports/**`,
and `docs/99-archive/**`.
GitHub cleanup requests for those surfaces must use
`.github/ISSUE_TEMPLATE/retention_sensitive_cleanup.yml`.

### 1. Deterministic Local Cleanup

Use the maintained deterministic cleanup entrypoints first:

```bash
# Preview local cache/build cleanup
make clean-local-artifacts DRY_RUN=1

# Apply local cache/build cleanup
make clean-local-artifacts

# Include local worktree/rollback purge
make clean-local-artifacts PURGE_WORKTREES=1
```

### 2. Repo-Hygiene Review Lane

Use the repo cleanup tool only as an exact candidate discovery lane:

```bash
# Dry run (show exact review/apply candidates)
python -m scripts.ops.support.repo.cleanup_repository --dry-run \
  --report-json reports/quality/root-hygiene-cleanup-classification.json

# Apply only policy-approved local artifact candidates
python -m scripts.ops.support.repo.cleanup_repository --apply
```

Tracked policy violations reported by this tool still require explicit git
review; they are not blanket-deleted by the script.

### 3. Git LFS Setup

For large files (VCR cassettes):

```bash
# Install Git LFS
git lfs install

# Track VCR cassettes
git lfs track "tests/fixtures/vcr/**/*.yaml"

# Add and commit
git add .gitattributes
git commit -m "feat: implement Git LFS for VCR cassettes"
```

## 🛡️ Prevention Measures

### .gitignore Patterns

The repository `.gitignore` includes patterns to prevent common cache and temporary files:

```gitignore
# Virtual environments
.python-user/

# AI agent temporary files
.codex_tmp/
.codex_tmp_issue_*.md

# Prevent root-level test scripts
/test_*.js
/test_*.py
/test_*.json
```

### Pre-commit Hooks

The repository includes pre-commit hooks that prevent cache files from being committed:

- `forbid-cache-files`: Blocks `__pycache__`, `.pyc`, `.pytest_cache`, etc.
- `check-added-large-files`: Blocks files >1MB (configurable)

## 📊 Repository Hygiene Standards

### What Should NOT Be in Git

1. **Cache Directories**: `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`
1. **Temporary Files**: `*.pyc`, `*.pyo`, `*.tmp`, `*.log`
1. **Local Environments**: `.venv/`, `.python-user/`, `venv/`
1. **AI Agent Files**: `.codex_tmp/`, `.codex_tmp_issue_*.md`
1. **Root Test Scripts**: `test_*.js`, `test_*.py`, `test_*.json` in repository root

### What SHOULD Be in Git

1. **Source Code**: All files in `src/`
1. **Configuration**: `configs/`, `pyproject.toml`, CI/CD files
1. **Tests**: All test files in `tests/`
1. **Documentation**: All files in `docs/`
1. **Historical Archives**: `scripts/ops/archive/`, `docs/99-archive/` (for reference)

## 🔧 Maintenance Schedule

### Weekly

- Run repo-hygiene review lane in dry-run mode
- Check repository size growth
- Review CI/CD pipeline results

### Monthly

- Run local cleanup wave (if needed)
- Update `.gitignore` patterns
- Review pre-commit hook effectiveness

### Quarterly

- Archive old documentation
- Review historical migration scripts
- Optimize Git LFS usage

## 📈 Impact Metrics

### Before Cleanup

- Repository size: ~777 MB
- Cache/temporary files: ~250 MB (32%)
- Orphan files: ~20 files

### After Cleanup

- Repository size: ~776.7 MB (310KB reduction)
- Cache/temporary files: ~0 MB
- Orphan files: ~0 files
- Prevention: Active via `.gitignore` and pre-commit hooks

## 🎯 Best Practices

1. **Always use dry-run first**: `python -m scripts.ops.support.repo.cleanup_repository --dry-run`
1. **Attach machine-readable evidence**: add `--report-json reports/quality/root-hygiene-cleanup-classification.json`
1. **Commit cleanup changes separately**: Makes reviews easier
1. **Document exceptions**: If you need to keep a cache file, document why
1. **Use Git LFS for large files**: Anything >1MB should use LFS
1. **Keep historical archives**: They provide valuable context

## 🔗 Related Documents

- [Documentation Publication Policy](../00-project/governance/06-doc-publication-policy.md)
- [Documentation Navigation Policy](../00-project/governance/07-doc-nav-policy.md)
- [Retention-Sensitive Cleanup](../05-operations/runbooks/retention-sensitive-cleanup.md)
- [Git LFS Documentation](https://git-lfs.com/)
- [Pre-commit Framework](https://pre-commit.com/)
