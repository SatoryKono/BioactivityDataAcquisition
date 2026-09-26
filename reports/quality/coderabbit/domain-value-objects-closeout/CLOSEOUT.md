# domain/value_objects residual closeout (#8096–#8130 pack)

- Branch: `grok-260807-108155`
- Fixed: **26**
- Rejected: **4**
- Total: **30**

## Dispositions

- **#8096** `reject` — Public activity exports do not require residual version-bump/ADR packaging; no runtime defect.
- **#8097** `fixed` — ConfidenceScore rejects bool before int range validation.
- **#8098** `fixed` — InChI requires version+layer after InChI= prefix.
- **#8099** `fixed` — MolecularWeight rounds before exclusive range validation.
- **#8100** `fixed` — PublicationFieldGroup.from_string documents ValueError for unknown groups.
- **#8101** `fixed` — SchemaDriftResult deep-freezes type_changes mappings via MappingProxyType.
- **#8102** `fixed` — Bronze/Silver/Gold DQ reports require timezone-aware timestamps.
- **#8103** `fixed` — ValueObject immutability uses explicit _initialized flag; custom-init subclasses updated.
- **#8104** `reject` — PublicationYear.__eq__ already requires same concrete class via isinstance; no defect.
- **#8105** `fixed` — PubMedId.from_raw delegates coercion without premature str() wrapping.
- **#8106** `fixed` — PChemblValue.__lt__ annotates other as object.
- **#8107** `fixed` — ColumnQualifier.parse/is_qualified split with maxsplit=2 preserving field dots.
- **#8108** `reject` — Module coverage inventory refresh is ops hygiene, not a column_order product defect.
- **#8109** `fixed` — Completeness/FK/statistical DQ result dict fields frozen with MappingProxyType.
- **#8111** `fixed` — DQResult freezes rule_outcomes lists to tuples.
- **#8113** `fixed` — is_valid_numeric catches OverflowError from float() on oversized ints.
- **#8114** `fixed` — ProteinClassHierarchy.is_leaf reflects path/leaf identity state.
- **#8115** `fixed` — Bounded descriptor from_raw return annotations use Self | None.
- **#8116** `fixed` — FieldGroupConfig snapshots field_groups via MappingProxyType.
- **#8118** `fixed` — PubChemCid._validate accepts int | str input signature.
- **#8119** `fixed` — Concentration rejects non-finite values (NaN/Inf) and non-numeric types.
- **#8120** `fixed` — Concentration unit conversion uses single base-10 exponent delta.
- **#8122** `fixed` — SMILES.from_raw narrows blank/None without assert.
- **#8123** `fixed` — ISSN and ORCID validate ISO checksum digits after format normalization; fixed corrupted orcid URL prefixes.
- **#8124** `fixed` — BronzeWriteResult rejects relative paths without provider/entity segments and path traversal.
- **#8126** `reject` — compression_ratio already guards zero compressed/uncompressed sizes (pre-existing).
- **#8127** `fixed` — validate_taxonomy_id doctest uses is None comparisons for None returns.
- **#8128** `fixed` — CompoundId raises on unsupported CompoundSource.
- **#8129** `fixed` — BatchDQMetrics freezes column_stats via MappingProxyType.
- **#8130** `fixed` — dq_metrics compatibility aliases reduced to test-used _compute_column_stats/_extract_numeric_values.

## Validation
- `pytest tests/unit/domain/value_objects` green
- No tech-debt budget growth
