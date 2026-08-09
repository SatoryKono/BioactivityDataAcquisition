# Grok Operator Runbook (BioETL)

*Status: internal-published | Operator SOP for Grok Build TUI on BioETL*

This runbook is **not** a runtime SSOT. Canonical AI precedence remains
`AGENTS.md` and `docs/00-project/NORMATIVE_SOURCES.md`.

## 1. Session shape

| Rule | Why |
|------|-----|
| 1 task = 1 branch | Avoid thrash and mixed commits |
| Prefer worktree when main is dirty | Protect foreign WIP |
| Never delete others' uncommitted work | Multi-agent safety |
| No `git reset --hard` / force-push | Irreversible loss |
| Push feature branches only | Protected `main` |
| `CYCLE_COUNT` default **1**, max **2**/session | Reduce compaction thrash |

## 2. Permission profiles (local `~/.grok/config.toml`)

### Safe (default)

```toml
[ui]
permission_mode = "ask"
remember_tool_approvals = true
default_selected_permission = "allow_once"
yolo = false
```

### Ship (optional, short-lived)

Use only for a single closeout session (issue comments/closes + PR ship) when
you intentionally accept higher autonomy:

```toml
[ui]
permission_mode = "always-approve"
yolo = false
```

Switch back to **safe** after the session. Never leave ship as the long-term default.

## 3. MCP slim profile (always-on target ≤8)

Recommended always-on:

- `github`
- `fetch`
- `brave-search` (or drop if using only built-in web_search)
- `context7`
- `ast-grep`
- `code-analyzer`
- `memory`

Enable on demand: `docker`, `grafana`, `prometheus`, `mutmut`, `github-actions`,
`deepwiki`, `ref` (after auth), `neo4j-memory`, etc.

Local config is machine-only — **do not commit** API keys or full `config.toml`.

## 4. Prompts

Prefer short templates:

- [grok-prompts-2-grok-closeout.md](../../prompts/grok-prompts-2-grok-closeout.md)
- [grok-prompts-1-grok-audit-cycle.md](../../prompts/grok-prompts-1-grok-audit-cycle.md)

Do not inline full RULES/ADR text into user prompts.

## 5. Models / session (recommended local)

```toml
[models]
default = "grok-4.5"
web_search = "grok-4.5"
temperature = 0.3

[session]
auto_compact_threshold_percent = 80

[tools]
respect_gitignore = true

[toolset.bash]
timeout_secs = 180.0
output_byte_limit = 30000
```

## 6. LSP (project)

`.grok/lsp.json` expects Windows venv:

` .venv-win/Scripts/basedpyright-langserver.exe `

Verify the binary exists before relying on LSP tools. If missing, bootstrap
`.venv-win` or disable LSP until healthy.

## 7. Closeout pattern

1. Confirm each issue against `origin/main` (code wins).
2. Fix or `VERIFIED_ALREADY_RESOLVED` with commands/SHA.
3. PR for product/docs deltas only.
4. Comment + close; leave blocked issues open.

## Related

- `AGENTS.md`
- [MEMORY_USAGE.md](MEMORY_USAGE.md)
- [AI_RUNTIME_MIRROR_OWNERSHIP.md](../policy/AI_RUNTIME_MIRROR_OWNERSHIP.md)
