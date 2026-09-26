# domain/behavior residual closeout (#8178–#8214)

- Branch: `grok-260807-108155`
- Fixed: **30**
- Rejected (with evidence): **7**
- Total: **37**

## Dispositions

- **#8178** `reject` — Presentation CSS in domain is pre-existing DQ HTML report surface; full layer move is ADR-sized, out of residual closeout. No product bug.
- **#8179** `reject` — Filesystem contract path extraction remains composition-adjacent domain pure helper; relocating needs wider refactor, no runtime defect.
- **#8180** `fixed` — validate_percent_value rejects NaN/Inf/non-numeric before range check.
- **#8181** `reject` — No PII-hash enable flag on DataNormalizationConfig; empty default salt is intentional. Fail-closed at use site via #8200.
- **#8182** `fixed` — validate_data rejects only None/empty collections; 0/False allowed.
- **#8183** `fixed` — Field priorities uniqueness keyed by priority rank across fields.
- **#8184** `reject` — DQReportSerializer domain placement is existing design; move to interfaces is ADR-sized without behavior defect.
- **#8185** `fixed` — ClassificationStats.__post_init__ enforces non-negative and bucket sum invariants.
- **#8186** `fixed` — Incoming schema fields taken as union over full record batch.
- **#8187** `reject` — create_ci_gate_report is domain pure projection for CI consumers; removal would break callers without product fix.
- **#8188** `fixed` — high_potency_threshold non-negative validation added; nested range configs already validate ordering.
- **#8189** `reject` — Registry-diff JSON parse is intentionally in SchemaClassifier domain helper; extraction move is non-residual.
- **#8190** `fixed` — EntityIdentityGenerator snapshots include/exclude sets at init.
- **#8191** `fixed` — Disposition policy preserves full issue order; rewrites blockers in place.
- **#8192** `fixed` — Threshold validator rejects bool before numeric range.
- **#8193** `fixed` — ValueValidator.__post_init__ applies NormalizationConfig molar ranges to unit windows.
- **#8194** `fixed` — Author dedupe uses str.casefold().
- **#8195** `fixed` — Common field iteration sorted for determinism.
- **#8196** `fixed` — error_records uses error markers only; quarantine kept separate.
- **#8197** `fixed` — Dropped eager _contract_policies cache; expose as derived property.
- **#8198** `fixed` — validate_composite reuses report via dataclasses.replace for execution_decision.
- **#8199** `fixed` — Gold substring removed; strictness_mode==strict upgrades WARN to QUARANTINE.
- **#8200** `fixed` — AuthorNormalizer.normalize_authors requires non-empty salt.
- **#8201** `fixed` — issue_code_overrides accepts Mapping and is snapshotted in __post_init__.
- **#8202** `fixed` — governance_impact uses effective blocker flag as SoT.
- **#8203** `fixed` — HTML serializer normalizes summary/checks/thresholds to dict before .get.
- **#8204** `fixed` — Fallback field collection only uses explicit columns/field_names keys.
- **#8205** `fixed` — aggregate_* default method uses self.default_method when method is None.
- **#8206** `fixed` — Empty explainability summary schema matches populated summary keys.
- **#8207** `fixed` — generate_field_explanation accepts merge_strategy and propagates from record explainer.
- **#8208** `fixed` — orjson.dumps protected with NON_STR_KEYS and TypeError/JSONEncodeError fallback.
- **#8209** `fixed` — NormalizationResult.value/unit required without cast(Any,None) defaults.
- **#8210** `fixed` — CompositeOutputExt builder constructs common kwargs once.
- **#8211** `fixed` — ast.literal_eval catches TypeError and RecursionError.
- **#8212** `fixed` — Cross-field outcomes apply invalid_record_policy like field/conditional.
- **#8213** `fixed` — Documented empty include as explicit filter-none (is not None).
- **#8214** `reject` — UnitConverter doctests already match current Concentration/PChembl API; no functional defect.

## Validation
- `pytest tests/unit/domain/behavior` green
- No tech-debt budget growth
