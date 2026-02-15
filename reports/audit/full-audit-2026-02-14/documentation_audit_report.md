# Documentation Audit Report (BioETL v5.14+)

## Summary
- Date: 2026-02-14 01:35 UTC
- Scope: `docs/**`, `README.md`, `mkdocs.yml`, alignment with code in `src/bioetl/**`
- Overall status: WARN

## Inventory
- Docs scanned: 247 markdown files under `docs/`
- Entry points (README.md, mkdocs.yml): scanned

## Findings by severity
### Critical
- None

### High
- None

### Medium
- Potential orphan documentation file (no inbound refs): `docs/00-project/01-domain-objects.md`
- Potential orphan documentation file (no inbound refs): `docs/00-project/02-etl-layers.md`
- Potential orphan documentation file (no inbound refs): `docs/00-project/03-data-flow.md`
- Potential orphan documentation file (no inbound refs): `docs/00-project/04-duplication-reduction.md`
- Potential orphan documentation file (no inbound refs): `docs/00-project/05-physical-layout.md`
- Potential orphan documentation file (no inbound refs): `docs/00-project/TOOLS.md`
- Potential orphan documentation file (no inbound refs): `docs/00-project/agents/AGENT.md`
- Potential orphan documentation file (no inbound refs): `docs/00-project/agents/CLAUDE.md`
- Potential orphan documentation file (no inbound refs): `docs/00-project/agents/GEMINI.md`
- Potential orphan documentation file (no inbound refs): `docs/00-project/agents/orchestration/ORCHESTRATION.md`
- Potential orphan documentation file (no inbound refs): `docs/00-project/agents/orchestration/subagents/pyAuditBot.md`
- Potential orphan documentation file (no inbound refs): `docs/00-project/agents/orchestration/subagents/subagents_registry.md`
- Potential orphan documentation file (no inbound refs): `docs/00-project/architecture-index.md`
- Potential orphan documentation file (no inbound refs): `docs/01-requirements/REQUIREMENTS.md`
- Potential orphan documentation file (no inbound refs): `docs/02-architecture/00-overview.md`
- Potential orphan documentation file (no inbound refs): `docs/02-architecture/architecture-diagrams.md`
- Potential orphan documentation file (no inbound refs): `docs/02-architecture/module-consolidation-migration-requirements.md`
- Potential orphan documentation file (no inbound refs): `docs/03-data-model/field-catalog-source-pipelines.md`
- Potential orphan documentation file (no inbound refs): `docs/03-data-model/field-migration-checklist.md`
- Potential orphan documentation file (no inbound refs): `docs/03-data-model/field-naming-unification-matrix.md`
- Potential orphan documentation file (no inbound refs): `docs/03-data-model/pipeline-validation-matrix.md`
- Potential orphan documentation file (no inbound refs): `docs/03-data-model/rf-naming-unification-plan.md`
- Potential orphan documentation file (no inbound refs): `docs/03-guides/add-pipeline-existing-source.md`
- Potential orphan documentation file (no inbound refs): `docs/03-guides/cleanup-policy.md`
- Potential orphan documentation file (no inbound refs): `docs/03-guides/date-handling.md`
- Potential orphan documentation file (no inbound refs): `docs/03-guides/development/config-schema-guidelines.md`
- Potential orphan documentation file (no inbound refs): `docs/03-guides/file-path-audit-report.md`
- Potential orphan documentation file (no inbound refs): `docs/03-guides/migration-5.9-to-5.14.md`
- Potential orphan documentation file (no inbound refs): `docs/03-guides/pipeline-lifecycle.md`
- Potential orphan documentation file (no inbound refs): `docs/03-guides/quick-start.md`
- Potential orphan documentation file (no inbound refs): `docs/03-guides/registry-pattern.md`
- Potential orphan documentation file (no inbound refs): `docs/03-guides/silver-schema-testing-guide.md`
- Potential orphan documentation file (no inbound refs): `docs/03-guides/testing.md`
- Potential orphan documentation file (no inbound refs): `docs/04-reference/api/infrastructure/unified-http-client.md`
- Potential orphan documentation file (no inbound refs): `docs/04-reference/contracts/gold-schemas.md`
- Potential orphan documentation file (no inbound refs): `docs/04-reference/contracts/observability.md`
- Potential orphan documentation file (no inbound refs): `docs/04-reference/pipelines/INDEX.md`
- Potential orphan documentation file (no inbound refs): `docs/04-reference/pipelines/chembl-activity.md`
- Potential orphan documentation file (no inbound refs): `docs/04-reference/pipelines/chembl-assay.md`
- Potential orphan documentation file (no inbound refs): `docs/04-reference/pipelines/chembl/14-subcellular-fraction-spec.md`
- Potential orphan documentation file (no inbound refs): `docs/04-reference/pipelines/chembl/15-protein-class-spec.md`
- Potential orphan documentation file (no inbound refs): `docs/04-reference/pipelines/chembl/16-target-component-spec.md`
- Potential orphan documentation file (no inbound refs): `docs/04-reference/pipelines/chembl/17-publication-similarity-spec.md`
- Potential orphan documentation file (no inbound refs): `docs/04-reference/pipelines/chembl/18-publication-term-spec.md`
- Potential orphan documentation file (no inbound refs): `docs/04-reference/pipelines/composite/02-molecule-spec.md`
- Potential orphan documentation file (no inbound refs): `docs/04-reference/pipelines/composite/03-target-spec.md`
- Potential orphan documentation file (no inbound refs): `docs/04-reference/pipelines/openalex-publication.md`
- Potential orphan documentation file (no inbound refs): `docs/04-reference/pipelines/semanticscholar-publication.md`
- Potential orphan documentation file (no inbound refs): `docs/04-reference/providers/uniprot/idmapping.md`
- Potential orphan documentation file (no inbound refs): `docs/04-reference/publication-validation-index.md`
- Potential orphan documentation file (no inbound refs): `docs/04-reference/schemas/domain/chembl/activity-schema.md`
- Potential orphan documentation file (no inbound refs): `docs/04-reference/schemas/domain/chembl/assay-schema.md`
- Potential orphan documentation file (no inbound refs): `docs/04-reference/schemas/domain/chembl/molecule-schema.md`
- Potential orphan documentation file (no inbound refs): `docs/04-reference/schemas/domain/chembl/target-schema.md`
- Potential orphan documentation file (no inbound refs): `docs/04-reference/templates/pipeline-review-checklist.md`
- Potential orphan documentation file (no inbound refs): `docs/05-operations/runbooks/publication-validation-runbook.md`
- Potential orphan documentation file (no inbound refs): `docs/05-operations/verification/publication-field-mapping-report.md`
- Potential orphan documentation file (no inbound refs): `docs/05-operations/verification/pubmed-extraction-verification-report.md`
- Potential orphan documentation file (no inbound refs): `docs/05-operations/verification/semanticscholar-publication-pipeline-verification.md`
- Potential orphan documentation file (no inbound refs): `docs/adr/ADR-030-publication-field-unification.md`
- Potential orphan documentation file (no inbound refs): `docs/analysis/PUBLICATION_TYPE_NORMALIZATION_ANALYSIS.md`
- Potential orphan documentation file (no inbound refs): `docs/analysis/chembl-validation-matrix.md`
- Potential orphan documentation file (no inbound refs): `docs/analysis/crossref-validation-matrix.md`
- Potential orphan documentation file (no inbound refs): `docs/analysis/openalex-validation-matrix.md`
- Potential orphan documentation file (no inbound refs): `docs/analysis/pubmed-validation-matrix.md`
- Potential orphan documentation file (no inbound refs): `docs/analysis/semanticscholar-validation-matrix.md`
- Potential orphan documentation file (no inbound refs): `docs/audits/architecture-audit-2026-02-07.md`
- Potential orphan documentation file (no inbound refs): `docs/audits/architecture-audit-2026-02-10.md`
- Potential orphan documentation file (no inbound refs): `docs/audits/audit-correction-plan-2026-02-11.md`
- Potential orphan documentation file (no inbound refs): `docs/audits/documentation-audit-2026-02-11.md`
- Potential orphan documentation file (no inbound refs): `docs/audits/documentation-audit-full-2026-02-11.md`
- Potential orphan documentation file (no inbound refs): `docs/providers/chembl.md`
- Potential orphan documentation file (no inbound refs): `docs/testing/05-test-final.md`
- Missing gold contract docs for pipelines: chembl_publication_v1.0.json, chembl_publication_similarity_v1.0.json, chembl_publication_term_v1.0.json, chembl_subcellular_fraction_v1.0.json, chembl_tissue_v1.0.json

