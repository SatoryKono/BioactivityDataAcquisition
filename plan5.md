1. **Fix Harness Script**:
   - Use `cat << 'EOF' > scripts/engineering/performance/measure_merger_input.py` to rewrite the script. It will import the real `MergeService` and use `resource.setrlimit`.

2. **Verify Harness Update**:
   - Run `cat scripts/engineering/performance/measure_merger_input.py` to verify the code was written.

3. **Add Regression/Smoke Tests**:
   - Use `cat << 'EOF' > tests/performance/test_measure_merger_input.py` to write a small smoke test that calls the harness with scale 100.

4. **Verify Smoke Test Creation**:
   - Run `cat tests/performance/test_measure_merger_input.py` to ensure it was created correctly.

5. **Execute & Test**:
   - Run `mkdir -p reports/performance/` and `uv run python scripts/engineering/performance/measure_merger_input.py`.
   - Run `uv run pytest tests/performance/test_measure_merger_input.py`.

6. **Refresh Artifacts**:
   - Run `make lint`
   - Run `uv run python -m scripts.engineering.qa.refresh_governance_artifacts --check || true`
   - Run `uv run python -m scripts.engineering.qa refresh-ci-drift-families --update --test-gov --flaky-fingerprint`
   - Run `uv run python -m scripts.engineering.qa refresh-ci-drift-families --check --test-gov --flaky-fingerprint`
   - Run `uv run python -m scripts.engineering.qa report-source-tree-manifest`
   - Run `uv run python -m scripts.engineering.qa.report_architecture_quality_scorecard`
   - Run `uv run python -m scripts.engineering.qa.report_module_coverage_inventory`
   - Run `uv run python -m scripts.engineering.qa report-debt-governance-gates --update`

7. **Verify Changes**:
   - Run `git status` to verify modified files.

8. **Commit Changes**:
   - Run `git add scripts/engineering/performance/measure_merger_input.py tests/performance/test_measure_merger_input.py reports/performance/merger_input_measurement.md $(git ls-files -m reports/ configs/ docs/ || true)`
   - Run `git commit --amend --no-edit` (or make a new commit).

9. **Run Full Tests**:
   - Run `uv run pytest tests/architecture/test_arch_s4_s9_gates.py tests/architecture/test_module_coverage_inventory_freshness.py tests/performance/` to guarantee no regressions in the committed codebase (due to timeout constraints, I am targeting relevant test subsets as per memory guidelines).

10. **Review Pre-commit Steps**:
   - Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done.

11. **Submit**:
   - End the session using the `submit` tool.
