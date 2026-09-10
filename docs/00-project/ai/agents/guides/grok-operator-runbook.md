# Grok Operator Runbook (BioETL)

*Status: internal-published | Operator SOP for Grok Build TUI on BioETL*

This runbook is **not** a runtime SSOT. Canonical AI precedence remains
`AGENTS.md` and `docs/00-project/NORMATIVE_SOURCES.md`.

## 1. Session shape

| Rule | Why |
|------|-----|
| 1 task = 1 branch | Avoid thrash and mixed commits |
| 1 agent = 1 worktree | Parallel cherry-pick/merge in a shared checkout corrupts generated YAML |
| Prefer `git worktree add` | Protect foreign WIP; do not `git checkout` another agent's branch |
| Never delete others' uncommitted work | Multi-agent safety |
| No `git reset --hard` / force-push | Irreversible loss |
| Push feature branches only | Protected `main` |
| `CYCLE_COUNT` default **1**, max **2**/session | Reduce compaction thrash |

If `MERGE_HEAD` or `CHERRY_PICK_HEAD` exists and this session did not start it:
`git merge --abort` or `git cherry-pick --abort`. Do not resolve a foreign
operation "while here".

Fetch `origin/main` with `git fetch origin main`. Do **not** copy the CI
refspec `git fetch --no-tags --depth=1 origin main:refs/remotes/origin/main`
into a local worktree: it can delete `origin/main` and fail
`report-architecture-debt-remote-main-baseline` (`local_tracking_ref_matches_remote`).
See [generated-artifact-drift-workflow.md](../../../../05-operations/runbooks/generated-artifact-drift-workflow.md).

Child Grok agents must not run `gh` or create issues/PR (parent-only GitHub).
`CYCLE_COUNT` stays 1–2; do not raise it to compensate for generated-artifact
loops.

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

## 3. MCP slim profile (always-on target ≤4 live)

Wave `SUBAGENT-20260910` (#10313 / #10314). Daily **parent** connected MCP:

- `github` (required; **only** the parent may write GitHub / run `gh`)
- `ast-grep`
- `code-analyzer`
- `context7` (disable if handshake FAIL)

Optional if actually live: `memory` (MCP file), `fetch`.

**Off** on daily parent: `grafana`, `prometheus`, `google_drive`, `tasks`,
`neo4j-*`, `deepwiki`, `brave-search`, `filesystem`, `docker`, `github-actions`.
`grafana`/`prometheus` stay off here even after Grok-only `obs-dashboard`
(#10319) — that agent named-inherits them.

Parent skills KEEP (≤7): `bioetl-session`, `bioetl-closeout`,
`bioetl-post-change`, `long-running-background-tasks`, `pr-babysit`, `review`,
`gh-address-comments`. Disable the non-BioETL catalog (`pc-agent-session`,
deploy/office/imagegen/`resume-*`, …) via `[skills] disabled`.

Child Grok agents (`docs/00-project/ai/grok/agents/`): `mcpInheritance.named`
**without** `github`; no `gh` / `hub` / `api.github.com`. Install:

```powershell
.\scripts\ai\grok\install_skills.ps1
```

Local config is machine-only — **do not commit** API keys or full `config.toml`.

## 4. Prompts

Prefer short library cards (render, do not hand-expand RULES/ADR):

| Id | Card | When |
| --- | --- | --- |
| `prompt.session.grok-bootstrap` | [library/session/bootstrap.md](../../prompts/library/session/bootstrap.md) | Daily work start |
| `prompt.audit.cycle` | [library/audit/cycle.md](../../prompts/library/audit/cycle.md) | One audit cycle |
| `prompt.closeout.grok` | [library/closeout/grok-closeout.md](../../prompts/library/closeout/grok-closeout.md) | Issue/PR closeout |

```powershell
.\.venv-win\Scripts\python.exe -m scripts.ai.prompts render prompt.session.grok-bootstrap `
  --param TASK="..." --param MODE=implement --param SCOPE="src/bioetl/domain"
.\.venv-win\Scripts\python.exe -m scripts.ai.prompts render prompt.audit.cycle `
  --param SCOPE="src/bioetl/domain" --param DOMAIN=docs
.\.venv-win\Scripts\python.exe -m scripts.ai.prompts render prompt.closeout.grok `
  --param SCOPE="issues: #NNNN"
```

Redirect stubs remain as deprecated cards: `prompt.audit.grok-cycle` → `prompt.audit.cycle`.

### Project skills (machine-local)

Tracked sources live under `docs/00-project/ai/grok/skills/` (repo root `.grok/`
is gitignored). Install into `~/.grok/skills/` or project `.grok/skills/`:

```powershell
.\scripts\ai\grok\install_skills.ps1          # user: ~/.grok/skills
.\scripts\ai\grok\install_skills.ps1 -Project # project: .grok/skills
```

Skills: `bioetl-session`, `bioetl-closeout`, `bioetl-post-change`.

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

## 8. Optional agent diagnostics

When a bounded agent trajectory or tool-routing failure exists, Grok may use
the repository adapter rather than calling AgentDebugX or ProofAgent directly:

```bash
python -m scripts.ai.agent_tools doctor
python -m scripts.ai.agent_tools debug --task-id <id> \
  --trajectory reports/ai/agent-tools/inputs/<trajectory>.json
python -m scripts.ai.agent_tools evaluate --task-id <id> \
  --events reports/ai/agent-tools/inputs/<events>.jsonl
```

The adapter enforces deterministic/no-upload execution and writes only to its
report subtree. Vendor results are advisory: confirm them with BioETL-native
tests and never use them alone to advance lifecycle state or close an issue.

## Related

- `AGENTS.md`
- [MEMORY_USAGE.md](MEMORY_USAGE.md)
- [AI_RUNTIME_MIRROR_OWNERSHIP.md](../policy/AI_RUNTIME_MIRROR_OWNERSHIP.md)
