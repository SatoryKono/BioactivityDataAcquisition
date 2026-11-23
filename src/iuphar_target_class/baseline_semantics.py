"""RF-001 semantic baseline for direct, local, and effective target classes.

The historical stage-1 policy stays unchanged. This module records the field
dictionary, the decision table, and the limits of standalone and composite
classification before any later rule change. Biological accuracy is not
accepted. Claims about original M semantics stay unbound until a manifest
entry carries that source's version id and SHA-256.
"""

from __future__ import annotations

from dataclasses import dataclass

from .policy import BASE_MISSING_MARKERS

BASELINE_ID = "iuphar-rf001-baseline-2026-11-23"
RECORDED_ON = "2026-11-23"
ISSUE = "https://github.com/SatoryKono/BioactivityDataAcquisition/issues/13309"
RULES_CONTRACT_VERSION = "iuphar-rules-rf001-1"
NORMALIZATION_CONTRACT_VERSION = "iuphar-normalization-rf001-1"
CLASSIFIER_CONTRACT_VERSION = "iuphar-classifier-rf001-1"
TABLE_CONTRACT_VERSION = "iuphar-table-rf001-1"
PROFILE_CHANGE_CONTRACT_VERSION = "iuphar-profile-change-rf001-1"
CANONICAL_OTHER = "Other Protein Target"
LEGACY_OTHER = "Other"
SNAPSHOT_ANNOTATION_CAPABILITY = "family_only"
COMMITTED_ENTITY_MODE = "off"
COMMITTED_ENTITY_CONTRACT = "3.0.0"
COMMITTED_TABLE_GENERATION = "V30"
COMMITTED_COMPOSITE_VERSION = "1.3.0"
MISSING_MARKERS_VERSION_STATUS = "не утверждено"

UNCERTAINTY_STATUSES: tuple[str, ...] = (
    "unknown",
    "partial",
    "ambiguous",
    "conflict",
)
AVAILABILITY_STATES: tuple[str, ...] = (
    "available",
    "source_unavailable",
    "not_found",
)
OTHER_LABELS = frozenset({CANONICAL_OTHER, LEGACY_OTHER})
_MISSING_CLASS_MARKERS = frozenset(marker.casefold() for marker in BASE_MISSING_MARKERS)


def _class_or_none(value: str | None) -> str | None:
    """Return a real class, or None for a missing-marker or blank value."""
    if value is None:
        return None
    stripped = value.strip()
    if stripped.casefold() in _MISSING_CLASS_MARKERS:
        return None
    return stripped


_DICTIONARY_PREFIX = "iuphar_"
_LOCAL_PREFIX = "local_"
_EFFECTIVE_PREFIX = "effective_"


@dataclass(frozen=True, slots=True)
class FieldDefinition:
    """One named field and the only layer allowed to write it."""

    name: str
    layer: str
    meaning: str


@dataclass(frozen=True, slots=True)
class DecisionRule:
    """One row of the RF-001 decision table. The first match is the outcome."""

    rule_id: str
    when: str
    decision_status: str
    effective_class: str
    effective_source: str
    completeness: str
    covers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProfileChangeRule:
    """A condition that requires a new profile version instead of an edit."""

    rule_id: str
    statement: str


@dataclass(frozen=True, slots=True)
class Capability:
    """What one surface may claim before and after dependency joins."""

    surface: str
    stage: str
    present_features: tuple[str, ...]
    unavailable_features: tuple[str, ...]
    classification_limit: str


