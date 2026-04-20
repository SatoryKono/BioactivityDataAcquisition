# Repository File Structure Cleanup Plan

*Status: working planning artifact (non-normative)*
*Created: 2026-04-20*
*Scope: audit and cleanup roadmap for repository layout, root-file policy, and generated artifact placement*

## Freshness note

This document is a repo-only planning and assessment surface. It must not
override:

- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- accepted ADRs in `docs/02-architecture/decisions/`
- active governance docs in `docs/00-project/governance/`

If repository structure policy or automation changes after this date, those
active sources win and this plan should be refreshed rather than silently
treated as current truth.

## Executive summary

The repository still has a strong macro-layout: `src/`, `configs/`, `tests/`,
`docs/`, `scripts/`, and `reports/` are meaningful top-level zones and this is
consistent with the repository overview in `README.md`.

The current problem is not the absence of structure. The problem is structural
drift in file-placement enforcement:

1. policy documents, root allowlists, and structural audit scripts disagree;
1. generated/runtime/local artifacts are committed in tracked root trees;
1. one-off operational and status markdown files still live in the root;
1. generated report families are duplicated across `src/tools/reports/` and
   `reports/`.

The next cleanup wave should not be a repo-wide reorganization. It should be a
bounded hygiene and policy-convergence pass.

## Brief assessment

### What is healthy

- The top-level repository zones are understandable and mostly stable.
- `README.md` already documents an intended structure for `src/`, `configs/`,
  `tests/`, `docs/`, `docs/reports/`, `reports/`, and `scripts/`.
- The project already has explicit cleanup and file-policy documents, so the
  repository does not need a new governance model from scratch.

### What is unhealthy

- The published file policy, the root allowlist, and structural enforcement do
  not currently align.
- Several tracked root directories contain generated, runtime, test, or local
  artifacts that should not live in git.
- Root markdown contains a mix of canonical entrypoints and one-off status
  documents.
- Generated merged documentation/report outputs are stored inside `src/`, which
  mixes source code with derived artifacts.

## Sources used for this plan

- `README.md`
- `docs/00-project/governance/03-file-policy.md`
- `docs/03-guides/cleanup-policy.md`
- `docs/03-guides/cleanup.md`
- `.github/root-allowlist.txt`
- `scripts/engineering/repo/audit_root_cleanliness.py`
- `scripts/engineering/diagnostics/audit_structure.py`
- `scripts/ops/support/repo/cleanup_repository.py`
- `src/tools/README.md`
- `src/tools/file_merger.py`
- `reports/README.md`
- `docs/reports/index.md`
- `docs/reports/evidence/project-package-topology/SUMMARY.md`
- `docs/reports/evidence/governance-signals/SUMMARY.md`

## Prioritized problems

### Critical

1. **Policy drift across enforcement surfaces**
   `docs/00-project/governance/03-file-policy.md` says root tracked markdown
   should be limited to canonical entrypoints and that operational quick refs
   should live under `docs/05-operations/`, but `.github/root-allowlist.txt`
   still explicitly allows multiple one-off status files in the root.

2. **Tracked generated/runtime/local root trees**
   The repository currently tracks artifact-like trees such as `node_modules/`,
   `output/`, `test-output/`, `MagicMock/`, `.python-user/`, and temporary MCP
   test directories. This directly conflicts with cleanup guidance and with the
   intended role of `reports/` as the working output surface.

3. **Generated reports committed under `src/`**
   `src/tools/reports/*.md` contains generated merged views and project tree
   snapshots. Those artifacts are not runtime source and already have an output
   home in `reports/`.

### Medium

1. **Root markdown contains status/recovery summaries**
   Files such as `AI_TOOLS_COMPLETE.md`, `SYNC_COMPLETE.md`, and test-fix
   summaries are not canonical root entrypoints.

2. **IDE/editor tracking policy is inconsistent**
   Published policy says local tooling dirs like `.idea/`, `.vscode/`,
   `.cursor/` should remain untracked, but the working tree currently tracks
   `.idea/`, `.vscode/`, and `.cursor/`.

3. **Root diagnostics and vendored binaries**
   `contract-registry-diagnostics.json` and
   `sonar-scanner-cli-5.0.1.3006-linux.zip` do not belong to the canonical root
   surface.

### Cosmetic

1. The root allowlist is serving as an accumulation bucket rather than a strict
   policy surface.
2. `docs/reports/`, `reports/`, and `src/tools/reports/` create unnecessary
   cognitive overhead for report placement.
3. Root structure expectations are documented in several places, but they are
   not expressed as one synchronized, authoritative contract.

## Safety classification

### Safe recommendations

- Untrack generated/runtime/local artifact trees from git.
- Remove `src/tools/reports/` as a committed generated-artifact surface.
- Archive one-off root status markdown into `docs/99-archive/`.
- Keep root free of `*.py` files unless a future exception is explicitly
  approved.

