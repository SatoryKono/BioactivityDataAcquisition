"""Entity and composite row construction for the normalization matrix."""

from __future__ import annotations

from scripts.docs.matrix.generate_pipeline_normalization_matrix import (
    Any,
    COMPOSITE_PIPELINE_KIND,
    ENTITY_PIPELINE_KIND,
    ENTITY_PROFILE_FIELD_ALIASES,
    ENTITY_SILVER_SCHEMA_REGISTRY,
    FALLBACK_BUSINESS,
    FALLBACK_TECHNICAL_PASSTHROUGH,
    FALSE_TEXT,
    JOIN_KEY_NORMALIZATION_POLICIES,
    NO_NORMALIZER,
    NormalizationRulesPolicy,
    PROFILE_NORMALIZATION_SOURCE,
    Path,
    _augment_row_with_inventory_metadata,
    _composite_inherited_field_type,
    _composite_schema_coverage,
    _dq_coverage,
    _ensure_chembl_policy_registry_initialized,
    _hash_ordering,
    _normalizer_name,
    _row_policy_metadata,
    _schema_coverage,
    _semantic_category,
    _strictness,
    _validate_non_chembl_inventory_rows,
    is_date_field,
    is_doi_field,
    is_pmid_field,
    is_smiles_field,
    pa,
    resolve_normalization_profile,
    structured_payload_policy,
    yaml,
)

def _entity_config_paths() -> list[Path]:
    return sorted(
        path
        for path in Path("configs/entities").glob("*/*.yaml")
        if path.parent.name != "composite"
    )


def _composite_config_paths() -> list[Path]:
    return sorted(Path("configs/composites").glob("*.yaml"))


def _load_yaml(path: Path) -> dict[str, object]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _render_bool(value: bool | None) -> str:
    if value is None:
        return ""
    return "true" if value else "false"


def _looks_like_string_type(type_name: str) -> bool:
    lowered = type_name.lower()
    return "string" in lowered or "large_string" in lowered


def _normalize_summary_from_policy(*, key: str, trim: bool, lowercase: bool) -> str:
    if key == "doi":
        return (
            "Validate DOI through the canonical domain identifier contract, then "
            "emit lowercase join-canonical text."
        )
    if key == "inchi_key":
        return (
            "Validate InChIKey through the canonical domain value-object contract, "
            "then emit uppercase join-canonical text."
        )
    if key == "pmid":
        return (
            "Validate PMID through the canonical domain identifier contract, then "
            "emit digits-only join-canonical text."
        )
    if key == "pmc_id":
        return (
            "Validate PMC identifier through the canonical domain identifier "
            "contract, then emit lowercase join-canonical text."
        )
    if key == "title":
        return (
            "Normalize fallback title join text through canonical title cleanup "
            "while preserving case."
        )
    if key == "target_id":
        return (
            "Validate ChEMBL target identifier through the canonical domain value-"
            "object contract, then emit uppercase join-canonical text."
        )
    if key == "uniprot_accession":
        return (
            "Validate UniProt accession through the canonical domain value-object "
            "contract, then emit uppercase join-canonical text."
        )
    if trim and lowercase:
        return "Trim surrounding whitespace and lowercase join-key text."
    if trim:
        return "Trim surrounding whitespace for join-key text."
    if lowercase:
        return "Lowercase join-key text."
    return "Composite join key is preserved as-is by explicit no-op policy."