@dataclass(frozen=True, slots=True)
class BoundaryObservation:
    """One semantic situation. The walker does not mutate it."""

    case_id: str
    layer_mix: bool = False
    distinct_row_count: int = 1
    distinct_key_total: bool = True
    assigned_label: str | None = None
    approved_other_mapping: bool = False
    legacy_field: bool = False
    parent_ids: tuple[str, ...] = ()
    retained_parent_ids: tuple[str, ...] = ()
    source_state: str = "available"
    uncertainty: str | None = None
    dictionary_class: str | None = None
    local_class: str | None = None
    local_status: str = "absent"

    def __post_init__(self) -> None:
        if not self.case_id.strip():
            raise ValueError("case_id is required")
        if self.distinct_row_count < 1:
            raise ValueError("distinct_row_count must be at least 1")
        if self.source_state not in AVAILABILITY_STATES:
            raise ValueError("source_state is outside the availability vocabulary")
        if (
            self.uncertainty is not None
            and self.uncertainty not in UNCERTAINTY_STATUSES
        ):
            raise ValueError("uncertainty is outside the uncertainty vocabulary")
        if self.local_status not in {
            "supported",
            "conflicting",
            "candidate_only",
            "absent",
        }:
            raise ValueError("local_status is outside the local vocabulary")
        object.__setattr__(
            self, "dictionary_class", _class_or_none(self.dictionary_class)
        )
        object.__setattr__(self, "local_class", _class_or_none(self.local_class))
        if self.local_status == "supported" and not self.local_class:
            raise ValueError("supported local requires local_class")


@dataclass(frozen=True, slots=True)
class BoundaryDecision:
    """The single outcome of the first matching decision row."""

    case_id: str
    rule_id: str
    decision_status: str
    effective_class: str | None
    effective_source: str | None
    iuphar_class: str | None
    local_class: str | None
    completeness: str
    codes: tuple[str, ...]
    dropped_parent_ids: tuple[str, ...] = ()
    invented_parent_ids: tuple[str, ...] = ()


FIELD_DEFINITIONS: tuple[FieldDefinition, ...] = (
    FieldDefinition(
        "target_type",
        "chembl_object_type",
        "Тип объекта ChEMBL. Не класс IUPHAR и не вывод local rules.",
    ),
    FieldDefinition(
        "iuphar_target_id",
        "dictionary",
        "Идентификатор мишени в справочнике. Локальный вывод сюда не пишется.",
    ),
    FieldDefinition(
        "iuphar_class",
        "dictionary",
        "Класс из утверждённого отображения type или family справочника.",
    ),
    FieldDefinition(
        "iuphar_match_status",
        "dictionary",
        "Статус поиска в справочнике. not_found только на полном источнике.",
    ),
    FieldDefinition(
        "iuphar_annotation_status",
        "dictionary",
        "Полнота аннотации справочника, а не статус локального правила.",
    ),
    FieldDefinition(
        "local_class",
        "local_rule",
        "Класс локальных правил. Это не факт справочника.",
    ),
    FieldDefinition(
        "effective_class",
        "decision",
        "Итоговый класс таблицы решений. Пустое значение допустимо.",
    ),
    FieldDefinition(
        "effective_source",
        "decision",
        "Слой источника итога: iuphar, local или пусто.",
    ),
    FieldDefinition(
        "decision_status",
        "decision",
        "Статус решения: resolved, requires_review, unresolved, contract_defect.",
    ),
    FieldDefinition(
        "target_class_profile_sha256",
        "profile_identity",
        "SHA-256 закреплённого профиля. Не класс и не источник класса.",
    ),
)