### Low
- None

## Proposed changes (prioritized)
1. Fix Critical/High nav and coverage gaps first (`mkdocs.yml` broken refs, missing provider/pipeline docs).
2. Resolve RULES/REQUIREMENTS traceability gaps and enforce REQ-ID cross links.
3. Archive or re-link orphan docs that are still relevant.

## Required decisions
- Confirm whether orphan docs should be archived (`docs/99-archive`) or linked into nav.
- Confirm expected contract versioning pattern (`*_v1.0.json`) for all active pipelines.

## Updated files (if changes applied)
- No documentation files were modified by this audit run.

## Dead or orphan docs (candidates)
- `docs/00-project/01-domain-objects.md`
- `docs/00-project/02-etl-layers.md`
- `docs/00-project/03-data-flow.md`
- `docs/00-project/04-duplication-reduction.md`
- `docs/00-project/05-physical-layout.md`
- `docs/00-project/TOOLS.md`
- `docs/00-project/agents/AGENT.md`
- `docs/00-project/agents/CLAUDE.md`
- `docs/00-project/agents/GEMINI.md`
- `docs/00-project/agents/orchestration/ORCHESTRATION.md`
- `docs/00-project/agents/orchestration/subagents/pyAuditBot.md`
- `docs/00-project/agents/orchestration/subagents/subagents_registry.md`
- `docs/00-project/architecture-index.md`
- `docs/01-requirements/REQUIREMENTS.md`
- `docs/02-architecture/00-overview.md`
- `docs/02-architecture/architecture-diagrams.md`
- `docs/02-architecture/module-consolidation-migration-requirements.md`
- `docs/03-data-model/field-catalog-source-pipelines.md`
- `docs/03-data-model/field-migration-checklist.md`
- `docs/03-data-model/field-naming-unification-matrix.md`
- `docs/03-data-model/pipeline-validation-matrix.md`
- `docs/03-data-model/rf-naming-unification-plan.md`
- `docs/03-guides/add-pipeline-existing-source.md`
- `docs/03-guides/cleanup-policy.md`
- `docs/03-guides/date-handling.md`
- `docs/03-guides/development/config-schema-guidelines.md`
- `docs/03-guides/file-path-audit-report.md`
- `docs/03-guides/migration-5.9-to-5.14.md`
- `docs/03-guides/pipeline-lifecycle.md`
- `docs/03-guides/quick-start.md`
- `docs/03-guides/registry-pattern.md`
- `docs/03-guides/silver-schema-testing-guide.md`
- `docs/03-guides/testing.md`
- `docs/04-reference/api/infrastructure/unified-http-client.md`
- `docs/04-reference/contracts/gold-schemas.md`
- `docs/04-reference/contracts/observability.md`
- `docs/04-reference/pipelines/INDEX.md`
- `docs/04-reference/pipelines/chembl-activity.md`
- `docs/04-reference/pipelines/chembl-assay.md`
- `docs/04-reference/pipelines/chembl/14-subcellular-fraction-spec.md`
- `docs/04-reference/pipelines/chembl/15-protein-class-spec.md`
- `docs/04-reference/pipelines/chembl/16-target-component-spec.md`
- `docs/04-reference/pipelines/chembl/17-publication-similarity-spec.md`
- `docs/04-reference/pipelines/chembl/18-publication-term-spec.md`
- `docs/04-reference/pipelines/composite/02-molecule-spec.md`
- `docs/04-reference/pipelines/composite/03-target-spec.md`
- `docs/04-reference/pipelines/openalex-publication.md`
- `docs/04-reference/pipelines/semanticscholar-publication.md`
- `docs/04-reference/providers/uniprot/idmapping.md`
- `docs/04-reference/publication-validation-index.md`
- `docs/04-reference/schemas/domain/chembl/activity-schema.md`
- `docs/04-reference/schemas/domain/chembl/assay-schema.md`
- `docs/04-reference/schemas/domain/chembl/molecule-schema.md`
- `docs/04-reference/schemas/domain/chembl/target-schema.md`
- `docs/04-reference/templates/pipeline-review-checklist.md`
- `docs/05-operations/runbooks/publication-validation-runbook.md`
- `docs/05-operations/verification/publication-field-mapping-report.md`
- `docs/05-operations/verification/pubmed-extraction-verification-report.md`
- `docs/05-operations/verification/semanticscholar-publication-pipeline-verification.md`
- `docs/adr/ADR-030-publication-field-unification.md`
- `docs/analysis/PUBLICATION_TYPE_NORMALIZATION_ANALYSIS.md`
- `docs/analysis/chembl-validation-matrix.md`
- `docs/analysis/crossref-validation-matrix.md`
- `docs/analysis/openalex-validation-matrix.md`
- `docs/analysis/pubmed-validation-matrix.md`
- `docs/analysis/semanticscholar-validation-matrix.md`
- `docs/audits/architecture-audit-2026-02-07.md`
- `docs/audits/architecture-audit-2026-02-10.md`
- `docs/audits/audit-correction-plan-2026-02-11.md`
- `docs/audits/documentation-audit-2026-02-11.md`
- `docs/audits/documentation-audit-full-2026-02-11.md`
- `docs/providers/chembl.md`
- `docs/testing/05-test-final.md`

## Verification
- RULES.md and REQUIREMENTS.md sync: OK/No critical mismatch detected
- ADR alignment (ADR-010, ADR-014, ADR-017): WARN
- Link check: WARN/OK

## Extra Coverage Gaps
- Missing pipeline docs mentions: none
- Missing provider docs: none
- Missing contract docs: chembl_publication_v1.0.json, chembl_publication_similarity_v1.0.json, chembl_publication_term_v1.0.json, chembl_subcellular_fraction_v1.0.json, chembl_tissue_v1.0.json