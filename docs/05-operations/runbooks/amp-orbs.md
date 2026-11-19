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

## Surface inventory (Amp project settings — source of truth is the UI)

| Setting | Value | Where |
| --- | --- | --- |
| Default orb size | `a1.large` (8 CPU / 16 GB, 60 GB disk) | Project Settings → Orb |
| Ship Behavior | Custom Ship (canonical text below) | Settings → Overview |
| MCP servers | memory, fetch, github (from `.amp/settings.json`) | Repo file + owner approval in orb |
| Skills path | `.codex/skills` (`amp.skills.path`) | `.amp/settings.json` |
| Secrets level | Project (never personal for setup) | Project → Secrets & Env Vars |
| GitHub integration | Connected, thread subscribed to CI/PR comments | Settings → Integrations & MCP |

The settings above live on ampcode.com and are NOT version-controlled;
this runbook is the canonical record. Any drift between the UI and this
table is a defect: fix the UI to match, or update this runbook and
`AGENTS.md` in the same PR that changes the decision.

## Lifecycle

### `.agents/setup` (snapshot build, 20-minute platform budget)

- `uv sync` (Python 3.13 from `.python-version`), then `npm ci`.
- No `git fetch --unshallow`: orbs clone the full branch history by
  default, which `check_no_partial_tree.py` requires.
- No `gh` commands: GitHub is not authenticated while setup runs.
- No Docker/Redis/monitoring startup (ADR-010, local-only deployment;
  the Docker daemon in an orb stays stopped).
- If setup risks the 20-minute budget, add a remote build cache (token in
  project secrets) instead of trimming dependencies.

### `.agents/resume` (after activation and each wake, ~10-second budget)

- Authentication and light repair only. Never install dependencies here;
  dependency changes go to `.agents/setup` and publish a new snapshot.
- Current content: verify `gh auth status`, warn on stderr, never block.

### Snapshot freshness

A setup snapshot stays valid while `uv.lock` / `package-lock.json` are
unchanged. After either changes, the next orb rebuilds the snapshot;
watch the first orb after such a merge for setup timeouts.

## Custom Ship — canonical prompt

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

## Secrets

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

## Known limits

- Orb outbound IP addresses change; APIs with IP allowlists may reject
  orb requests. Record such rejections here instead of retrying blindly.
- MCP servers from `.amp/settings.json` require explicit approval in the
  orb (Always Allow is set by the owner once per server).
- Skill name collisions resolve by Amp's documented search order; a
  `.codex/skills` skill that silently loses to a built-in Amp skill is a
  passport defect, not a reason to copy skills into an Amp tree.

## Trial run and passport

Acceptance evidence lives in issue #13216 as a passport table
(file-present / configured / loaded / executed, separately). Unverified
states are UNKNOWN; a failed or skipped check never counts as PASS.

## Rollback

1. Repository (one PR): remove the `AGENTS.md` / `.junie/guidelines.md`
   Amp sections, `.amp/settings.json`, `.agents/setup`, `.agents/resume`,
   the `.amp` entries in `repo_structure_catalog.yaml` and
   `03-file-policy.md`, the `.gitignore` negations, and this runbook;
   refresh `documentation-cleanup-inventory` per post-change validation.
2. Amp side: delete the project secrets, disconnect the GitHub
   integration, and delete or archive the project.