DECISION_RULES: tuple[DecisionRule, ...] = (
    DecisionRule(
        "layer_mix",
        "Локальный вывод записан в поле iuphar_*",
        "contract_defect",
        "null",
        "null",
        "conflict",
        ("conflict",),
    ),
    DecisionRule(
        "undefined_table_distinct",
        "Несколько различных строк схлопнуты без полного ключа, как Table.Distinct",
        "requires_review",
        "null",
        "null",
        "ambiguous",
        ("ambiguous",),
    ),
    DecisionRule(
        "source_unavailable_supported_local",
        "Источник недоступен, supported local сохраняется отдельно от iuphar_*",
        "requires_review",
        "local class",
        "local",
        "source_unavailable",
        ("source_unavailable",),
    ),
    DecisionRule(
        "source_unavailable",
        "Источник недоступен и supported local нет",
        "unresolved",
        "null",
        "null",
        "source_unavailable",
        ("source_unavailable",),
    ),
    DecisionRule(
        "confirmed_not_found_conflict",
        "Полный источник не содержит идентификатор, local конфликтует",
        "requires_review",
        "null",
        "null",
        "not_found",
        ("not_found",),
    ),
    DecisionRule(
        "confirmed_not_found_supported_local",
        "Полный источник не содержит идентификатор, supported local сохраняется",
        "resolved",
        "local class",
        "local",
        "not_found",
        ("not_found",),
    ),
    DecisionRule(
        "confirmed_not_found",
        "Полный источник не содержит идентификатор и supported local нет",
        "unresolved",
        "null",
        "null",
        "not_found",
        ("not_found",),
    ),
    DecisionRule(
        "dropped_parents",
        "Сохранённый путь теряет или подменяет хотя бы одного родителя",
        "requires_review",
        "null",
        "null",
        "partial",
        ("partial",),
    ),
    DecisionRule(
        "false_other",
        "Other или Other Protein Target без утверждённого отображения",
        "unresolved",
        "null",
        "null",
        "unknown",
        ("unknown",),
    ),
    DecisionRule(
        "legacy_other_alias",
        "Токен Other лежит в legacy-поле и есть утверждённое отображение",
        "resolved",
        CANONICAL_OTHER,
        "iuphar",
        "complete",
        (),
    ),
    DecisionRule(
        "admissible_other",
        "Утверждённое отображение даёт каноническую метку Other Protein Target",
        "resolved",
        CANONICAL_OTHER,
        "iuphar",
        "complete",
        (),
    ),
    DecisionRule(
        "unknown",
        "Класс не определён и подстановки нет",
        "unresolved",
        "null",
        "null",
        "unknown",
        ("unknown",),
    ),
    DecisionRule(
        "partial_annotation",
        "Аннотация справочника неполна, путь при этом не схлопнут",
        "requires_review",
        "dictionary class or null",
        "iuphar only when a dictionary class exists",
        "partial",
        ("partial",),
    ),
    DecisionRule(
        "ambiguous_match",
        "Несколько кандидатов остаются при заданном полном ключе",
        "requires_review",
        "null",
        "null",
        "ambiguous",
        ("ambiguous",),
    ),
    DecisionRule(
        "layer_conflict",
        "Справочник и local rules расходятся; оба значения сохраняются",
        "requires_review",
        "dictionary class or null",
        "iuphar only when a dictionary class exists",
        "conflict",
        ("conflict",),
    ),
    DecisionRule(
        "dictionary_resolved",
        "Есть факт справочника и нет неопределённости, конфликта или смешения",
        "resolved",
        "dictionary class",
        "iuphar",
        "complete",
        (),
    ),
)

PROFILE_CHANGE_RULES: tuple[ProfileChangeRule, ...] = (
    ProfileChangeRule(
        "immutable-baseline",
        "Manifest RF-001 не перезаписывается. Новая семантика публикует новый "
        "baseline id и новый manifest.",
    ),
    ProfileChangeRule(
        "version-bump",
        "Смена rules, normalization, classifier или table contract, байтов "
        "снимка, приёмки или схемы классификации требует новой версии профиля.",
    ),
    ProfileChangeRule(
        "digest-binds-bytes",
        "Digest профиля — SHA-256 точных байтов. Тот же digest для других "
        "байтов является дефектом контракта.",
    ),
    ProfileChangeRule(
        "mode-does-not-migrate",
        "mode off и shadow оставляют канонические таблицы на контракте 3.0.0. "
        "mode enrich выбирает 3.1.0 только для запуска с закреплённым профилем "
        "и не мигрирует канонические таблицы.",
    ),
    ProfileChangeRule(
        "recalculation-is-separate",
        "Кэш результата и пересчёт — разные роли. Пересчёт получает новый "
        "артефакт и новый SHA-256.",
    ),
    ProfileChangeRule(
        "m-claim-needs-version",
        "Утверждение о семантике M допустимо только с version_id и SHA-256 "
        "записи m_source. Непривязанный источник не поддерживает такое "
        "утверждение.",
    ),
    ProfileChangeRule(
        "missing-markers-stay-unapproved",
        "missing_markers_version остаётся пустой, пока нет отдельного "
        "утверждения. Смена набора маркеров повышает версию normalization.",
    ),
    ProfileChangeRule(
        "full-features-after-joins",
        "Полный набор признаков допустим только после dependency joins "
        "composite target. Standalone chembl_target эти признаки не заявляет.",
    ),
)