def _fallback_contract(
    rule_set: NormalizationRulesPolicy,
    *,
    field_name: str,
    field_type: str,
) -> tuple[str, str, str]:
    if field_name in rule_set.passthrough_fields:
        return (
            FALLBACK_TECHNICAL_PASSTHROUGH,
            "passthrough",
            "Field is passed through unchanged by the canonical fallback normalization seam.",
        )
    if field_name.startswith("_"):
        return (
            FALLBACK_TECHNICAL_PASSTHROUGH,
            "passthrough",
            "Technical field appears in the normalization inventory only; "
            "persisted-row publication is governed separately by the "
            "Silver/Gold storage contract.",
        )
    if field_name in rule_set.title_fields:
        return (
            FALLBACK_BUSINESS,
            "normalize_title",
            "Normalize title text through HTML/entity cleanup and whitespace normalization.",
        )
    if field_name in rule_set.abstract_fields:
        return (
            FALLBACK_BUSINESS,
            "normalize_abstract",
            "Normalize abstract text through HTML/entity cleanup and whitespace normalization.",
        )
    if field_name in rule_set.oa_status_fields:
        return (
            FALLBACK_BUSINESS,
            "normalize_oa_status",
            "Trim textual OA status and lowercase the resulting value.",
        )
    if is_doi_field(field_name, rule_set=rule_set):
        return (
            FALLBACK_BUSINESS,
            "normalize_profile_doi",
            "Normalize DOI through the canonical fallback identifier helper.",
        )
    if is_pmid_field(field_name, rule_set=rule_set):
        return (
            FALLBACK_BUSINESS,
            "normalize_profile_pmid",
            "Normalize PMID through the canonical fallback identifier helper.",
        )
    if is_date_field(field_name, rule_set=rule_set):
        return (
            FALLBACK_BUSINESS,
            "normalize_partial_date",
            "Canonicalize supported date text to the stable partial-date representation.",
        )
    if is_smiles_field(field_name):
        return (
            FALLBACK_BUSINESS,
            "SMILES.from_raw(mode=soft)",
            "Validate and trim SMILES text; invalid values collapse to None.",
        )
    if _looks_like_string_type(field_type):
        return (
            FALLBACK_BUSINESS,
            "normalize_string + canonicalize_json_string(json-like)",
            "Trim string values, collapse blanks to None, and canonicalize JSON-looking string payloads.",
        )
    return (
        FALLBACK_BUSINESS,
        "preserve_non_string",
        "No field-specific fallback normalizer is applied; non-string values are preserved as-is.",
    )


def _build_entity_rows_for_pipeline(
    *,
    pipeline_name: str,
    provider: str,
    entity: str,
    schema: pa.Schema,
) -> list[dict[str, str]]:
    profile = resolve_normalization_profile(provider, entity)
    rule_set = NormalizationRulesPolicy()
    rows: list[dict[str, str]] = []
    for field_name in schema.names:
        field = schema.field(field_name)
        field_type = str(field.type)
        profile_rule = _resolve_profile_rule(
            profile=profile,
            pipeline_name=pipeline_name,
            field_name=field_name,
        )
        if profile_rule is not None:
            rows.append(
                _entity_profile_row(
                    provider=provider,
                    entity=entity,
                    pipeline_name=pipeline_name,
                    field_name=field_name,
                    field_type=field_type,
                    arrow_nullable=field.nullable,
                    profile_rule=profile_rule,
                )
            )
        else:
            source, normalizer, summary = _fallback_contract(
                rule_set,
                field_name=field_name,
                field_type=field_type,
            )
            rows.append(
                _entity_fallback_row(
                    provider=provider,
                    entity=entity,
                    pipeline_name=pipeline_name,
                    field_name=field_name,
                    field_type=field_type,
                    arrow_nullable=field.nullable,
                    source=source,
                    normalizer=normalizer,
                    summary=summary,
                )
            )
        for alias_field_name in _alias_field_names(
            pipeline_name=pipeline_name,
            field_name=field_name,
            schema_field_names=schema.names,
        ):
            alias_profile_rule = _resolve_profile_rule(
                profile=profile,
                pipeline_name=pipeline_name,
                field_name=alias_field_name,
            )
            if alias_profile_rule is not None:
                rows.append(
                    _entity_profile_row(
                        provider=provider,
                        entity=entity,
                        pipeline_name=pipeline_name,
                        field_name=alias_field_name,
                        field_type=field_type,
                        arrow_nullable=field.nullable,
                        profile_rule=alias_profile_rule,
                    )
                )
            else:
                source, normalizer, summary = _fallback_contract(
                    rule_set,
                    field_name=alias_field_name,
                    field_type=field_type,
                )
                rows.append(
                    _entity_fallback_row(
                        provider=provider,
                        entity=entity,
                        pipeline_name=pipeline_name,
                        field_name=alias_field_name,
                        field_type=field_type,
                        arrow_nullable=field.nullable,
                        source=source,
                        normalizer=normalizer,
                        summary=summary,
                    )
                )
    return rows


def _alias_field_names(
    *,
    pipeline_name: str,
    field_name: str,
    schema_field_names: list[str],
) -> tuple[str, ...]:
    """Return reviewed alias rows that should also be emitted for one Silver field."""
    aliases = ENTITY_PROFILE_FIELD_ALIASES.get(pipeline_name, {})
    reverse_aliases = {alias: source for source, alias in aliases.items()}
    candidates = [
        aliases.get(field_name),
        reverse_aliases.get(field_name),
    ]
    return tuple(
        candidate
        for candidate in dict[str, object].fromkeys(candidates)
        if candidate is not None and candidate not in schema_field_names
    )


