---
id: prompt.fragment.generated-artifact-ci
version: 1.0.0
status: active
class: fragment
owner: BioETL Team
summary: Generated-artifact CI families, hasher split, and safe origin/main fetch
---

## Generated-artifact CI

- Canon: `docs/05-operations/runbooks/generated-artifact-drift-workflow.md`.
- Telemetry `source_tree_sha256` ≠ `reports/quality/test-governance-current.json`
  `source_tree_sha256`. Do not copy SHA between them.
- Telemetry hasher: LF `tests/**/*.py`, `pyproject.toml`,
  `configs/quality/test_matrix.yaml`, `.github/workflows/tests.yml`.
- Non-`main` telemetry pin: `source_event=pull_request`; `source_commit` is
  an ancestor of HEAD.
- Fetch: `git fetch origin main`. Do not
  `git fetch origin main:refs/remotes/origin/main --depth=1` in a worktree.
- Windows: `.\.venv-win\Scripts\python.exe`; `PYTHONPATH=src`.