CAPABILITIES: tuple[Capability, ...] = (
    Capability(
        surface="chembl_target",
        stage="standalone_before_dependency_joins",
        present_features=(
            "target_id",
            "target_type",
            "pref_name",
            "organism",
            "taxonomy_id",
            "target_row_ec_numbers",
            "target_row_xrefs",
            "seed_component_id_lists",
        ),
        unavailable_features=(
            "uniprot_protein_record",
            "protein_class_l1_l5",
            "component_classifications_after_target_component",
        ),
        classification_limit=(
            "Класс, которому нужны признаки после joins, остаётся partial "
            "или insufficient_input. Зафиксированный mode — off, контракт "
            "3.0.0, канонические таблицы V30."
        ),
    ),
    Capability(
        surface="composite_target",
        stage="after_ordered_dependency_joins",
        present_features=(
            "seed_features",
            "target_component",
            "protein_class_hierarchy",
            "uniprot_accession_when_mapping_status_found",
            "uniprot_protein",
        ),
        unavailable_features=(
            "features_of_a_dependency_that_did_not_run",
            "features_absent_from_a_completed_dependency",
        ),
        classification_limit=(
            "Незапущенная зависимость даёт source_unavailable для своих "
            "признаков. Завершённая зависимость без строки даёт not_found "
            "для этого join. local_* по-прежнему не копируется в iuphar_*. "
            "Канонические таблицы остаются V30 до отдельной миграции."
        ),
    ),
)

PATH_POLICY: dict[str, str] = {
    "direction": "root_to_leaf",
    "member": "family_id",
    "display_separator": " → ",
    "multiple_parents": "retain_all",
    "collapse": "forbidden",
    "display_is_source_of_truth": "false",
}

LOCAL_INFERENCE_IN_IUPHAR = BoundaryObservation(
    case_id="local_inference_in_iuphar",
    layer_mix=True,
    dictionary_class="Enzyme",
    local_class="Enzyme",
)
DROPPED_PARENTS = BoundaryObservation(
    case_id="dropped_parents",
    parent_ids=("10", "20"),
    retained_parent_ids=("10",),
)
FALSE_OTHER = BoundaryObservation(
    case_id="false_other",
    assigned_label=LEGACY_OTHER,
    approved_other_mapping=False,
    uncertainty="unknown",
)
UNDEFINED_TABLE_DISTINCT = BoundaryObservation(
    case_id="undefined_table_distinct",
    distinct_row_count=2,
    distinct_key_total=False,
)


def field_layer(name: str) -> str:
    """Return the only layer that may write ``name``."""
    if name == "target_type":
        return "chembl_object_type"
    if name == "decision_status":
        return "decision"
    if name == "target_class_profile_sha256":
        return "profile_identity"
    if name.startswith(_DICTIONARY_PREFIX):
        return "dictionary"
    if name.startswith(_LOCAL_PREFIX):
        return "local_rule"
    if name.startswith(_EFFECTIVE_PREFIX):
        return "decision"
    raise ValueError(f"field has no RF-001 layer: {name}")


def covered_statuses() -> frozenset[str]:
    """Statuses named by the decision table, including availability."""
    found: set[str] = set()
    for rule in DECISION_RULES:
        found.update(rule.covers)
    return frozenset(found)


