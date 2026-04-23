# scripts/repo — Repository Governance

Repository hygiene and inventory governance tooling.

## Unified Entry Point

```bash
python -m scripts.engineering.repo --help
python -m scripts.engineering.repo <command> [args...]
```

## Commands

| Command                 | Script                           | Description                                                      |
| ----------------------- | -------------------------------- | ---------------------------------------------------------------- |
| `check-inventory`       | `check_scripts_inventory.py`     | Check scripts inventory drift against manifest                   |
| `check-catalog`         | `check_scripts_catalog.py`       | Validate catalog governance policy                               |
| `check-versions`        | `check_version_consistency.py`   | Check version consistency across project files                   |
| `check-cleanliness`     | `audit_root_cleanliness.py`      | Audit repository root layout allowlist                           |
| `split-testing-roadmap` | `split_testing_roadmap_issue.py` | Preview or create child issues for testing roadmap issue `#2511` |
| `sync-docs-issues`      | `sync_docs_issues.py`            | Preview or apply labels, milestone, and comments for docs-sync issues |
| `all`                   | *(all above)*                    | Run all checks sequentially                                      |

## Shell Wrapper

```bash
bash scripts/engineering/repo/split_testing_roadmap_issue.sh --help
GITHUB_PERSONAL_ACCESS_TOKEN=... bash scripts/engineering/repo/split_testing_roadmap_issue.sh --apply --comment-parent
bash scripts/engineering/repo/sync_docs_issues.sh --help
GITHUB_PERSONAL_ACCESS_TOKEN=... bash scripts/engineering/repo/sync_docs_issues.sh --apply --skip-milestone
```

Use the shell wrapper when you want a copy-pasteable bash entrypoint for the
testing-roadmap issue split workflow or the docs-sync issue metadata workflow.
Both wrappers forward all arguments to their Python implementations.

## When to Use

| Command                 | When                                                                    | Trigger                      |
| ----------------------- | ----------------------------------------------------------------------- | ---------------------------- |
| `check-inventory`       | After adding/removing/renaming scripts                                  | Manual or CI drift check     |
| `check-catalog`         | After modifying `scripts/engineering/repo/catalog.yaml` or adding new script directories | CI gate (`architecture.yml`) |
| `check-versions`        | Before release or after bumping version in any file                     | CI gate (`docs.yml`)         |
| `check-cleanliness`     | After adding files to repository root                                   | Pre-commit hook              |
| `split-testing-roadmap` | When converting a roadmap issue into executable GitHub child issues     | Manual maintenance workflow  |
| `sync-docs-issues`      | When applying the documentation-sync issue package metadata and execution-order comments | Manual maintenance workflow  |
| `all`                   | Quick local sanity check before PR                                      | Manual                       |

## Other Files

| File                   | Description               |
| ---------------------- | ------------------------- |
| `preflight_cleanup.sh` | Pre-commit cleanup helper |
