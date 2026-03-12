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

## When to Use

| Command | When | Trigger |
|---------|------|---------|
| `check-links` | After editing docs; validates internal links, spec files, contracts, legacy path guardrails | CI gate (`docs.yml`, every PR) |
| `check-drift` | After renaming classes, moving modules, or changing ports; detects doc/code desync | CI gate (`architecture.yml`) |
| `check-docstrings` | After adding new modules/classes/functions; enforces coverage thresholds (modules 100%, classes 95%, functions 90%) | CI gate (`architecture.yml`) |
| `check-kpi` | Weekly documentation health tracking; generates coverage, links, and drift metrics | Scheduled weekly (Monday 4:00 UTC) |
| `fix-links-auto` | After bulk renames or restructuring; auto-rewrites broken doc links | Manual, after refactoring |
| `fix-links-explicit` | When specific broken links need targeted fixes with explicit rules | Manual, on-demand |
| `fix-link-warnings` | After `check-links` reports warnings; fixes link format issues in specified files | Manual, on-demand |
| `audit-sentence` | Before release or documentation review; audits sentence structure and grammar | Manual, pre-release |

## Other Files

| File | Description |
|------|-------------|
| `build_docs_site.sh` | Build MkDocs documentation site |
