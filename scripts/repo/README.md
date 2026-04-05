# scripts/repo — Repository Governance

Repository hygiene and inventory governance tooling.

## Unified Entry Point

```bash
python -m scripts.repo --help
python -m scripts.repo <command> [args...]
```

## Commands

| Command                 | Script                           | Description                                                      |
| ----------------------- | -------------------------------- | ---------------------------------------------------------------- |
| `check-inventory`       | `check_scripts_inventory.py`     | Check scripts inventory drift against manifest                   |
| `check-catalog`         | `check_scripts_catalog.py`       | Validate catalog governance policy                               |
| `check-versions`        | `check_version_consistency.py`   | Check version consistency across project files                   |
| `check-cleanliness`     | `audit_root_cleanliness.py`      | Audit repository root layout allowlist                           |
| `split-testing-roadmap` | `split_testing_roadmap_issue.py` | Preview or create child issues for testing roadmap issue `#2511` |
| `all`                   | *(all above)*                    | Run all checks sequentially                                      |

## Shell Wrapper

```bash
bash scripts/repo/split_testing_roadmap_issue.sh --help
GITHUB_PERSONAL_ACCESS_TOKEN=... bash scripts/repo/split_testing_roadmap_issue.sh --apply --comment-parent
```

Use the shell wrapper when you want a copy-pasteable bash entrypoint for the
testing-roadmap issue split workflow. It forwards all arguments to the Python
implementation.

## When to Use

| Command                 | When                                                                    | Trigger                      |
| ----------------------- | ----------------------------------------------------------------------- | ---------------------------- |
| `check-inventory`       | After adding/removing/renaming scripts                                  | Manual or CI drift check     |
| `check-catalog`         | After modifying `scripts/catalog.yaml` or adding new script directories | CI gate (`architecture.yml`) |
| `check-versions`        | Before release or after bumping version in any file                     | CI gate (`docs.yml`)         |
| `check-cleanliness`     | After adding files to repository root                                   | Pre-commit hook              |
| `split-testing-roadmap` | When converting a roadmap issue into executable GitHub child issues     | Manual maintenance workflow  |
| `all`                   | Quick local sanity check before PR                                      | Manual                       |

## Other Files

| File                   | Description               |
| ---------------------- | ------------------------- |
| `preflight_cleanup.sh` | Pre-commit cleanup helper |
