# scripts/docs — Documentation Maintenance

Documentation lint, build, drift checks, and maintenance tooling.

## Unified Entry Point

```bash
python -m scripts.docs --help
python -m scripts.docs <command> [args...]
```

## Commands

| Command | Script | Description |
|---------|--------|-------------|
| `check-links` | `check_doc_links.py` | Check documentation links, specs, and configs |
| `check-drift` | `check_doc_drift.py` | Check documentation drift (ports, classes) |
| `check-docstrings` | `check_docstring_coverage.py` | Check docstring coverage |
| `check-kpi` | `report_docs_kpi.py` | Report documentation KPI metrics |
| `fix-links-auto` | `fix_doc_links_auto.py` | Auto-fix broken documentation links |
| `fix-links-explicit` | `fix_doc_links_explicit.py` | Fix documentation links with explicit rules |
| `fix-link-warnings` | `fix_link_warnings.py` | Fix link warnings in specified files |
| `audit-sentence` | `sentence_doc_audit.py` | Sentence-level documentation audit |

## Other Files

| File | Description |
|------|-------------|
| `build_docs_site.sh` | Build MkDocs documentation site |