def _field_lookup_candidates(*, pipeline_name: str, field_name: str) -> tuple[str, ...]:
    """Try the shipped field name first, then any reviewed alias seam in either direction."""
    aliases = ENTITY_PROFILE_FIELD_ALIASES.get(pipeline_name, {})
    reverse_aliases = {alias: source for source, alias in aliases.items()}
    candidates = [field_name]
    alias_name = aliases.get(field_name)
    if alias_name is not None:
        candidates.append(alias_name)
    source_name = reverse_aliases.get(field_name)
    if source_name is not None:
        candidates.append(source_name)
    return tuple(dict[str, object].fromkeys(candidates))


def _resolve_profile_rule(
    *, profile: Any | None, pipeline_name: str, field_name: str
) -> Any | None:
    if profile is None:
        return None
    for candidate in _field_lookup_candidates(
        pipeline_name=pipeline_name,
        field_name=field_name,
    ):
        rule = profile.rule_for(candidate)
        if rule is not None:
            return rule
    return None


def _resolve_field_value(
    *, pipeline_name: str, field_name: str, available_values: dict[str, str]
) -> str | None:
    for candidate in _field_lookup_candidates(
        pipeline_name=pipeline_name,
        field_name=field_name,
    ):
        value = available_values.get(candidate)
        if value is not None:
            return value
    return None


def _profile_lookup_field_name(*, pipeline_name: str, field_name: str) -> str:
    """Resolve reviewed Silver legacy aliases to canonical profile/schema fields."""
    return _field_lookup_candidates(
        pipeline_name=pipeline_name,
        field_name=field_name,
    )[0]


def _entity_profile_row(
    *,
    provider: str,
    entity: str,
    pipeline_name: str,
    field_name: str,
    field_type: str,
    arrow_nullable: bool,
    profile_rule: Any,
) -> dict[str, str]:
    """Build one entity matrix row sourced from an explicit profile rule."""
    notes = profile_rule.notes or ""
    notes = _augment_structured_payload_policy_notes(
        provider=provider,
        entity=entity,
        field_name=field_name,
        notes=notes,
    )
    normalizer_name = _normalizer_name(
        profile_rule.normalizer,
        field_name=field_name,
        notes=profile_rule.notes,
    )
    controlled_vocabulary_source, strictness, semantic_category, policy_scope = (
        _row_policy_metadata(
            provider=provider,
            entity=entity,
            field_name=field_name,
            normalization_source=PROFILE_NORMALIZATION_SOURCE,
            normalizer_name=normalizer_name,
            notes=notes,
        )
    )
    return {
        "provider": provider,
        "pipeline_name": pipeline_name,
        "pipeline_kind": ENTITY_PIPELINE_KIND,
        "entity": entity,
        "field_name": field_name,
        "field_type": field_type,
        "normalization_source": PROFILE_NORMALIZATION_SOURCE,
        "normalizer": normalizer_name,
        "normalization_summary": notes,
        "controlled_vocabulary_source": controlled_vocabulary_source,
        "policy_scope": policy_scope,
        "semantic_category": semantic_category,
        "include_in_content_hash": _render_bool(profile_rule.include_in_hash),
        "set_like": _render_bool(profile_rule.set_like),
        "hash_ordering": _hash_ordering(
            provider=provider,
            entity=entity,
            field_name=field_name,
            include_in_hash=profile_rule.include_in_hash,
            set_like=profile_rule.set_like,
        ),
        "strictness": strictness,
        "schema_coverage": _schema_coverage(
            pipeline_name=pipeline_name,
            field_name=field_name,
            arrow_nullable=arrow_nullable,
        ),
        "dq_coverage": _dq_coverage(
            pipeline_name=pipeline_name,
            provider=provider,
            entity=entity,
            field_name=field_name,
            strictness=strictness,
        ),
        "notes": notes,
    }


def _augment_structured_payload_policy_notes(
    *,
    provider: str,
    entity: str,
    field_name: str,
    notes: str,
) -> str:
    """Append raw/canonical sidecar governance notes for semantic-sensitive JSON."""
    policy = structured_payload_policy(f"{provider}.{entity}", field_name)
    if policy is None:
        return notes

    semantics = policy.collection_semantics.value.replace("_", " ")
    if policy.requires_raw_sidecar_before_semantic_transform:
        governance_note = (
            f"Semantic-sensitive {semantics} payload: canonical JSON is not a raw "
            f"provider substitute; semantic transforms must materialize "
            f"{policy.raw_sidecar_field} and {policy.canonical_sidecar_field} before "
            f"replacing or deriving provider payload semantics."
        )
    else:
        governance_note = (
            f"Semantic-sensitive {semantics} payload: the persisted canonical JSON "
            f"field {policy.canonical_sidecar_field} is the ratified evidence surface; "
            f"future semantic transforms must not assume an implicit raw sidecar or "
            f"replace provider semantics without an explicit contract change."
        )
    if not notes:
        return governance_note
    return f"{notes} {governance_note}"


