# Repository Cleanup Guide

This guide documents the cleanup procedures and best practices for maintaining the BioETL repository hygiene.

## 🗑️ Cleanup Procedures

### 1. Manual Cleanup

For one-time cleanup of existing repository issues:

```bash
# Remove cache directories
rm -rf .python-user/ .codex_tmp/ __pycache__/ .pytest_cache/ .mypy_cache/ .ruff_cache/

# Remove temporary files
rm -f test_*.js test_*.json *.tmp *.log

# Remove orphan files from root
rm -f test_*.py  # Be careful with this one!
```

### 2. Automated Cleanup

Use the provided cleanup script:

```bash
# Dry run (show what would be cleaned)
python scripts/ops/cleanup_repository.py --dry-run

# Actually clean
python scripts/ops/cleanup_repository.py

# Clean specific categories
python scripts/ops/cleanup_repository.py --cache --temp
```

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
2. **Temporary Files**: `*.pyc`, `*.pyo`, `*.tmp`, `*.log`
3. **Local Environments**: `.venv/`, `.python-user/`, `venv/`
4. **AI Agent Files**: `.codex_tmp/`, `.codex_tmp_issue_*.md`
5. **Root Test Scripts**: `test_*.js`, `test_*.py`, `test_*.json` in repository root

### What SHOULD Be in Git

1. **Source Code**: All files in `src/`
2. **Configuration**: `configs/`, `pyproject.toml`, CI/CD files
3. **Tests**: All test files in `tests/`
4. **Documentation**: All files in `docs/`
5. **Historical Archives**: `scripts/ops/archive/`, `docs/99-archive/` (for reference)

## 🔧 Maintenance Schedule

### Weekly
- Run cleanup script in dry-run mode
- Check repository size growth
- Review CI/CD pipeline results

### Monthly
- Run full cleanup (if needed)
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

1. **Always use dry-run first**: `python scripts/ops/cleanup_repository.py --dry-run`
2. **Commit cleanup changes separately**: Makes reviews easier
3. **Document exceptions**: If you need to keep a cache file, document why
4. **Use Git LFS for large files**: Anything >1MB should use LFS
5. **Keep historical archives**: They provide valuable context

## 🔗 Related Documents

- [Documentation Publication Policy](../00-project/governance/06-doc-publication-policy.md)
- [Documentation Navigation Policy](../00-project/governance/07-doc-nav-policy.md)
- [Git LFS Documentation](https://git-lfs.com/)
- [Pre-commit Framework](https://pre-commit.com/)
