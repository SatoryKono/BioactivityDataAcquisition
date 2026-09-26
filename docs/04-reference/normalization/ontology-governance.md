______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-07-28'

______________________________________________________________________

# Ontology Governance Procedures

**Issue:** #6561

## Purpose

Govern controlled vocabularies and ontology-like fields so normalization and DQ
share one authority (no dual SSOT).

## Authority locations

| Kind | Path examples |
| --- | --- |
| Enums | `configs/enums/**` |
| Controlled vocab | `configs/vocab/**` |
| Ontology policy YAML | e.g. `configs/vocab/chembl_ontology.yaml` |
| Domain profiles | `src/bioetl/domain/normalization/profiles/` |
| Generated field matrices | `docs/reports/generated/pipeline_normalization_field_matrix/` |

## Change procedure

1. **Inventory** observed values (fixtures, sample Bronze).
2. **Propose** enum/vocab delta with owner (provider family).
3. **Update** YAML SSOT + profile code in the same change when behavior shifts.
4. **Align** DQ patterns / gold contracts with the same tokens.
5. **Test** subset/drift tests and representative pipeline fixtures.
6. **Docs** — update family overview if operator-facing meaning changes.

## Rules

- Prefer extend-only enums; removals need migration notes
- Unknown values: explicit policy (reject vs quarantine vs null) — never silent drop
- Ontology IDs keep family canonical form (see identifier policies)
- No hard-coded synonym tables in adapters when a registry exists

## Review checklist

- [ ] Single authority file identified
- [ ] Profile + DQ + gold agree
- [ ] Fixtures cover new edge tokens
- [ ] Hash/identity impact acknowledged

## Related

- [chembl-normalization-overview](chembl-normalization-overview.md)
- [reference-identifiers](reference-identifiers.md)