def _entity_fallback_row(
    *,
    provider: str,
    entity: str,
    pipeline_name: str,
    field_name: str,
    field_type: str,
    arrow_nullable: bool,
    source: str,
    normalizer: str,
    summary: str,
) -> dict[str, str]:
    """Build one entity matrix row sourced from fallback normalization policy."""
    controlled_vocabulary_source, strictness, semantic_category, policy_scope = (
        _row_policy_metadata(
            provider=provider,
            entity=entity,
            field_name=field_name,
            normalization_source=source,
            normalizer_name=normalizer,
            notes=summary,
        )
    )
    return {
        "provider": provider,
        "pipeline_name": pipeline_name,
        "pipeline_kind": ENTITY_PIPELINE_KIND,
        "entity": entity,
        "field_name": field_name,
        "field_type": field_type,
        "normalization_source": source,
        "normalizer": normalizer,
        "normalization_summary": summary,
        "controlled_vocabulary_source": controlled_vocabulary_source,
        "policy_scope": policy_scope,
        "semantic_category": semantic_category,
        "include_in_content_hash": "",
        "set_like": FALSE_TEXT,
        "hash_ordering": "fallback_policy",
        "strictness": strictness,
        "schema_coverage": _schema_coverage(
            pipeline_name=pipeline_name,
            field_name=field_name,
            arrow_nullable=arrow_nullable,
        ),
        "dq_coverage": _dq_coverage(
            pipeline_name=pipeline_name,
            provider=provider,
            entity=entity,
            field_name=field_name,
            strictness=strictness,
        ),
        "notes": "",
    }


def _iter_composite_fields(payload: dict[str, object]) -> list[str]:
    composite = payload.get("composite")
    if not isinstance(composite, dict):
        return []
    merge = composite.get("merge")
    if not isinstance(merge, dict):
        return []
    column_groups = merge.get("column_groups")
    if not isinstance(column_groups, list):
        return []

    ordered: list[str] = []
    seen: set[str] = set()
    for group in column_groups:
        if not isinstance(group, dict):
            continue
        fields = group.get("fields")
        if not isinstance(fields, list):
            continue
        for field_name in fields:
            if not isinstance(field_name, str) or field_name in seen:
                continue
            seen.add(field_name)
            ordered.append(field_name)
    return ordered


def _iter_composite_join_keys(payload: dict[str, object]) -> set[str]:
    composite = payload.get("composite")
    if not isinstance(composite, dict):
        return set()

    keys: set[str] = set()
    for entries in _composite_join_key_entry_lists(composite):
        keys.update(_join_keys_from_entries(entries))
    return keys


def _composite_join_key_entry_lists(composite: dict[str, object]) -> list[list[object]]:
    """Return composite dependency/enricher entry lists that may declare join keys."""
    entry_lists: list[list[object]] = []
    for key in ("dependencies", "enrichers"):
        value = composite.get(key)
        if isinstance(value, list):
            entry_lists.append(value)
    return entry_lists


def _join_keys_from_entries(entries: list[object]) -> set[str]:
    """Extract declared join keys from composite dependency-like entries."""
    keys: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        join_keys = entry.get("join_keys")
        if not isinstance(join_keys, list):
            continue
        keys.update(key for key in join_keys if isinstance(key, str))
    return keys


def _iter_composite_join_key_occurrences(payload: dict[str, object]) -> list[str]:
    return sorted(_iter_composite_join_keys(payload))


def _build_composite_rows_for_pipeline(
    *,
    pipeline_name: str,
    payload: dict[str, object],
) -> list[dict[str, str]]:
    join_keys = _iter_composite_join_keys(payload)
    rows: list[dict[str, str]] = []
    for field_name in _iter_composite_fields(payload):
        rows.append(_composite_row(pipeline_name, field_name, join_keys, payload))
    return rows


