# Plan to solve issue #12473

The issue indicates that some `publication` entities across various providers still have `severity: warn` instead of `severity: error` in their data quality config fields (specifically `publication_year`, `author_orcids`, `issn_list`, `citations_received`, `citations_made`, `doi_alias_equality`, etc.).

1. **Verify changed configs:**
   - I have already modified the yaml configs in `configs/entities/*/publication.yaml` to change `severity: warn` to `severity: error`.
   - I also updated the test assertions in `tests/integration/config/test_dq_config_loading.py` to check for `error` instead of `warn` for `publication_year` rules.

2. **Complete Pre-Commit Steps**
   - Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done (e.g. running ARTIFACT_REFRESH).

3. **Submit the Change**
   - Submit the branch using the `submit` tool and wait for PR creation.
