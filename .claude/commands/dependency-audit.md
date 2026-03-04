---
description: Аудит зависимостей BioETL — CVE, обновления, лицензии, дерево. Действия: check, security, outdated, licenses, tree. Пример: /dependency-audit security
---

# /dependency-audit

Аудит зависимостей BioETL: CVE, обновления, совместимость, лицензии.

## Использование
```
/dependency-audit [action]
```

**Действия:** `check` (default, all), `security`, `outdated`, `licenses`, `tree`

---

## Инструкции

### `security`
```bash
uv run pip-audit --skip-editable 2>&1
osv-scanner scan . 2>&1 || echo "osv-scanner not installed"
uv run bandit -r src/bioetl/ -c pyproject.toml 2>&1 | tail -20
uv run python -m pytest tests/architecture/test_antipatterns.py::test_no_hardcoded_secrets -v --tb=short 2>&1
```

Report table: Tool | Findings | Critical | High | Medium | Low

### `outdated`
```bash
uv pip list --outdated 2>&1 || pip list --outdated 2>&1
```
Cross-reference with `pyproject.toml` pinned ranges.
Risk: LOW (patch), MEDIUM (minor), HIGH (major), BREAKING (incompatible).

### `licenses`
```bash
uv run pip-licenses --format=markdown --with-urls 2>&1 | head -50
```
Check: no GPL/AGPL dependencies.

### `tree`
```bash
uv pip tree 2>&1 | head -60 || pip install pipdeptree && pipdeptree 2>&1 | head -60
```
Show: version conflicts, circular dependencies.

### `check` (default)
Run all above sequentially. Summary report:

```
Dependency Audit Report
=======================
Date: YYYY-MM-DD
Total dependencies: N (direct) + M (transitive)

| Check | Status | Details |
|-------|:------:|---------|
| CVE/Vulnerabilities | ✅/❌ | N critical, M high |
| Outdated packages | ✅/⚠️ | N major, M minor behind |
| License compliance | ✅/❌ | All MIT/Apache/BSD |
| Version conflicts | ✅/❌ | N conflicts |
| Pinning quality | ✅/⚠️ | N unpinned |

Recommendations:
1. <action item>
```
