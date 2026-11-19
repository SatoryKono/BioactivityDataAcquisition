______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-11-19'

______________________________________________________________________

# Amp orbs: lifecycle, settings, and rollback

## Trigger

Use when onboarding or changing the Amp surface, after an Amp platform
change, or when an orb misbehaves (setup timeout, missing tools, wrong
Ship behavior). Tracking issue: #13216. The contract section is
`AGENTS.md` § Amp Orb Agent (Phase 1, subordinate surface).

## Impact

The hooks prepare dependency snapshots and check GitHub CLI authentication
when an orb starts or wakes. Custom Ship can create a feature branch PR
after the local test gate. The project settings and the trial passport
are maintained separately from this Git checkout.

## Preconditions

Use the GitHub-backed Amp project for this repository. Confirm the base
branch, full history, orb size and Custom Ship settings. Obtain the
project owner's approval for the secret names and the workspace MCP servers.

## Procedure

### Amp project settings

| Setting | Value | Where |
| --- | --- | --- |
| Default orb size | `a1.large` (8 CPU / 16 GB, 60 GB disk) | Project Settings → Orb |
| Ship Behavior | Custom Ship (canonical text below) | Settings → Overview |
| MCP servers | memory, github (from `.amp/settings.json`); fetch excluded — its wrapper requires the registered Windows host (see Known limits) | Repo file + owner approval in orb |
| Skills path | `.codex/skills` (`amp.skills.path`) | `.amp/settings.json` |
| Secrets level | Project (never personal for setup) | Project → Secrets & Env Vars |
| GitHub integration | Connected, thread subscribed to CI/PR comments | Settings → Integrations & MCP |

The settings above live on ampcode.com and are NOT version-controlled;
this runbook is the canonical record. Any drift between the UI and this
table is a defect: fix the UI to match, or update this runbook and
`AGENTS.md` in the same PR that changes the decision.

### Lifecycle

#### `.agents/setup` (snapshot build, 20-minute platform budget)

- `uv sync --locked` (Python 3.13 from `.python-version`), then `npm ci`.
- Keep Shallow Clone disabled in the Amp project. Amp clones the full
  history by default, as required by `check_no_partial_tree.py`.
- Installs the pinned official `github-mcp-server` binary (v2.2.0,
  checksum-verified) into `$HOME/tools/bin` — a candidate path of
  `github-mcp-wrapper.sh`; without it the GitHub MCP cannot start in a
  fresh orb. Read-only mode needs no digest approval.
- No `gh` commands: GitHub is not authenticated while setup runs.
- No Docker/Redis/monitoring startup (ADR-010, local-only deployment;
  the Docker daemon in an orb stays stopped).
- If setup risks the 20-minute budget, add a remote build cache (token in
  project secrets) instead of trimming dependencies.

#### `.agents/resume` (after activation and each wake, ~10-second budget)

- Authentication and light repair only. Never install dependencies here;
  dependency changes go to `.agents/setup` and publish a new snapshot.
- Current content: verify `gh auth status`, warn on stderr, never block.

#### Snapshot freshness

Amp refreshes the project snapshot when the base branch moves or the
shared project configuration changes. The refresh may start in the
background or when a new orb starts. Check setup logs after changes
to the hook or dependency locks.

See [The Orb Lifecycle](https://ampcode.com/docs/orbs/customizing#the-orb-lifecycle).

### Custom Ship — canonical prompt

```text
Ship procedure for SatoryKono/BioactivityDataAcquisition:
1. Run `make test-fast`. If it fails, stop and report the failure; do not ship.
2. Commit all changes with a conventional-commit message.
3. Push the current feature branch (never push to main directly).
4. Open a pull request with `gh pr create --fill`. Write the PR title and
   description in Russian.
5. Do not merge the pull request. Do not enable auto-merge.
6. Subscribe this thread to the PR's CI runs and review comments, and
   report the PR URL.
```

The default Ship behavior (push to the base branch) is forbidden for this
repository. If Ship Behavior is ever found reset to default, stop all orb
write work until Custom Ship is restored.

### Secrets

Project-level secrets hold the wide key set from the `.env` inventory
(names only here; values live only in Amp settings and the owner's local
`.env`): `GITHUB_TOKEN`, `GITHUB_PERSONAL_ACCESS_TOKEN`,
`GITHUB_CDX_PERSONAL_ACCESS_TOKEN`, `OPENAI_API_KEY`, `GROK_API_TOKEN`,
`DEEPWIKI_API_KEY`, `DEEPWIKI_ORGANISATION_ID`, `CONTEXT7_API_KEY`,
`NEEDLE_API_KEY`, `BRAVE_API_KEY`, `QODO_API_KEY`, `SONARQUBE_TOKEN`,
`DOCKER_API_KEY`, `DOCKER_USERNAME`, `HUB_PAT_TOKEN`.

- Rotation: replace the value in Amp project settings, then restart orb
  processes (`amp orb restart-processes`) or start a fresh orb; running
  orbs keep stale values otherwise.
- Revocation: delete the secret in Amp settings AND rotate it at the
  issuer — deletion alone does not invalidate a leaked value.
- Setup receives workspace + project values only, never personal ones;
  do not move a key to the personal level to "fix" a setup failure.

### Known limits

- Orb outbound IP addresses change; APIs with IP allowlists may reject
  orb requests. Record such rejections here instead of retrying blindly.
- MCP servers from `.amp/settings.json` require explicit approval in the
  orb (Always Allow is set by the owner once per server).
- The registered Fetch wrapper requires a Windows owner. Fetch on an
  Amp-hosted Linux orb needs an approved Linux transport before it can
  be counted as executed.
- The repository memory wrapper exits in `off` and `read-only` modes.
  Persistent memory requires separate, explicit `read-write` authority.
- GitHub MCP needs the official `github-mcp-server` executable or a
  qualified repository transport. `gh auth status` only checks CLI
  authentication. Verify GitHub MCP separately in the passport.
- Skill name collisions resolve by Amp's documented search order; a
  `.codex/skills` skill that silently loses to a built-in Amp skill is a
  passport defect, not a reason to copy skills into an Amp tree.

## Verification

Acceptance evidence lives in issue #13216 as a passport table
(file-present / configured / loaded / executed, separately). Unverified
states are UNKNOWN; a failed or skipped check never counts as PASS.

## Rollback

1. Repository (one PR): remove the `AGENTS.md` / `.junie/guidelines.md`
   Amp sections, `.amp/settings.json`, `.agents/setup`, `.agents/resume`,
   the `.amp` entries in `repo_structure_catalog.yaml`,
   `root_hygiene_review_registry.yaml` and `03-file-policy.md`, the `.gitignore` negations, and this runbook;
   refresh `documentation-cleanup-inventory` per post-change validation.
2. Amp side: delete the project secrets, disconnect the GitHub
   integration, and delete or archive the project.


## Post-incident

Record the source commit, Amp version, orb size, and setup and resume log
outcomes in #13216. After correcting a failure, repeat the affected passport
check and distinguish the result from the GitHub PR checks.

## Compliance

Apply the root BioETL guardrails in the orb. Preserve full-tree commits and
the required GitHub checks. Keep credential values out of Git and logs.
Record the explicit workspace MCP approvals and leave merge to the
authorized GitHub process outside Amp.