### Conditionally safe recommendations

- Move `QUICK_START.md` and `NEO4J-MCP-SETUP.md` after deciding whether they are
  still active operational guidance or only historical context.
- Relocate CI diagnostics such as `contract-registry-diagnostics.json` to
  `reports/quality/` or a CI-only artifact path after workflow updates.
- Remove the vendored Sonar scanner zip after replacing it with an explicit
  bootstrap/download step.

### Risky recommendations

- Removing `.codex/`, `.gemini/`, `.claude/`, or `.vibe/` from version control
  without first deciding whether they are intentional shared AI-tooling
  surfaces.
- Removing `.vscode/` or `.cursor/` without first deciding whether the team
  wants shared workspace config and shared editor rules in-repo.

## Root `md` and `py` audit

## Root `py`

No root-level `*.py` files were found during the audit.

Interpretation:

- current state is acceptable;
- no transfers are needed;
- future root-level python files should be treated as policy exceptions and
  should normally move to `scripts/`, `src/`, or `tests/`.

## Root `md`

### Leave in root

- `README.md`
- `CHANGELOG.md`
- `GEMINI.md`

Reason:

- these are canonical repository entrypoints or standard top-level project
  metadata surfaces;
- `GEMINI.md` is already recognized in naming exceptions as a runtime doc
  surface.

### Move to `docs/99-archive/`

- `AI_TOOLS_COMPLETE.md`
- `GEMINI_UPDATED.md`
- `SYNC_COMPLETE.md`
- `TEST_FIXES_SUMMARY.md`
- `TEST_FIXES_PHASE2_SUMMARY.md`
- `TOOLS_COMPARISON.md`

Reason:

- they are wave summaries, completion notes, or one-off comparison/status
  artifacts;
- they are not canonical repository root entrypoints;
- the active file policy already says such materials should be archived rather
  than kept in root.

### Move to `docs/05-operations/`

- `QUICK_START.md`

Suggested target:

- `docs/05-operations/tooling/scripts-ops/neo4j-backend-recovery-quick-start.md`
  or an equivalent Neo4j/MCP recovery page in the operations tree.

Reason:

- it is operational recovery guidance, not repository entrypoint metadata;
- `docs/05-operations/tooling/scripts-ops/` already exists as the canonical
  home for script/tooling quick-start material.

### Requires review before move

- `NEO4J-MCP-SETUP.md`

Decision rule:

- if it still reflects current supported setup, promote and normalize it into
  `docs/05-operations/`;
- if it is only a point-in-time recovery note, archive it to `docs/99-archive/`.

## Files and directories by action

### Remove from git or untrack

- `node_modules/`
- `output/`
- `test-output/`
- `MagicMock/`
- `.python-user/`
- `.tmp-codex-mcp-test-camel/`
- `.tmp-codex-mcp-test-snake/`
- `logs/bioetl.log`
- `src/tools/reports/`

### Move

- `AI_TOOLS_COMPLETE.md` -> `docs/99-archive/`
- `GEMINI_UPDATED.md` -> `docs/99-archive/`
- `SYNC_COMPLETE.md` -> `docs/99-archive/`
- `TEST_FIXES_SUMMARY.md` -> `docs/99-archive/`
- `TEST_FIXES_PHASE2_SUMMARY.md` -> `docs/99-archive/`
- `TOOLS_COMPARISON.md` -> `docs/99-archive/`
- `QUICK_START.md` -> `docs/05-operations/...`
- `NEO4J-MCP-SETUP.md` -> `docs/05-operations/...` or `docs/99-archive/`

### Keep as-is

- `README.md`
- `CHANGELOG.md`
- `GEMINI.md`
- root project/build/config files such as `pyproject.toml`, `mkdocs.yml`,
  `pytest.ini`, `Makefile`, `docker-compose*.yml`, `package.json`,
  `package-lock.json`, `uv.lock`, `.env.example`, `.gitignore`, `.mcp.json`,
  `sonar-project.properties`

### Reclassify or regroup

- `.idea/` -> likely untrack entirely
- `.vscode/` -> either formal shared workspace config or untracked local state
- `.cursor/` -> either formal shared editor rules or untracked local state
- `.claude/`, `.codex/`, `.gemini/`, `.vibe/` -> keep only if the repository
  intentionally version-controls these as shared AI tooling surfaces
- `contract-registry-diagnostics.json` -> move output path to `reports/quality/`
  or CI artifact temp space
- `sonar-scanner-cli-5.0.1.3006-linux.zip` -> remove after introducing download
  bootstrap

## Proposed target repository file policy

## Root

Allowed:

- canonical repository entrypoints and standard metadata:
  `README.md`, `CHANGELOG.md`, `LICENSE`, runtime instruction files approved by
  policy, and build/config entrypoints;
