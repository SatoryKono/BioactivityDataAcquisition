# Scripts CLI Wrapper Caller Matrix

This note tracks compatibility-wrapper retention for the `scripts/*` CLI
refactor wave and supports RF-008.

## Scope

Candidate wrappers reviewed:

| Path | Current role | Observed callers | Deletion status |
| --- | --- | --- | --- |
| `scripts/docs/check_doc_links.py` | special-case legacy shim | `.github/workflows/docs.yml`, docs governance pages, tests importing historical module surface | retain |
| `scripts/docs/run_mkdocs_build.py` | compatibility shim | `scripts/docs/README.md`, `tests/architecture/test_docs_compat_shim_governance.py` | retain |
| `scripts/docs/build_docs_site.sh` | shell transport adapter | `scripts/docs/README.md` | retain |
| `scripts/diagrams/generate_architecture_bundle.py` | compatibility wrapper | `scripts/diagrams/README.md`, diagram workflow docs, architecture tests | retain |
| `scripts/diagrams/generate_views_bundle.py` | compatibility wrapper | `scripts/diagrams/README.md`, diagram workflow docs, architecture tests | retain |
| `scripts/engineering/dev/setup_copilot_codex_mcp.py` | Python compatibility facade | docs deployment notes, README, tests | retain |
| `scripts/engineering/dev/setup_copilot_codex_mcp.sh` | shell transport facade | dev README, architecture tests | retain |
| `scripts/engineering/dev/setup_copilot_codex_mcp.ps1` | PowerShell transport facade | dev README, architecture tests | retain |
| `scripts/ops/launchers/codex/codex.sh` | public launcher facade | extensive ops docs, batch launchers, helper docs | retain |
| `scripts/ops/launchers/codex/codex-exec.sh` | public launcher facade | ops docs and wrappers | retain |

## Notes

- The current safe wave is internal dispatch consolidation, not file deletion.
- `scripts/docs/check_doc_links.py` remains the highest-risk shim because tests
  rely on its historical monkeypatchable module surface.
- `scripts/ops/launchers/codex/*` remain public/tested compatibility surfaces
  and are not candidates for early deletion.
