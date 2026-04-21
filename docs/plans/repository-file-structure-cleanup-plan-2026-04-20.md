# Repository File Structure Cleanup Plan

*Status: active planning artifact (non-normative)*
*Created: 2026-04-20*
*Refreshed: 2026-04-21*
*Scope: audit and cleanup roadmap for repository layout, root-file policy, and generated artifact placement*

## Freshness note

This document is a repo-only planning surface. It must not override:

- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- accepted ADRs in `docs/02-architecture/decisions/`
- active governance docs in `docs/00-project/governance/`
- enforcement in `scripts/engineering/repo/audit_root_cleanliness.py`

The 2026-04-21 refresh supersedes the original 2026-04-20 assessment for live
state. The original cleanup wave appears to have closed the largest root
artifact problems: root markdown is now reduced to canonical entries, root-level
Python is absent, root cleanliness passes, and the previously identified
generated/runtime trees are no longer tracked.

## Executive summary

The repository now has a mostly clean top-level layout. The next cleanup wave
should focus on policy convergence and prevention rather than broad file moves.

Current baseline:

- `python3 scripts/engineering/repo/audit_root_cleanliness.py` passes.
- The root audit validates 32 root files and 16 root directories.
- Tracked root markdown is limited to `README.md`, `CHANGELOG.md`, and
  `GEMINI.md`.
- No tracked root-level `*.py` files are present.
- No tracked paths were found for the previously risky generated families:
  `src/tools/reports/`, `output/`, `test-output/`, `MagicMock/`,
  `.python-user/`, `node_modules/`, `logs/`, root coverage artifacts, or
  `contract-registry-diagnostics.json`.

Remaining work is governance work:

1. align root allowlist, README policy, cleanup docs, and audits;
1. decide which AI/editor config directories are intentional shared repo
   surfaces;
1. make generated artifact placement rules explicit for all generators;
1. add regression checks for the cleanup state already achieved.

## Evidence snapshot

Commands used for the 2026-04-21 refresh:

```bash
python3 scripts/engineering/repo/audit_root_cleanliness.py
git ls-files | rg '^[^/]+\.md$|^[^/]+\.py$'
git ls-files | rg '^(src/tools/reports/|output/|test-output/|MagicMock/|\.python-user/|node_modules/|logs/|.*sonar-scanner.*zip$|contract-registry-diagnostics\.json$|.*\.coverage|htmlcov/|coverage\.xml$)'
```

Observed results:

- root audit: `OK: root layout audit passed`;
- root markdown: `CHANGELOG.md`, `GEMINI.md`, `README.md`;
- root Python: none;
- tracked generated/runtime artifact pattern scan: no matches.

## Target repository layout contract

## Root

Allowed:

- canonical repository entrypoints: `README.md`, `CHANGELOG.md`, `LICENSE`;
- explicitly approved runtime instruction files such as `GEMINI.md`;
- build, package, CI, docs, and tool configuration files;
- top-level directories approved by root audit policy.

Forbidden in tracked root:

- generated diagnostics;
- coverage output;
- runtime logs;
- screenshots and render outputs;
- one-off recovery or completion notes;
- vendored dependency caches;
- temporary MCP/setup test trees;
- root-level Python helpers unless explicitly approved.

## `src/`

Allowed:

- maintained runtime source code;
- source-adjacent helper modules that are imported and tested as source.

Forbidden:

- generated merged documentation;
- generated reports and repo tree snapshots;
- diagnostics, logs, screenshots, or ad-hoc exports.

## `docs/`

Allowed:

- canonical active documentation under `docs/00-05/`;
- active planning under `docs/plans/`;
- curated repo-only evidence and bounded internal memos under `docs/reports/`;
- historical context under `docs/99-archive/`.

Routing:

- current instructions and runbooks -> `docs/00-05/`;
- active execution plans -> `docs/plans/`;
- curated evidence and bounded memos -> `docs/reports/`;
- historical or superseded notes -> `docs/99-archive/`.

## `reports/`

Allowed:

- generated working outputs;
- tool-heavy derived reports;
- timestamped diagnostics;
- model-specific or iteration-specific artifacts.

Forbidden:

- normative instructions;
- active operator runbooks;
- duplicate curated artifacts that should live under `docs/reports/`.

## `scripts/`

Allowed:

- maintained executable tooling;
- compatibility wrappers during bounded migration windows;
- adjacent README files for tool usage.

Forbidden:

