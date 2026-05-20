# Root Hygiene Issue Drafts Index

These files are publish-ready GitHub issue drafts created from the
2026-05-19 file-structure cleanup audit plus local repository verification in
this workspace.

Direct publication to GitHub was blocked in this session because local `gh`
CLI is not installed.

## Publish Order

### P1

1. `RH-014-Rehome-Observability-Cardinality-Evidence-Out-Of-Forbidden-Root-Artifacts.md`
2. `RH-015-Remove-Tracked-Root-Transient-Helpers-And-Restore-Root-Allowlist-Compliance.md`

### P2

3. `RH-016-Expand-Root-Hygiene-Review-Lanes-For-Observed-Transient-Root-Families.md`

## Verification Snapshot

- `./.venv/bin/python scripts/engineering/repo/audit_root_cleanliness.py --strict-untracked`
  currently fails on tracked root drift:
  - `temp_analyze_conflicting.py`
  - `temp_get_hash.py`
  - `test_output.txt`
  - `artifacts/`
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
- The highest-signal defect is the contradiction between root-hygiene policy
  and the current observability evidence path under `artifacts/`.
