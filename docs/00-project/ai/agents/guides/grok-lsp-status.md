# Grok LSP status (BioETL)

*Status: internal | Verified 2026-08-07*

## Project surface

- Config: `.grok/lsp.json`
- Expected server: `.venv-win/Scripts/basedpyright-langserver.exe`
- `python.analysis.extraPaths`: `src`

## Verification (2026-08-07)

| Check | Result |
|-------|--------|
| `.venv-win/Scripts/basedpyright-langserver.exe` | **present** (~108 KB) |
| `.venv-win/Scripts/python.exe` | **present** |
| `.grok/lsp.json` paths absolute to this checkout | **valid** |

If the binary disappears after venv recreate, reinstall basedpyright into
`.venv-win` or update `.grok/lsp.json` before relying on LSP tools.

Tracked under #8280 / epic #8274.
