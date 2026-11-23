______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P1
  Last verified: '2026-11-23'

______________________________________________________________________

# IUPHAR Target Classification Semantics (RF-001)

Contract/baseline for [#13309](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/13309)
under epic [#13308](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/13308).
This page records vocabulary and decision boundaries. It does **not** admit
biological accuracy, migrate V30 tables, or rewrite historical results.

Canonical machine sources:

- `src/iuphar_target_class/semantics.py` (`rf001-2026-11-23`)
- `data/iuphar_target_class/rf001/baseline_manifest.json`
- `src/bioetl/domain/config/target_classification.py`
- `src/iuphar_target_class/policy.py` → `rf001_semantics`
- `configs/entities/chembl/target.yaml` (standalone)
- `configs/composites/target.yaml` (enriched composite)

## Field dictionary

| Field / prefix | Layer | Meaning |
| --- | --- | --- |
| `target_type` | ChEMBL object | Provider object type (`SINGLE PROTEIN`, …). Never an IUPHAR class. |
| `iuphar_*` | Reference / direct | Snapshot identity and approved type/family mapping outputs. |
| `local_*` | Local rules | EC / annotation / prediction rules. Must not be copied into `iuphar_*`. |
| `effective_*`, `decision_status` | Final + provenance | Resolution-table outcome and its source (`iuphar_normalized`, `local_rule`, `none`). |
| `legacy_iuphar_class` | Legacy comparison | Historical M/Excel value for comparison only. |

Nine additive V31 business columns (enrich only): see
[`TARGET_CLASSIFICATION_FIELDS`](../../../../src/bioetl/domain/config/target_classification.py)
and [chembl_target_v3.1.json](../../contracts/gold/chembl_target_v3.1.json).

## Statuses

- **Match:** `matched`, `ambiguous`, `identity_conflict`, `insufficient_input`,
  `source_unavailable`, `not_found`, `contract_error`.
- **Annotation:** `available`, `partial`, `unmapped_type`, `conflicting`,
  `not_available`.
- **Local:** `supported`, `not_supported`, `candidate_only`, `conflicting`.
- **Decision:** `resolved`, `requires_review`, `unresolved`.
- **Completeness:** `family_only`, `admission_complete`, `complete`, `incomplete`.
- **Uncertainty tokens:** `unknown` / `partial` / `ambiguous` / `conflict` stay
  explicit; do not collapse them into a class.

`source_unavailable` means required snapshot sources are incomplete.
`not_found` means the snapshot is complete and searchable channels yield no hit.
They remain distinct.

## Capability matrix

| Surface | Priority | Full features | Notes |
| --- | --- | --- | --- |
| `composite_target` | 1 | After dependency joins | UniProt protein, idmapping accession, L1–L5 protein-class summary. **RF-003 (#13311)** runs full classification after joins via `data/iuphar_target_class/rf003/feature_whitelist.json`. |
| standalone `chembl_target` | 2 | No | Seed fields only; early classification cannot use post-join features. |

Production `target_classification.mode` remains `"off"` until a later RF admits
enrich. Matched counts are not biological accuracy.
`biological_accuracy_accepted` stays `false` unless independently proven.

## Paths, missing markers, legacy Other

- Canonical path direction is **root → leaf** (`root_to_leaf`).
- `leaf_to_root` is migration/comparison text only and does not choose a class.
- Multi-parent paths are retained; graph defects do not invent a class from a
  cut path. `Table.Distinct`-style collapse is not an identity decision.
- **RF-005 (#13313):** repeated family IDs with the same payload **union**
  parent sets (order-independent). Conflicting payloads stay a graph defect.
  `iuphar_subclass` comes only from the approved type/family dictionary and
  does **not** elevate `annotation_capability` above `family_only`.
  `local:` / `synthetic:` / `legacy:` IDs stay outside the official numeric
  family graph. Coverage matrix:
  [`data/iuphar_target_class/rf005/coverage_matrix.json`](../../../../data/iuphar_target_class/rf005/coverage_matrix.json).
- Missing markers currently: `#n/a`, `N/A`, `n/a`, `""`, plus null and
  whitespace-only. `missing_markers_version` remains unset (`не утверждено`).
- **Other Protein Target** is allowed only from an approved direct/family
  mapping, an explicit local rule, or as a legacy comparison value. It is
  forbidden as a default for unmapped/unknown/ambiguous rows or from L1/L2
  prediction alone.

## Versioning / profile change rules

| Surface | Current baseline | Change rule |
| --- | --- | --- |
| `rules_version` | `plan-v1-r9` | New rules → new version; do not rewrite historical runs |
| `normalization_version` | unset | Approving missing markers publishes a new version |
| `classification_schema_version` (profile) | `3.1.0` when shadow/enrich enabled | Adapter field; not the same as table contract |
| table / business contract | off/shadow → V30 / `3.0.0`; enrich → V31 / `3.1.0` | Nine additive columns only after enrich admission |
| originals | stage-0 + acceptance artifacts | Preserve; recompute as a separate run |

## Baseline manifest

[`data/iuphar_target_class/rf001/baseline_manifest.json`](../../../../data/iuphar_target_class/rf001/baseline_manifest.json)
pins **immutable** stage-0 / acceptance / upstream hashes under
`pinned_artifacts`. Live configs, docs, and source contracts are listed under
`mutable_surfaces` (path + role only) so comment-level edits do not invalidate
the RF-001 baseline. Excel/M caches outside the repository stay `not_pinned`.
Audit control counts from epic #13308 are observations only.

## Audit counterexamples (manual)

1. Local output must not appear in `iuphar_*`.
2. Multi-parent hierarchy must not lose parents.
3. Unmapped/unknown must not become false Other.
4. `Table.Distinct`-style selection must not hide ambiguity.
5. Matched counts ≠ `biological_accuracy_accepted`.

## Related

- Runbook: [iuphar-target-classification.md](../../../05-operations/runbooks/iuphar-target-classification.md)
- Target pipeline spec: [04-target-spec.md](04-target-spec.md)
