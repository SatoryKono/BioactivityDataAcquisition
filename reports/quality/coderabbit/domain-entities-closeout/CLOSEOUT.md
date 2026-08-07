# domain/entities residual closeout (#8131–#8154)

- Branch: `grok-260807-108155`
- Fixed: **17**
- Rejected: **7**
- Total: **24**

## Dispositions

- **#8131** `reject` — ChEMBL activity/target DTO facade relocation to adapters is ADR-sized layering work; no runtime defect in current domain DTOs.
- **#8132** `fixed` — ChEMBLTissue validates stripped tissue_id/pref_name and rejects whitespace-only values.
- **#8133** `fixed` — BaseEntity.__post_init__ requires non-empty run_id/run_type and non-None ingestion_ts.
- **#8134** `reject` — PubMed ArticleRecord stays domain-facing DTO; adapter move is campaign-wide architecture, not residual product fix.
- **#8135** `reject` — Public bioactivity exports do not require version-bump artifacts for residual closeout; no code defect.
- **#8136** `fixed` — Bioactivity.with_state enforces documented forward transitions RAW->NORMALIZED->VALIDATED.
- **#8137** `reject` — ChEMBL DTO re-export facade remains intentional domain boundary surface.
- **#8138** `fixed` — Cell/target tax_id Field descriptions document ChEMBL mirror + NCBI Taxonomy meaning.
- **#8139** `fixed` — Removed unreachable TYPE_CHECKING branch from entities.__getattr__.
- **#8140** `fixed` — _safe_str rejects bools and normalizes integral floats.
- **#8141** `reject` — File-wide mypy misc suppression on CrossRef overrides is established pattern; per-line churn has no product impact.
- **#8142** `fixed` — Target/TargetComponent freeze list-shaped fields via freeze_fields.
- **#8143** `fixed` — LOOKUP_METHODS registered in package _ENTITY_IMPORTS lazy map.
- **#8144** `reject` — File-wide mypy misc suppression on PubChem overrides is established pattern; no product defect.
- **#8145** `fixed` — ActivityRecord.target_tax_id typed as int | None.
- **#8146** `fixed` — PublicationEntityBase syncs doi/pmid/pmc_id with publication_* aliases.
- **#8147** `fixed` — _first_truthy_value returns value directly without redundant intermediate.
- **#8148** `fixed` — variant_sequence comment corrected to Amino acid sequence.
- **#8149** `fixed` — Shared require_positive_id/require_non_empty_str helpers extracted to _validators.
- **#8150** `reject` — Coverage inventory refresh is post-change ops hygiene, not a UniProt entity defect; no module behavior change required for residual.
- **#8151** `fixed` — Semantic Scholar paper_id must be 40 hex characters.
- **#8152** `fixed` — MoleculeRecord/TargetRecord IDs require min_length=1.
- **#8153** `fixed` — TissueRecord/CompoundLinkRecord IDs require min_length=1.
- **#8154** `fixed` — Tanimoto fields constrained to [0.0, 1.0].

## Validation
- `pytest tests/unit/domain/entities` green
- No tech-debt budget growth