- generated outputs;
- runtime artifacts;
- local logs.

## `configs/`

Allowed:

- runtime configuration;
- schema configuration;
- quality configuration;
- governance manifests.

Forbidden:

- generated diagnostics emitted by CI or local runs.

## `tests/`

Allowed:

- tests;
- intentionally versioned test fixtures;
- static expected outputs used as fixtures.

Forbidden:

- ad-hoc output trees from local test runs unless promoted to fixtures.

## Cleanup roadmap

## Wave 1: policy convergence

Goal: make every policy surface say the same thing.

Actions:

- Reconcile `README.md` root layout policy with
  `scripts/engineering/repo/audit_root_cleanliness.py`.
- Review `.github/root-allowlist.txt` and remove forward-compatible allowances
  that are no longer intended root files.
- Add a short note to `docs/plans/README.md` that this plan was refreshed on
  2026-04-21 and now tracks prevention work.
- Cross-check cleanup docs under `docs/03-guides/` for stale references to
  removed root status files or removed generated trees.

Acceptance:

- root allowlist contains only root files that are intentionally allowed;
- README, cleanup docs, and audit script describe compatible rules;
- no cleanup doc instructs users to write generated output into root or `src/`.

## Wave 2: generated artifact routing

Goal: ensure every generator writes to a known, policy-compliant destination.

Actions:

- Inventory scripts that write files under `reports/`, `docs/reports/`,
  `docs/reports/generated/`, `src/**/generated/`, or repository root.
- Classify each output as source artifact, generated source, working report,
  curated evidence, or local-only diagnostic.
- For each generated writer, document the intended output directory and whether
  the output is tracked, ignored, or CI-only.
- Add or update tests for generators that previously wrote to risky locations.

Acceptance:

- no maintained generator defaults to repository root for diagnostics;
- generated source remains under explicit `generated/` packages with
  deterministic regeneration commands;
- working reports route to `reports/`;
- curated outputs route to `docs/reports/` only after curation.

## Wave 3: AI and editor surface decision

Goal: distinguish shared repo tooling from local machine state.

Actions:

- Decide whether `.codex/`, `.gemini/`, `.claude/`, `.vibe/`, `.cursor/`,
  `.vscode/`, and `.idea/` are shared project surfaces, local-only surfaces, or
  mixed.
- For shared surfaces, document ownership and allowed file types.
- For local-only surfaces, untrack or ignore machine-specific files.
- Keep MCP/generated config paths aligned with the setup scripts.

Acceptance:

- every tracked AI/editor directory has an explicit reason to be tracked;
- local machine state is ignored;
- setup scripts regenerate local config without modifying unrelated files.

## Wave 4: enforcement hardening

Goal: keep the cleaned structure from regressing.

Actions:

- Extend root hygiene checks to flag tracked generated artifact families.
- Add architecture tests for root markdown and root Python policy.
- Add a guard for generated report placement under `src/`.
- Keep `.gitignore`, `.dockerignore`, and root audit rules in sync for
  coverage, logs, temporary outputs, and generated reports.

Acceptance:

- CI fails if non-canonical root markdown or root Python appears;
- CI fails if generated working reports are committed under `src/`;
- ignored generated artifacts are not copied into Docker build contexts;
- local sharded coverage output stays local unless explicitly exported by CI.

## Current open questions

- Should `.idea/` and `.vscode/` remain tracked as shared workspace config, or
  should they be reduced to documented examples plus local ignored state?
- Should `.codex/` and `.gemini/` be treated as first-class shared AI tooling
  surfaces, or regenerated local config?
- Should `docs/reports/generated/` remain a tracked generated-docs surface, or
  should it be split into tracked curated generated outputs and ignored local
  generated outputs?
- Should `.github/root-allowlist.txt` keep absent forward-compatible entries,
  or should it only list files that are expected in the current tree?

## Definition of done

- root tracked files are limited to canonical entrypoints and intentional
  project configuration;
- root tracked markdown stays limited to approved entrypoints;
- no root-level Python helper files are introduced without explicit policy
  approval;
- generated/runtime/local artifact trees stay untracked;
- generators have documented output destinations;
- `src/` contains runtime source or intentionally generated source, not working
  reports;
- `docs/plans/`, `docs/reports/`, `docs/99-archive/`, and `reports/` have
  non-overlapping roles in both documentation and practice;
- root cleanliness and structural tests enforce the same rules described in the
  published file policy.
