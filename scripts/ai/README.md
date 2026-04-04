# scripts/ai — Internal Agent Launchers

Internal convenience launchers for the Gemini-based helper personas retained in
the repository for operator compatibility.

Policy:

- These scripts are internal support entrypoints, not canonical contributor
  workflow commands.
- They may be invoked directly or through local shell aliases/wrappers outside
  the repository.
- Changes should preserve the current direct-execution contract unless a
  documented replacement path exists.
- They are intentionally kept out of the grouped `python -m scripts.<group>`
  command surface.

Scripts:

- `scripts/ai/code-reviewer.sh`
- `scripts/ai/data-engineer.sh`
- `scripts/ai/literature-researcher.sh`

For standard project automation, prefer the canonical grouped helpers under
`scripts/dev`, `scripts/qa`, `scripts/schema`, `scripts/docs`, and `scripts/repo`.