def _composite_row(
    pipeline_name: str,
    field_name: str,
    join_keys: set[str],
    payload: dict[str, object],
) -> dict[str, str]:
    """Build one composite matrix row."""
    source, normalizer, summary, notes = _composite_field_policy(field_name, join_keys)
    strictness = _strictness(
        field_name=field_name,
        normalization_source=source,
        normalizer_name=normalizer,
        notes=summary,
    )
    return {
        "provider": "composite",
        "pipeline_name": pipeline_name,
        "pipeline_kind": COMPOSITE_PIPELINE_KIND,
        "entity": pipeline_name.removeprefix("composite_"),
        "field_name": field_name,
        "field_type": _composite_inherited_field_type(
            pipeline_name=pipeline_name,
            field_name=field_name,
            payload=payload,
        ),
        "normalization_source": source,
        "normalizer": normalizer,
        "normalization_summary": summary,
        "controlled_vocabulary_source": "",
        "policy_scope": "not_applicable",
        "semantic_category": _semantic_category(
            provider="composite",
            entity=pipeline_name.removeprefix("composite_"),
            field_name=field_name,
            strictness=strictness,
        ),
        "include_in_content_hash": "",
        "set_like": FALSE_TEXT,
        "hash_ordering": "not_applicable",
        "strictness": strictness,
        "schema_coverage": _composite_schema_coverage(pipeline_name, field_name),
        "dq_coverage": "not_applicable",
        "notes": notes,
    }


def _composite_field_policy(
    field_name: str,
    join_keys: set[str],
) -> tuple[str, str, str, str]:
    """Resolve normalization semantics for one composite field."""
    policy = JOIN_KEY_NORMALIZATION_POLICIES.get(field_name)
    if field_name not in join_keys or policy is None:
        return (
            "upstream_inherited",
            NO_NORMALIZER,
            (
                "No composite-specific field normalizer is defined; field is inherited "
                "from already-normalized upstream records."
            ),
            "Composite normalization is key-oriented; non-key fields preserve upstream semantics.",
        )
    return (
        "composite_join_key_policy",
        "join_key_policy",
        _normalize_summary_from_policy(
            key=field_name,
            trim=policy.trim,
            lowercase=policy.lowercase,
        ),
        "Applied only while resolving and comparing composite join keys.",
    )


def build_field_matrix_rows() -> list[dict[str, str]]:
    """Build the complete field normalization matrix for all pipelines.

    NOSONAR - S3776: complexity 30 exceeds 15; extraction would obscure matrix generation logic
    """
    _ensure_chembl_policy_registry_initialized()
    rows: list[dict[str, str]] = []
    rows.extend(_entity_field_matrix_rows())
    rows.extend(_composite_field_matrix_rows())
    augmented_rows = [_augment_row_with_inventory_metadata(row) for row in rows]
    _validate_non_chembl_inventory_rows(augmented_rows)
    return augmented_rows


def _entity_field_matrix_rows() -> list[dict[str, str]]:
    """Build matrix rows for all shipped entity pipelines."""
    rows: list[dict[str, str]] = []
    for config_path in _entity_config_paths():
        pipeline_inputs = _entity_pipeline_inputs(config_path)
        if pipeline_inputs is None:
            continue
        pipeline_name, provider, entity, schema = pipeline_inputs
        rows.extend(
            _build_entity_rows_for_pipeline(
                pipeline_name=pipeline_name,
                provider=provider,
                entity=entity,
                schema=schema,
            )
        )
    return rows


def _entity_pipeline_inputs(
    config_path: Path,
) -> tuple[str, str, str, Any] | None:
    """Resolve matrix inputs for one entity pipeline config."""
    payload = _load_yaml(config_path)
    pipeline = payload.get("pipeline")
    if not isinstance(pipeline, dict):
        return None
    pipeline_name = str(pipeline.get("pipeline_name", "")).strip()
    if not pipeline_name:
        return None
    schema = ENTITY_SILVER_SCHEMA_REGISTRY.get(pipeline_name)
    if schema is None:
        raise ValueError(f"Missing Silver schema registry entry for {pipeline_name}")
    provider = str(payload.get("provider", "")).strip()
    entity = str(payload.get("entity", "")).strip()
    return pipeline_name, provider, entity, schema


def _composite_field_matrix_rows() -> list[dict[str, str]]:
    """Build matrix rows for all shipped composite pipelines."""
    rows: list[dict[str, str]] = []
    for config_path in _composite_config_paths():
        composite_inputs = _composite_pipeline_inputs(config_path)
        if composite_inputs is None:
            continue
        pipeline_name, payload = composite_inputs
        rows.extend(
            _build_composite_rows_for_pipeline(
                pipeline_name=pipeline_name,
                payload=payload,
            )
        )
    return rows


def _composite_pipeline_inputs(
    config_path: Path,
) -> tuple[str, dict[str, object]] | None:
    """Resolve matrix inputs for one composite pipeline config."""
    payload = _load_yaml(config_path)
    composite = payload.get("composite")
    if not isinstance(composite, dict):
        return None
    pipeline_name = str(composite.get("name", "")).strip()
    if not pipeline_name:
        return None
    return pipeline_name, payload



