---
id: prompt.fragment.gh-powershell
version: 1.0.0
status: active
class: fragment
owner: BioETL Team
summary: Deterministic gh usage from Windows PowerShell (body-file, jq, upstream ref)
---

## gh from PowerShell

Do not use GitHub MCP solely to replace `gh pr view --json`. Prefer `gh` CLI
with these contracts (#10300):

- Issue/PR body: `--body-file path` or `--body-file -`. Never `--body @...`
  (`@` is a file prefix). Never `gh issue comment --body @"..."@` here-strings
  (empty or truncated body).
- `--jq '...'` in **single** quotes, or parse JSON with
  `.\.venv-win\Scripts\python.exe`. Unquoted `{` / `|` are PowerShell scriptblocks.
- Upstream ref: `git rev-parse --abbrev-ref '@{u}'` (quoted). Bare `@{u}` is a
  hash literal.
- `gh pr checks` non-zero while the parent run is `IN_PROGRESS` is **not** a
  failed suite. Use `docs/00-project/ai/skills/local/gh-fix-ci/scripts/inspect_pr_checks.py`
  (pending-aware). Do not treat pending as fail.
- Before `gh`, prefer no process `GITHUB_TOKEN` / `GH_TOKEN` so `hosts.yml`
  OAuth wins (#10298). Do not print token values.