def decide(observation: BoundaryObservation) -> BoundaryDecision:
    """Apply the decision table. The first matching row is the outcome."""
    for rule in _WALKER:
        decision = rule(observation)
        if decision is not None:
            _reject_substituted_absence(decision)
            return decision
    raise RuntimeError("RF-001 decision table is not total")


def contract_document() -> dict[str, object]:
    """Return the deterministic RF-001 semantic document."""
    return {
        "artifact": "iuphar_rf001_baseline_semantics",
        "baseline_id": BASELINE_ID,
        "biological_accuracy_accepted": False,
        "capabilities": [_capability_payload(item) for item in CAPABILITIES],
        "configuration": {
            "composite_version": COMMITTED_COMPOSITE_VERSION,
            "entity_contract": COMMITTED_ENTITY_CONTRACT,
            "entity_mode": COMMITTED_ENTITY_MODE,
            "table_generation": COMMITTED_TABLE_GENERATION,
        },
        "contract_versions": {
            "classifier": CLASSIFIER_CONTRACT_VERSION,
            "normalization": NORMALIZATION_CONTRACT_VERSION,
            "profile_change": PROFILE_CHANGE_CONTRACT_VERSION,
            "rules": RULES_CONTRACT_VERSION,
            "table": TABLE_CONTRACT_VERSION,
        },
        "decision_table": [_rule_payload(rule) for rule in DECISION_RULES],
        "field_dictionary": [_field_payload(item) for item in FIELD_DEFINITIONS],
        "issue": ISSUE,
        "legacy_other": {
            "admissible_when": (
                "Токен Other хранится в legacy-поле, а утверждённое "
                "отображение той же строки даёт Other Protein Target."
            ),
            "canonical_label": CANONICAL_OTHER,
            "forbidden_as_fill_in_for": [
                *UNCERTAINTY_STATUSES,
                "source_unavailable",
                "not_found",
            ],
            "legacy_token": LEGACY_OTHER,
        },
        "m_semantics_bound": False,
        "missing_markers": {
            "base": list(BASE_MISSING_MARKERS),
            "does_not_mean": ["not_found", CANONICAL_OTHER, LEGACY_OTHER],
            "effect": "absence",
            "null_is_marker": True,
            "version": None,
            "version_status": MISSING_MARKERS_VERSION_STATUS,
            "whitespace_only_is_marker": True,
        },
        "path_policy": dict(PATH_POLICY),
        "profile_change_rules": [
            {"rule_id": rule.rule_id, "statement": rule.statement}
            for rule in PROFILE_CHANGE_RULES
        ],
        "recorded_on": RECORDED_ON,
        "snapshot_annotation_capability": SNAPSHOT_ANNOTATION_CAPABILITY,
    }


def _field_payload(item: FieldDefinition) -> dict[str, str]:
    return {"layer": item.layer, "meaning": item.meaning, "name": item.name}


def _rule_payload(rule: DecisionRule) -> dict[str, object]:
    return {
        "completeness": rule.completeness,
        "covers": list(rule.covers),
        "decision_status": rule.decision_status,
        "effective_class": rule.effective_class,
        "effective_source": rule.effective_source,
        "rule_id": rule.rule_id,
        "when": rule.when,
    }


def _capability_payload(item: Capability) -> dict[str, object]:
    return {
        "classification_limit": item.classification_limit,
        "present_features": list(item.present_features),
        "stage": item.stage,
        "surface": item.surface,
        "unavailable_features": list(item.unavailable_features),
    }


def _decision(
    observation: BoundaryObservation,
    *,
    rule_id: str,
    decision_status: str,
    effective_class: str | None,
    effective_source: str | None,
    iuphar_class: str | None,
    completeness: str,
    codes: tuple[str, ...],
    dropped_parent_ids: tuple[str, ...] = (),
    invented_parent_ids: tuple[str, ...] = (),
) -> BoundaryDecision:
    return BoundaryDecision(
        case_id=observation.case_id,
        rule_id=rule_id,
        decision_status=decision_status,
        effective_class=effective_class,
        effective_source=effective_source,
        iuphar_class=iuphar_class,
        local_class=observation.local_class,
        completeness=completeness,
        codes=codes,
        dropped_parent_ids=dropped_parent_ids,
        invented_parent_ids=invented_parent_ids,
    )


