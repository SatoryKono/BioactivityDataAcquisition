# scripts/repo — Repository Governance

Repository hygiene and inventory governance tooling.

## Unified Entry Point

```bash
python -m scripts.engineering.repo --help
python -m scripts.engineering.repo <command> [args...]
python -m scripts.engineering.repo cleanup-branch-candidates --help
```

## Commands

| Command                 | Script                           | Description                                                           |
| ----------------------- | -------------------------------- | --------------------------------------------------------------------- |
| `check-inventory`       | `check_scripts_inventory.py`     | Check scripts inventory drift against manifest                        |
| `sync-wrapper-caller-matrix` | `generate_scripts_wrapper_caller_matrix.py` | Refresh the tracked wrapper caller matrix used for RF-008 cleanup evidence |
| `check-catalog`         | `check_scripts_catalog.py`       | Validate catalog governance policy                                    |
| `check-versions`        | `check_version_consistency.py`   | Check version consistency across project files                        |
| `check-cleanliness`     | `audit_root_cleanliness.py`      | Audit repository root layout allowlist                                |
| `check-cleanup-governance` | `check_cleanup_governance.py` | Block unsafe broad cleanup guidance outside allowlisted examples       |
| `check-root-review-registry` | `check_root_hygiene_review_registry.py` | Validate review-required and blocked cleanup lanes              |
| `check-gh-actions-pins` | `check_github_action_pins.py` | Enforce pinned SHA + version comment policy in GitHub Actions files |
| `preflight-cleanup`     | `preflight_cleanup.sh`           | Preview/apply the bounded release-preflight cleanup set               |
| `split-testing-roadmap` | `split_testing_roadmap_issue.py` | Preview or create child issues for testing roadmap issue `#2511`      |
| `sync-docs-issues`      | `sync_docs_issues.py`            | Preview or apply labels, milestone, and comments for docs-sync issues |
| `all`                   | *(all above)*                    | Run all checks sequentially                                           |

## Shell Wrapper

```bash
python -m scripts.engineering.repo split-testing-roadmap --help
python -m scripts.engineering.repo sync-docs-issues --help
python -m scripts.engineering.repo cleanup-branch-candidates --help

bash scripts/engineering/repo/cleanup_branch_candidates.sh
bash scripts/engineering/repo/cleanup_branch_candidates.sh --apply
bash scripts/engineering/repo/cleanup_branch_candidates.sh --apply --with-remote
```

Prefer the `python -m scripts.engineering.repo ...` commands above as the
canonical public surface.

Use the shell wrappers only when you want a copy-pasteable bash transport for
the same workflows from shell-centric runbooks or ad-hoc operator sessions.
The split-testing-roadmap and sync-docs-issues shell wrappers are compatibility
convenience paths and should not be used as the primary documented entrypoint.
They forward all arguments to their Python implementations.
Use `python -m scripts.engineering.repo cleanup-branch-candidates` as the
canonical branch-cleanup entrypoint. Keep
`cleanup_branch_candidates.sh` when you want the same workflow through a
copy-pasteable shell transport with a safe dry-run default and archive tags for
the risky local branches.

## When to Use

| Command                     | When                                                                                     | Trigger                      |
| --------------------------- | ---------------------------------------------------------------------------------------- | ---------------------------- |
| `check-inventory`           | After adding/removing/renaming scripts                                                   | Manual or CI drift check     |
| `sync-wrapper-caller-matrix` | After wrapper-routing changes or before deleting a compatibility entrypoint              | Manual evidence refresh      |
| `check-catalog`             | After modifying `scripts/engineering/repo/catalog.yaml` or adding new script directories | CI gate (`architecture.yml`) |
| `check-versions`            | Before release or after bumping version in any file                                      | CI gate (`docs.yml`)         |
| `check-cleanliness`         | After adding files to repository root                                                    | Pre-commit hook              |
| `check-cleanup-governance`  | After changing cleanup docs, runbooks, or repo maintenance scripts                       | Root-hygiene workflow        |
| `check-root-review-registry` | After updating review-required or blocked cleanup lanes                                 | Root-hygiene workflow        |
| `check-gh-actions-pins` | After editing `.github/workflows/*` or `.github/actions/*`                              | Governance preflight gate    |
| `preflight-cleanup`         | Before release or before expensive local verification waves                              | Manual / `make clean-preflight` |
| `split-testing-roadmap`     | When converting a roadmap issue into executable GitHub child issues                      | Manual maintenance workflow  |
| `sync-docs-issues`          | When applying the documentation-sync issue package metadata and execution-order comments | Manual maintenance workflow  |
| `cleanup-branch-candidates` | When applying the agreed local-branch cleanup set with optional remote deletion          | Manual maintenance workflow  |
| `all`                       | Quick local sanity check before PR                                                       | Manual                       |

## Other Files

| File                           | Description                                               |
| ------------------------------ | --------------------------------------------------------- |
| `check_cleanup_governance.py`  | Guard active docs/scripts against broad cleanup guidance  |
| `preflight_cleanup.sh`         | Bounded release-preflight cleanup helper                  |
| `cleanup_branch_candidates.sh` | Dry-run/apply cleanup for the curated branch deletion set |
