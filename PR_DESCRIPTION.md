## Summary

Completes issue #12374 by fully delegating expensive diagram architecture tests to the `docs-governance` lane (`docs.yml`), while retaining cheap docs/parity parity checks within the core PR Class lane (`pr-required.yml`). This prevents redundant execution of slow Mermaid/Puppeteer validations in `arch-tests`.

## Changes

1.  **Eliminated duplicate expensive tests in Class lane:** Added exclusion patterns (`--ignore=tests/architecture/test_diagram_artifact_check.py --ignore=tests/architecture/test_diagram_corpus_regression_guards.py --ignore=tests/architecture/test_diagram_drift_and_embed_guards.py --ignore=tests/architecture/test_diagram_issues_6205_6211_closeout.py --ignore=tests/architecture/test_diagram_lint_policy_rules.py --ignore=tests/architecture/test_diagram_narrative_docs_sync.py --ignore=tests/architecture/test_diagram_nightly_suite.py --ignore=tests/architecture/test_diagram_nightly_workflow.py --ignore=tests/architecture/test_diagram_quality_budget_security.py --ignore=tests/architecture/test_diagram_quality_gates.py --ignore=tests/architecture/test_diagram_regression_workflow.py --ignore=tests/architecture/test_diagram_tooling_fail_closed.py --ignore=tests/architecture/test_check_diagram_visual_smoke.py --ignore=tests/architecture/test_run_diagram_checks_script.py --ignore=tests/architecture/test_validate_mermaid_syntax_script.py`) to the `arch-pytest` target inside `.github/workflows/pr-required.yml`.
2.  **Intentional Coverage Overlap Maintained:** Fast, normative production contract ↔ docs parity checks (like `test_mkdocs_nav_references_existing_markdown_files` and `test_required_checks_prose_consistency`) deliberately remain in `pr-required.yml` to maintain tight invariant coverage on every PR, while also running structurally in `docs.yml`.

## Node Migration Crosswalk

| NodeID (Module) | Old Owner | New Owner | Trigger Conditions / Overlap |
| :--- | :--- | :--- | :--- |
| `tests/architecture/test_diagram*.py` | `arch-tests` (`pr-required.yml`) | `docs-governance` (`docs.yml`) | Runs in `docs.yml` when diagram-related paths or configs change. Excluded from `pr-required.yml` to save runner-minutes. |
| `tests/architecture/test_check_diagram_visual_smoke.py` | `arch-tests` (`pr-required.yml`) | `docs-governance` (`docs.yml`) | Render artifacts checks. Excluded from `pr-required.yml`. |
| `tests/architecture/test_run_diagram_checks_script.py` | `arch-tests` (`pr-required.yml`) | `docs-governance` (`docs.yml`) | Excluded from `pr-required.yml`. |
| `tests/architecture/test_validate_mermaid_syntax_script.py` | `arch-tests` (`pr-required.yml`) | `docs-governance` (`docs.yml`) | Requires Puppeteer. Excluded from `pr-required.yml`. |

## Metrics & Impact

-   **Coverage/Reporting:** Invariant reporting preserved. Nightly schedules automatically run `diagram-nightly.yml` and `architecture-docs-nightly.yml` ensuring full coverage.
-   **Quantitative effect:** ESTIMATED - by preventing duplicate Puppeteer/Mermaid setup in the main Class lane on non-diagram PRs, the `arch-tests` execution time is reduced. Wall-clock savings depend on runner contention; runner-minutes saved per execution approximately matches the execution time of the 15 ignored modules (UNKNOWN precise time without ≥3 runs).