def _layer_mix(observation: BoundaryObservation) -> BoundaryDecision | None:
    if not observation.layer_mix:
        return None
    return _decision(
        observation,
        rule_id="layer_mix",
        decision_status="contract_defect",
        effective_class=None,
        effective_source=None,
        iuphar_class=None,
        completeness="conflict",
        codes=("layer_mix",),
    )


def _undefined_distinct(observation: BoundaryObservation) -> BoundaryDecision | None:
    unordered = (
        observation.distinct_row_count > 1 and not observation.distinct_key_total
    )
    if not unordered:
        return None
    return _decision(
        observation,
        rule_id="undefined_table_distinct",
        decision_status="requires_review",
        effective_class=None,
        effective_source=None,
        iuphar_class=None,
        completeness="ambiguous",
        codes=("undefined_table_distinct",),
    )


def _supported_local(observation: BoundaryObservation) -> bool:
    return observation.local_status == "supported" and bool(observation.local_class)


def _publishable_local_class(observation: BoundaryObservation) -> bool:
    """A supported local class may fill a gap only when it is not an Other label."""
    return _supported_local(observation) and observation.local_class not in OTHER_LABELS


def _unapproved_local_other(
    observation: BoundaryObservation, *, completeness: str, code: str
) -> BoundaryDecision | None:
    """Keep a dictionary gap from publishing an unapproved Other via local rules."""
    label = observation.local_class
    if label not in OTHER_LABELS or not _supported_local(observation):
        return None
    approved = observation.approved_other_mapping and not (
        label == LEGACY_OTHER and not observation.legacy_field
    )
    if approved:
        return None
    return _decision(
        observation,
        rule_id="false_other",
        decision_status="unresolved",
        effective_class=None,
        effective_source=None,
        iuphar_class=None,
        completeness=completeness,
        codes=("false_other", code),
    )


def _source_unavailable(observation: BoundaryObservation) -> BoundaryDecision | None:
    if observation.source_state != "source_unavailable":
        return None
    rejected = _unapproved_local_other(
        observation, completeness="source_unavailable", code="source_unavailable"
    )
    if rejected is not None:
        return rejected
    if _publishable_local_class(observation):
        return _decision(
            observation,
            rule_id="source_unavailable_supported_local",
            decision_status="requires_review",
            effective_class=observation.local_class,
            effective_source="local",
            iuphar_class=None,
            completeness="source_unavailable",
            codes=("source_unavailable",),
        )
    return _decision(
        observation,
        rule_id="source_unavailable",
        decision_status="unresolved",
        effective_class=None,
        effective_source=None,
        iuphar_class=None,
        completeness="source_unavailable",
        codes=("source_unavailable",),
    )


def _confirmed_not_found(observation: BoundaryObservation) -> BoundaryDecision | None:
    if observation.source_state != "not_found":
        return None
    if observation.local_status == "conflicting":
        return _decision(
            observation,
            rule_id="confirmed_not_found_conflict",
            decision_status="requires_review",
            effective_class=None,
            effective_source=None,
            iuphar_class=None,
            completeness="not_found",
            codes=("confirmed_not_found",),
        )
    rejected = _unapproved_local_other(
        observation, completeness="not_found", code="confirmed_not_found"
    )
    if rejected is not None:
        return rejected
    if _publishable_local_class(observation):
        return _decision(
            observation,
            rule_id="confirmed_not_found_supported_local",
            decision_status="resolved",
            effective_class=observation.local_class,
            effective_source="local",
            iuphar_class=None,
            completeness="not_found",
            codes=("confirmed_not_found",),
        )
    return _decision(
        observation,
        rule_id="confirmed_not_found",
        decision_status="unresolved",
        effective_class=None,
        effective_source=None,
        iuphar_class=None,
        completeness="not_found",
        codes=("confirmed_not_found",),
    )