- project config files used by tooling, packaging, CI, docs, and local bootstrap.

Forbidden in tracked root:

- generated diagnostics;
- screenshots and render outputs;
- runtime logs;
- temporary MCP or setup test trees;
- one-off recovery or completion notes;
- vendored dependency caches;
- root-level test data dumps;
- root-level python helper scripts not explicitly approved.

## `src/`

Allowed:

- runtime source code;
- source-adjacent helper modules that are part of maintained tooling.

Forbidden:

- generated merged documentation;
- generated reports and repo tree snapshots;
- screenshots, diagnostics, logs, ad-hoc exports.

## `docs/`

Allowed:

- canonical active documentation under `docs/00-05/`;
- curated repo-only evidence and bounded internal memos under `docs/reports/`;
- historical context only under `docs/99-archive/`.

Routing:

- active runbooks and quick refs -> `docs/05-operations/`
- current canonical guidance -> `docs/00-05/`
- historical status artifacts -> `docs/99-archive/`

## `scripts/`

Allowed:

- maintained executable tooling;
- compatibility wrappers during bounded migration windows;
- small adjacent README surfaces for tool usage.

Forbidden:

- generated outputs and runtime artifacts.

## `configs/`

Allowed:

- runtime configs, schema configs, quality configs, governance manifests.

Forbidden:

- diagnostics generated during CI/runtime.

## `tests/`

Allowed:

- tests and committed test fixtures.

Forbidden:

- ad-hoc output trees from local test runs unless they are intentionally versioned
  fixtures.

## `reports/`

Allowed:

- generated working outputs, tool-heavy derived reports, iteration-specific
  diagnostics, timestamps, and model-specific working artifacts.

Forbidden:

- canonical instructions and active runbooks;
- duplicate copies of curated `docs/reports/` artifacts when not needed.

## Temporary and local surfaces

These should remain untracked and ignored:

- `.venv*`
- `.cache*`
- `node_modules/`
- `output/`
- `logs/`
- `tmp/`
- local editor state unless explicitly approved

## Step-by-step cleanup plan

1. **Converge policy surfaces**
   Update `03-file-policy.md`, `.github/root-allowlist.txt`,
   `audit_root_cleanliness.py`, and `audit_structure.py` so they describe the
   same allowed root files and root directories.

2. **Clean generated root artifacts**
   Remove tracked generated/runtime/local trees from git and ensure `.gitignore`
   keeps them out.

3. **Normalize runtime log handling**
   Keep `logs/` as a runtime path if needed, but do not track `logs/bioetl.log`.
   If a committed path is needed, use `.gitkeep`.

4. **Archive root status markdown**
   Move one-off completion/recovery/test-fix docs out of root.

5. **Resolve Neo4j operational docs**
   Decide whether `QUICK_START.md` and `NEO4J-MCP-SETUP.md` are active
   runbooks or historical notes, then move accordingly.

6. **Eliminate generated reports from `src/`**
   Keep `reports/` as the only working-output surface for file-merger outputs.
   Update references and manifests that still point to `src/tools/reports/`.

7. **Relocate diagnostics**
   Stop writing `contract-registry-diagnostics.json` to the repo root. Route it
   to `reports/quality/` or CI artifact staging.

8. **Remove vendored binary payloads**
   Replace the root Sonar zip with an explicit bootstrap/download step, then
   remove it from the index.

9. **Review tracked editor/tooling surfaces**
   Separate shared project tooling from local editor state. Keep only the former
   in git.

10. **Tighten enforcement**
    Make root and structure audits fail on reintroduction of generated tracked
    trees and non-canonical root markdown.

## Suggested implementation order

### Wave 1: low-risk hygiene

- untrack `logs/bioetl.log`
- untrack temporary MCP test dirs
- archive root status markdown
- move `QUICK_START.md`

### Wave 2: generated artifact cleanup

- untrack `output/`, `test-output/`, `MagicMock/`, `.python-user/`,
  `node_modules/`
- remove `src/tools/reports/` committed outputs

### Wave 3: policy convergence

- update governance docs and audits
- shrink root allowlist to canonical surfaces only
- update cleanup automation and preflight checks

### Wave 4: ambiguous tooling surfaces

- decide fate of `.idea/`, `.vscode/`, `.cursor/`
- decide whether `.claude/`, `.codex/`, `.gemini/`, and `.vibe/` remain
  intentional shared repo tooling

## Definition of done

- root tracked files are limited to canonical entrypoints and project config;
- no generated/runtime/local artifact trees remain tracked at the root;
- `src/` no longer contains committed generated report families;
- root markdown contains only approved canonical files;
- `docs/05-operations/`, `docs/99-archive/`, `docs/reports/`, and `reports/`
  have non-overlapping roles in practice, not only in documentation;
- root cleanliness and structural audits enforce the same rules described in the
  published file policy.
