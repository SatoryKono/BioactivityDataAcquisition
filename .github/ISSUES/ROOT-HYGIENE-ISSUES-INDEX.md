# Root Hygiene Issue Drafts Index

These files are publish-ready GitHub issue drafts created from the
2026-05-19 file-structure cleanup audit plus local repository verification in
this workspace. Additional drafts were added on 2026-05-21 after a fresh
repo-native audit surfaced new live root-governance gaps.

Direct publication to GitHub was blocked in this session because local `gh`
CLI is not installed.

## Publish Order

### P1

1. `RH-014-Rehome-Observability-Cardinality-Evidence-Out-Of-Forbidden-Root-Artifacts.md`
2. `RH-015-Remove-Tracked-Root-Transient-Helpers-And-Restore-Root-Allowlist-Compliance.md`

### P2

3. `RH-016-Expand-Root-Hygiene-Review-Lanes-For-Observed-Transient-Root-Families.md`

### P2.5

4. `RH-017-Resolve-Noncanonical-Concepts-Root-Documentation-Surface.md`
5. `RH-018-Resolve-Tracked-Extra-Docker-Compose-Root-Allowlist-Drift.md`

## Verification Snapshot

- `./.venv/bin/python scripts/engineering/repo/audit_root_cleanliness.py --strict-untracked`
  passes on tracked root policy after the RH-014/015/016/017/018 closeout.
- `python3 scripts/engineering/diagnostics/audit_structure.py --path .`
  reports a clean structure state.
- `./.venv/bin/python -m pytest -q tests/unit/scripts/repo/test_check_root_hygiene_review_registry.py tests/architecture/test_root_hygiene_review_registry.py tests/unit/scripts/repo/test_cleanup_repository.py`
  pass.
- `reports/quality/root-hygiene-cleanup-classification.json` currently reports
  `337` cleanup candidates, all `SAFE`, with `0` `REVIEW_REQUIRED` and `0`
  `BLOCKED`.
- `.env`, `scripts/ai/codex/.env.codex`, `scripts/ai/gemini/.env.gemini`, and
  `scripts/ai/vibe/.env.vibe` are local secret-bearing env surfaces and must
  remain ignored/untracked repo artifacts.

## Not Reopened In This Pack

- retention-sensitive cleanup proposal template already exists:
  `.github/ISSUE_TEMPLATE/retention_sensitive_cleanup.yml`
- broad cleanup guidance guard already exists:
  `scripts/engineering/repo/check_cleanup_governance.py`
- root-hygiene CI already exports machine-readable cleanup evidence:
  `.github/workflows/root-hygiene.yml`
- the `.cursor/**` policy conflict described by the audit is no longer a live
  governance gap in this checkout because `.cursor` is registered as a curated
  shared surface in `configs/quality/repo_structure_catalog.yaml` and the file
  policy documents that exception explicitly

## Notes

- This pack intentionally converts only confirmed residual gaps into issues.
- It does not open a generic "clean the repo" umbrella issue.
- All previously identified tracked-tree gaps for this pack are now addressed in-draft.
- The pack currently acts as closeout evidence and audit traceability for completed root-hygiene work.