def _other_label(observation: BoundaryObservation) -> str | None:
    if observation.assigned_label in OTHER_LABELS:
        return observation.assigned_label
    if observation.dictionary_class in OTHER_LABELS:
        return observation.dictionary_class
    return None


def _other_decision(observation: BoundaryObservation) -> BoundaryDecision | None:
    label = _other_label(observation)
    if label is None:
        return None
    resolving = observation.approved_other_mapping and not (
        label == LEGACY_OTHER and not observation.legacy_field
    )
    if observation.uncertainty is not None and resolving:
        return None
    if not observation.approved_other_mapping or (
        label == LEGACY_OTHER and not observation.legacy_field
    ):
        return _decision(
            observation,
            rule_id="false_other",
            decision_status="unresolved",
            effective_class=None,
            effective_source=None,
            iuphar_class=None,
            completeness="unknown",
            codes=("false_other",),
        )
    if label == LEGACY_OTHER:
        return _decision(
            observation,
            rule_id="legacy_other_alias",
            decision_status="resolved",
            effective_class=CANONICAL_OTHER,
            effective_source="iuphar",
            iuphar_class=CANONICAL_OTHER,
            completeness="complete",
            codes=("legacy_other_alias",),
        )
    return _decision(
        observation,
        rule_id="admissible_other",
        decision_status="resolved",
        effective_class=CANONICAL_OTHER,
        effective_source="iuphar",
        iuphar_class=CANONICAL_OTHER,
        completeness="complete",
        codes=("admissible_other",),
    )


def _dropped_parents(observation: BoundaryObservation) -> BoundaryDecision | None:
    parents = set(observation.parent_ids)
    retained = set(observation.retained_parent_ids)
    if parents == retained:
        return None
    return _decision(
        observation,
        rule_id="dropped_parents",
        decision_status="requires_review",
        effective_class=None,
        effective_source=None,
        iuphar_class=None,
        completeness="partial",
        codes=("dropped_parent",),
        dropped_parent_ids=tuple(sorted(parents - retained)),
        invented_parent_ids=tuple(sorted(retained - parents)),
    )


def _uncertainty(observation: BoundaryObservation) -> BoundaryDecision | None:
    status = observation.uncertainty
    if status is None:
        return None
    if status == "partial":
        return _dictionary_or_null(
            observation,
            rule_id="partial_annotation",
            completeness="partial",
            codes=("partial_annotation",),
        )
    if status == "ambiguous":
        return _decision(
            observation,
            rule_id="ambiguous_match",
            decision_status="requires_review",
            effective_class=None,
            effective_source=None,
            iuphar_class=None,
            completeness="ambiguous",
            codes=("ambiguous_match",),
        )
    if status == "conflict":
        return _dictionary_or_null(
            observation,
            rule_id="layer_conflict",
            completeness="conflict",
            codes=("conflict",),
        )
    return _decision(
        observation,
        rule_id="unknown",
        decision_status="unresolved",
        effective_class=None,
        effective_source=None,
        iuphar_class=None,
        completeness="unknown",
        codes=("unknown",),
    )


def _admitted_dictionary_class(observation: BoundaryObservation) -> str | None:
    """Keep a real dictionary fact, including an approved canonical Other."""
    label = observation.dictionary_class
    if label not in OTHER_LABELS:
        return label
    admitted = observation.approved_other_mapping and not (
        label == LEGACY_OTHER and not observation.legacy_field
    )
    if not admitted:
        return None
    return CANONICAL_OTHER


def _dictionary_or_null(
    observation: BoundaryObservation,
    *,
    rule_id: str,
    completeness: str,
    codes: tuple[str, ...],
) -> BoundaryDecision:
    dictionary_class = _admitted_dictionary_class(observation)
    return _decision(
        observation,
        rule_id=rule_id,
        decision_status="requires_review",
        effective_class=dictionary_class,
        effective_source="iuphar" if dictionary_class else None,
        iuphar_class=dictionary_class,
        completeness=completeness,
        codes=codes,
    )


def _layers_disagree(observation: BoundaryObservation) -> bool:
    if observation.dictionary_class is None:
        return False
    if observation.local_status == "conflicting":
        return True
    return (
        observation.local_status == "supported"
        and observation.local_class != observation.dictionary_class
    )


def _layer_disagreement(observation: BoundaryObservation) -> BoundaryDecision | None:
    """Keep the dictionary fact, but do not call a disagreeing local layer resolved."""
    if not _layers_disagree(observation):
        return None
    return _dictionary_or_null(
        observation,
        rule_id="layer_conflict",
        completeness="conflict",
        codes=("layer_conflict",),
    )


def _dictionary_resolved(observation: BoundaryObservation) -> BoundaryDecision | None:
    if observation.dictionary_class is None:
        return None
    return _decision(
        observation,
        rule_id="dictionary_resolved",
        decision_status="resolved",
        effective_class=observation.dictionary_class,
        effective_source="iuphar",
        iuphar_class=observation.dictionary_class,
        completeness="complete",
        codes=("dictionary_resolved",),
    )


def _otherwise_unknown(observation: BoundaryObservation) -> BoundaryDecision | None:
    return _decision(
        observation,
        rule_id="unknown",
        decision_status="unresolved",
        effective_class=None,
        effective_source=None,
        iuphar_class=None,
        completeness="unknown",
        codes=("unknown",),
    )


def _reject_substituted_absence(decision: BoundaryDecision) -> None:
    if decision.completeness == "source_unavailable" and "not_found" in decision.codes:
        raise RuntimeError("source_unavailable must not be rewritten as not_found")
    if decision.completeness == "not_found" and "source_unavailable" in decision.codes:
        raise RuntimeError("confirmed not_found must not be rewritten as unavailable")
    if decision.effective_source == "iuphar" and decision.iuphar_class is None:
        raise RuntimeError("iuphar source requires a dictionary class")
    if decision.effective_source == "local" and decision.local_class is None:
        raise RuntimeError("local source requires a local class")


_WALKER = (
    _layer_mix,
    _undefined_distinct,
    _source_unavailable,
    _confirmed_not_found,
    _dropped_parents,
    _other_decision,
    _uncertainty,
    _layer_disagreement,
    _dictionary_resolved,
    _otherwise_unknown,
)


__all__ = [
    "AVAILABILITY_STATES",
    "BASELINE_ID",
    "CANONICAL_OTHER",
    "CAPABILITIES",
    "CLASSIFIER_CONTRACT_VERSION",
    "COMMITTED_COMPOSITE_VERSION",
    "COMMITTED_ENTITY_CONTRACT",
    "COMMITTED_ENTITY_MODE",
    "COMMITTED_TABLE_GENERATION",
    "DECISION_RULES",
    "DROPPED_PARENTS",
    "FALSE_OTHER",
    "FIELD_DEFINITIONS",
    "ISSUE",
    "LEGACY_OTHER",
    "LOCAL_INFERENCE_IN_IUPHAR",
    "NORMALIZATION_CONTRACT_VERSION",
    "PATH_POLICY",
    "PROFILE_CHANGE_CONTRACT_VERSION",
    "PROFILE_CHANGE_RULES",
    "RECORDED_ON",
    "RULES_CONTRACT_VERSION",
    "SNAPSHOT_ANNOTATION_CAPABILITY",
    "TABLE_CONTRACT_VERSION",
    "UNCERTAINTY_STATUSES",
    "UNDEFINED_TABLE_DISTINCT",
    "BoundaryDecision",
    "BoundaryObservation",
    "contract_document",
    "covered_statuses",
    "decide",
    "field_layer",
]
