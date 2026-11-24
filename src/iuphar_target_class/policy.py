"""Stage-1 policy: class dictionary, comparison rule, and recorded limits.

Direct class mappings, graph limits and the HTTP adapter configuration were
recorded on 2026-11-15. Biological accuracy is not yet accepted. Unapproved
plan parameters stay null. EC, L1, and L2 rules stay on the local layer.

RF-001 (#13309) embeds the field-layer / status / capability semantics contract
without changing biological acceptance or rewriting historical artifacts.

RF-002 (#13310) embeds the UniProt identifier-role / matching-policy contract
(primary vs auxiliary xref) without relaxing trusted-anchor conflicts.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .gtopdb_2026_3_1 import (
    APPROVED_ON,
    ARCHIVE_SHA256,
    ARCHIVE_URL,
    RELEASE,
    RELEASE_DATE,
    SPECIES_TAXON_IDS,
    SQL_SHA256,
    TARGETS_CSV_SHA256,
    TARGETS_CSV_URL,
    TYPE_SUBCLASS_PAIRS,
)
from .identifier_roles import identifier_roles_document
from .iuphar_mapping import approved_class_mappings
from .semantics import semantics_document
from .stage0.io import atomic_write_bytes, canonical_json_bytes, sha256_bytes

WORKING_CLASSES: tuple[str, ...] = (
    "Receptor",
    "Ion Channel",
    "Enzyme",
    "Transporter",
    "Other Protein Target",
)
PLAN_SOURCE = "план v1 r9 §2.1"
PLAN_SECTION_5 = "план v1 r9 §5"
DOCUMENTARY_STATUS = "подтверждено документально"
# RF-005 (#13313): subclass dictionary + multi-parent path persistence.
PLAN_VERSION = "plan-v1-r9"
LOCAL_RULE_CATALOG_VERSION = "iuphar-local-rules-20261123"
BASE_MISSING_MARKERS: tuple[str, ...] = (
    "#n/a",
    "N/A",
    "n/a",
    "",
)
EC_CATEGORIES: tuple[tuple[int, str], ...] = (
    (1, "Oxidoreductases"),
    (2, "Transferases"),
    (3, "Hydrolases"),
    (4, "Lyases"),
    (5, "Isomerases"),
    (6, "Ligases"),
    (7, "Translocases"),
)
EC_SINGULAR: tuple[tuple[int, str], ...] = (
    (1, "Oxidoreductase"),
    (2, "Transferase"),
    (3, "Hydrolase"),
    (4, "Lyase"),
    (5, "Isomerase"),
    (6, "Ligase"),
    (7, "Translocase"),
)
# EC 7 is recorded as Translocase and does not become an IUPHAR class.
EC_WORKING_CLASS: dict[int, str | None] = {
    1: "Enzyme",
    2: "Enzyme",
    3: "Enzyme",
    4: "Enzyme",
    5: "Enzyme",
    6: "Enzyme",
    7: None,
}
LOCAL_CATALOG_VERSION = "local-rules-2026.11.23"
CLASS_PRIORITY = 100
EXCLUDED_NHR_KEYWORDS: tuple[str, ...] = ("KW-0804", "KW-0805", "KW-0863")
_FORBIDDEN_CLASS_OUTPUTS = frozenset(
    {"multifunctional", "multifunctional target", "nuclear hormone receptor"}
)
_CONTROLLED_ANNOTATIONS: tuple[tuple[str, str, str, str], ...] = (
    ("KW-0378", "Hydrolase", "Enzyme", "UniProt KW-0378 Hydrolase"),
    (
        "KW-0418",
        "Kinase",
        "Enzyme",
        "UniProt KW-0418 Kinase; не подстрока свободного текста",
    ),
    (
        "KW-0675",
        "Receptor",
        "Receptor",
        "UniProt KW-0675 Receptor; не zinc finger и не transcription",
    ),
    ("KW-0808", "Transferase", "Enzyme", "UniProt KW-0808 Transferase"),
)
UNSET = "не утверждено"
VOLUME_TEST_SECONDS = 300
VOLUME_TEST_TIME_STATUS = "утверждено"
APPROVED = "утверждено"
NOT_RUN = "NOT_RUN"
GRAPH_MAX_DEPTH = 8
GRAPH_MAX_VISITED_NODES = 128
ROLE_ASSIGNMENT = (
    "владелец результата — Федор Новиков; исполнитель модуля и "
    "проверяющий эталонов — Cursor, назначение владельца 2026-11-11"
)


@dataclass(frozen=True, slots=True)
class RuleRecord:
    """One versioned rule. Broken records block processing."""

    rule_id: str
    family: str
    input_conditions: str
    output: str
    justification_source: str
    version: str
    limits: str
    marks_direct_layer: bool
    priority: int = CLASS_PRIORITY


@dataclass(frozen=True, slots=True)
class ClassAssignment:
    """Direct-layer class from an approved type or family mapping only."""

    iuphar_class: str | None
    status: str
    proof: str | None
    candidates: tuple[str, ...]
    rule_id: str | None


def class_rules() -> tuple[RuleRecord, ...]:
    """Five working classes. Each cites the plan and a non-guessing rule."""
    rules: list[RuleRecord] = []
    for name in WORKING_CLASSES:
        rules.append(
            RuleRecord(
                rule_id=f"class:{name}",
                family="dictionary",
                input_conditions=(
                    "утверждённое отображение type или family ID выбранного "
                    f"выпуска даёт {name}"
                ),
                output=name,
                justification_source=PLAN_SOURCE,
                version=PLAN_VERSION,
                limits=(
                    "проектная группировка, не схема API; без утверждённого "
                    "отображения класс не присваивается"
                ),
                marks_direct_layer=False,
            ),
        )
    return tuple(rules)


def _local_rule(
    rule_id: str,
    family: str,
    conditions: str,
    output: str,
    justification: str,
    limits: str,
    *,
    priority: int = CLASS_PRIORITY,
) -> RuleRecord:
    return RuleRecord(
        rule_id=rule_id,
        family=family,
        input_conditions=conditions,
        output=output,
        justification_source=justification,
        version=LOCAL_CATALOG_VERSION,
        limits=limits,
        marks_direct_layer=False,
        priority=priority,
    )


def _ec_names_align() -> None:
    singular = dict(EC_SINGULAR)
    for number, plural in EC_CATEGORIES:
        if plural != singular[number] + "s":
            message = f"EC {number} singular and plural names disagree"
            raise ValueError(message)
        if number not in EC_WORKING_CLASS:
            message = f"EC {number} has no fixed class mapping"
            raise ValueError(message)


def local_rules() -> tuple[RuleRecord, ...]:
    """Versioned local catalog. None of these rules write the direct layer.

    EC 1–6 map to Enzyme. EC 7 stays the IUBMB category Translocases and does
    not assign Transporter. Equal class priorities do not break a tie.
    """
    _ec_names_align()
    rules: list[RuleRecord] = []
    for number, plural in EC_CATEGORIES:
        singular = dict(EC_SINGULAR)[number]
        rules.append(
            _local_rule(
                f"ec:{number}",
                "ec",
                f"ec_category={number}",
                plural,
                "план v1 r8 шаг D; справочник IUBMB",
                (
                    f"категория {singular} / {plural}, не идентификатор и не "
                    "класс IUPHAR; EC 7 не становится Transporter; слой local"
                ),
                priority=0,
            )
        )
    for number, class_name in EC_WORKING_CLASS.items():
        if class_name is None:
            continue
        singular = dict(EC_SINGULAR)[number]
        rules.append(
            _local_rule(
                f"ec-class:{number}",
                "ec_class",
                f"ec_category={number}",
                class_name,
                (
                    f"IUBMB EC {number} {singular} входит в рабочий класс "
                    f"{class_name}; несколько номеров этой категории не "
                    "создают Multifunctional"
                ),
                (
                    "не пишет iuphar_*; не выбирает первую строку; "
                    "равный приоритет с другим классом оставляет конфликт"
                ),
            )
        )
    for keyword_id, _name, class_name, basis in _CONTROLLED_ANNOTATIONS:
        rules.append(
            _local_rule(
                f"annotation:{keyword_id}",
                "annotation",
                f"keyword_id={keyword_id}",
                class_name,
                basis,
                (
                    "только точный идентификатор; свободный текст, zinc finger "
                    "и transcription factor класс не назначают"
                ),
            )
        )
    rules.extend(
        (
            _local_rule(
                "predicted-l1-l2-unknown",
                "l1_l2",
                "provenance missing",
                "candidate_only",
                "происхождение не подтверждено свидетельством и не берётся из константы True",
                "не независимое подтверждение и не direct-слой",
                priority=0,
            ),
            _local_rule(
                "predicted-l1-l2-iuphar-derived",
                "l1_l2",
                "relation=iuphar",
                "dependent_not_confirmation",
                "предсказание, выведенное из IUPHAR, не подтверждает IUPHAR повторно",
                "не независимое свидетельство direct-слоя",
                priority=0,
            ),
            _local_rule(
                "predicted-l1-l2-independent",
                "l1_l2",
                "provenance present and relation=independent",
                "predicted working class",
                "независимость допустима только при явном relation=independent и непустом provenance",
                "значение True без такого свидетельства не принимается",
            ),
            _local_rule(
                "free-text",
                "free_text",
                "свободный текст, подстроки kinase/channel/zinc finger/transcription factor",
                "кандидат ручного разбора",
                "план v1 r8 шаг D",
                "класс автоматически не определяется",
                priority=0,
            ),
            _local_rule(
                "rejected:tf-zinc-finger-nhr",
                "rejected",
                "keyword KW-0863 or KW-0804 or KW-0805 or free text zinc finger/transcription factor",
                "not_assigned",
                "нет специфического основания назначать nuclear hormone receptor",
                "правило не применяется; TF и zinc finger не становятся nuclear hormone receptor",
                priority=0,
            ),
        )
    )
    return tuple(rules)


def local_rules_catalog_sha256() -> str:
    """Hash the catalog payload. The hash does not include itself."""
    payload = [_rule_payload(rule) for rule in local_rules()]
    return sha256_bytes(canonical_json_bytes(payload))


def local_evidence_content(ref: str, rule_ids: tuple[str, ...]) -> str:
    """Bind one local witness to its own rule ids and the catalog hash."""
    rules = ",".join(sorted(rule_ids))
    digest = local_rules_catalog_sha256()
    return (
        f"{ref}; rules={rules}; catalog={LOCAL_CATALOG_VERSION}; "
        f"catalog_sha256={digest}"
    )


def all_rules() -> tuple[RuleRecord, ...]:
    """Dictionary rules followed by local rules."""
    return class_rules() + local_rules()


_REQUIRED_RULE_FIELDS = (
    "rule_id",
    "family",
    "input_conditions",
    "output",
    "justification_source",
    "version",
    "limits",
)
_LOCAL_FAMILIES = frozenset(
    {"ec", "ec_class", "annotation", "l1_l2", "l2", "free_text", "rejected"}
)


def validate_rules(rules: tuple[RuleRecord, ...]) -> None:
    """Reject a rule config that omits a field or marks EC/L1/L2 as direct."""
    for rule in rules:
        _reject_incomplete_rule(rule)
        _reject_direct_local_rule(rule)
        _reject_dictionary_output(rule)
        _reject_negative_priority(rule)
        _reject_forbidden_output(rule)
        _reject_ec7_transporter(rule)
        _reject_excluded_nhr_annotation(rule)


def _reject_incomplete_rule(rule: RuleRecord) -> None:
    for field_name in _REQUIRED_RULE_FIELDS:
        if not getattr(rule, field_name):
            message = f"rule {rule.rule_id} missing {field_name}"
            raise ValueError(message)


def _reject_direct_local_rule(rule: RuleRecord) -> None:
    if rule.family in _LOCAL_FAMILIES and rule.marks_direct_layer:
        message = f"rule {rule.rule_id} must not be marked direct"
        raise ValueError(message)


def _reject_dictionary_output(rule: RuleRecord) -> None:
    if rule.family == "dictionary" and rule.output not in WORKING_CLASSES:
        message = f"rule {rule.rule_id} output is outside the class dictionary"
        raise ValueError(message)


def _reject_negative_priority(rule: RuleRecord) -> None:
    if rule.priority < 0:
        message = f"rule {rule.rule_id} priority must not be negative"
        raise ValueError(message)


def _reject_forbidden_output(rule: RuleRecord) -> None:
    if rule.output.casefold() in _FORBIDDEN_CLASS_OUTPUTS:
        message = (
            f"rule {rule.rule_id} must not assign {rule.output}; "
            "Multifunctional and nuclear hormone receptor are not inferred"
        )
        raise ValueError(message)


def _reject_ec7_transporter(rule: RuleRecord) -> None:
    if rule.family == "ec_class" and rule.input_conditions == "ec_category=7":
        message = (
            f"rule {rule.rule_id} must not map EC 7 to a working class; "
            "EC 7 stays the Translocases observation"
        )
        raise ValueError(message)


def _reject_excluded_nhr_annotation(rule: RuleRecord) -> None:
    if rule.family == "annotation" and any(
        rule.input_conditions == f"keyword_id={keyword_id}"
        for keyword_id in EXCLUDED_NHR_KEYWORDS
    ):
        message = (
            f"rule {rule.rule_id} must not map a transcription factor or "
            "zinc finger keyword to a class"
        )
        raise ValueError(message)


def assign_mapped_class(
    *,
    type_name: str | None,
    family_ids: tuple[str, ...],
    type_to_class: Mapping[str, str],
    family_to_class: Mapping[str, str],
    name: str | None = None,
    path_text: str | None = None,
) -> ClassAssignment:
    """Assign a class only from an approved type or family mapping.

    ``name`` and ``path_text`` are accepted so a class word in them cannot
    become the result. They are not read as evidence.
    """
    del name, path_text
    _reject_foreign_targets(type_to_class)
    _reject_foreign_targets(family_to_class)
    family_classes = tuple(
        family_to_class[family_id]
        for family_id in sorted(family_ids)
        if family_id in family_to_class
    )
    distinct = tuple(sorted(set(family_classes)))
    if len(distinct) > 1:
        return ClassAssignment(
            iuphar_class=None,
            status="conflicting",
            proof=None,
            candidates=family_classes,
            rule_id=None,
        )
    if type_name and type_name in type_to_class:
        mapped = type_to_class[type_name]
        return ClassAssignment(
            iuphar_class=mapped,
            status="available",
            proof="type",
            candidates=(mapped,),
            rule_id=f"class:{mapped}",
        )
    if len(distinct) == 1:
        mapped = distinct[0]
        return ClassAssignment(
            iuphar_class=mapped,
            status="partial",
            proof="family_mapping",
            candidates=family_classes,
            rule_id=f"class:{mapped}",
        )
    return ClassAssignment(
        iuphar_class=None,
        status="unmapped_type",
        proof=None,
        candidates=(),
        rule_id=None,
    )


def compare_subclasses(
    *,
    direct_subclass: str | None,
    local_subclass: str | None,
    direct_vocabulary: frozenset[str],
    local_vocabulary: frozenset[str],
    same_pairs: frozenset[tuple[str, str]],
    class_subclass_pairs: frozenset[tuple[str, str]],
) -> str:
    """Return same, class_subclass, incompatible, or contract_defect.

    A subclass outside its own vocabulary is a contract defect. A subclass
    with no link to the other layer is incompatible.
    """
    if direct_subclass is not None and direct_subclass not in direct_vocabulary:
        return "contract_defect"
    if local_subclass is not None and local_subclass not in local_vocabulary:
        return "contract_defect"
    if direct_subclass is None or local_subclass is None:
        return "empty"
    pair = (direct_subclass, local_subclass)
    if direct_subclass == local_subclass or pair in same_pairs:
        return "same"
    if pair in class_subclass_pairs:
        return "class_subclass"
    return "incompatible"


def direct_mapping_document() -> dict[str, object]:
    """Serialize the approved release-specific rules and input provenance."""
    types, families = approved_class_mappings(RELEASE)
    source = f"GtoPdb {RELEASE}; {TARGETS_CSV_URL}; {ARCHIVE_URL}"
    types_by_class: list[dict[str, object]] = []
    families_by_class: list[dict[str, object]] = []
    for name in sorted(WORKING_CLASSES):
        groups = (
            (
                "iuphar_type",
                "source_types",
                sorted(k for k, v in types.items() if v == name),
            ),
            (
                "iuphar_family",
                "family_ids",
                sorted((k for k, v in families.items() if v == name), key=int),
            ),
        )
        for family, field, values in groups:
            rule = RuleRecord(
                rule_id=f"{family}:{name}",
                family=family,
                input_conditions=f"совпадение с явным значением из {field}",
                output=name,
                justification_source=source,
                version=RELEASE,
                limits=(
                    "только выпуск и явно перечисленные значения; "
                    "не по названию, пути или типу предка"
                ),
                marks_direct_layer=True,
            )
            validate_rules((rule,))
            payload = _rule_payload(rule)
            payload[field] = values
            if family == "iuphar_type":
                types_by_class.append(payload)
            else:
                families_by_class.append(payload)
    return {
        "approved_on": APPROVED_ON,
        "families": families_by_class,
        "graph_only_type": "grouping",
        "provenance": {
            "archive_sha256": ARCHIVE_SHA256,
            "archive_url": ARCHIVE_URL,
            "attribution": "IUPHAR/BPS Guide to PHARMACOLOGY",
            "contents_license": "https://creativecommons.org/licenses/by-sa/4.0/",
            "database_license": "https://opendatacommons.org/licenses/odbl/1-0/",
            "license_scope": "provider-derived family/target records only",
            "release_date": RELEASE_DATE,
            "source_homepage": "https://www.guidetopharmacology.org/",
            "sql_sha256": SQL_SHA256,
            "targets_csv_sha256": TARGETS_CSV_SHA256,
            "targets_csv_url": TARGETS_CSV_URL,
        },
        "release": RELEASE,
        "snapshot_completeness_certified": False,
        "types": types_by_class,
    }


def policy_document() -> dict[str, object]:
    """Canonical stage-1 policy. Unset plan parameters stay null."""
    validate_rules(all_rules())
    return {
        "api_contract": {
            "documentary": [
                {
                    "as_of": "2026-11-09",
                    "item": "api_key_required",
                    "note": "не проверенный контракт сервиса",
                    "source": PLAN_SECTION_5,
                    "status": DOCUMENTARY_STATUS,
                },
                {
                    "as_of": "2026-11-09",
                    "item": "header_GTP-API-Key",
                    "note": "не проверенный контракт сервиса",
                    "source": PLAN_SECTION_5,
                    "status": DOCUMENTARY_STATUS,
                },
                {
                    "as_of": "2026-11-09",
                    "item": "rate_about_60_per_minute",
                    "note": "ориентир документации, не измеренный лимит",
                    "source": PLAN_SECTION_5,
                    "status": DOCUMENTARY_STATUS,
                },
            ],
            "operational_check": {
                "blocks_stages_0_to_3": False,
                "reason": "эксплуатационная проверка относится к этапу 4",
                "status": NOT_RUN,
            },
            "saved_responses": {
                "families": NOT_RUN,
                "gene_protein_cross_reference": NOT_RUN,
                "reason": "сохранённые ответы в репозитории отсутствуют",
                "targets": NOT_RUN,
            },
        },
        "biological_accuracy_accepted": False,
        "class_dictionary": [_rule_payload(rule) for rule in class_rules()],
        "direct_mappings": direct_mapping_document(),
        "rf001_semantics": semantics_document(),
        "rf002_identifier_roles": identifier_roles_document(),
        "gold_cases": {
            "cases": [],
            "checker": "Cursor",
            "reason": "проверяющий не подтвердил биологические эталоны",
            "status": "не подтверждены",
        },
        "http_adapter": {
            "approved_on": "2026-11-15",
            "burst": 1,
            "client_mapping": (
                "timeout_sec задаёт connect, write и pool; "
                "read = timeout_sec * read_timeout_multiplier"
            ),
            "failure_threshold": 5,
            "max_retries": 3,
            "operational_check": NOT_RUN,
            "rate_note": (
                "потолок по документальному ориентиру около 60 запросов/мин; "
                "лимит сервиса не измерен"
            ),
            "read_timeout_multiplier": 2,
            "recovery_timeout": 60,
            "requests_per_second": 1,
            "retry_base_delay": 1,
            "retry_max_delay": 30,
            "status": APPROVED,
            "timeout_sec": 15,
            "version": "2026-11-15",
        },
        "issue": "https://github.com/SatoryKono/BioactivityDataAcquisition/issues/13009",
        "l1_l2_independence": {
            "biological_sample_review": False,
            "checker": "Cursor",
            "checked_against": "этап 0: provenance L1/L2 не установлено",
            "result": "производным независимым подтверждением не считается",
            "role_assignment": ROLE_ASSIGNMENT,
            "usage": "candidate_only",
        },
        "local_rule_catalog_sha256": local_rules_catalog_sha256(),
        "local_rule_catalog_version": LOCAL_CATALOG_VERSION,
        "local_rules": [_rule_payload(rule) for rule in local_rules()],
        "parameters": {
            "graph_limits": {
                "approved_on": "2026-11-15",
                "keys": ["max_depth", "max_visited_nodes"],
                "max_depth": GRAPH_MAX_DEPTH,
                "max_visited_nodes": GRAPH_MAX_VISITED_NODES,
                "scope": "обход предков familyIds одной мишени",
                "status": APPROVED,
            },
            "isoform_policy": None,
            "isoform_policy_status": UNSET,
            "missing_markers_base": list(BASE_MISSING_MARKERS),
            "missing_markers_null": True,
            "missing_markers_version": None,
            "missing_markers_whitespace_only": True,
            "missing_markers_version_status": UNSET,
            "snapshot_coverage": (
                "все мишени в согласованном охвате, их семейства и предки, "
                "генные и белковые идентификаторы"
            ),
            "snapshot_species": list(SPECIES_TAXON_IDS),
            "snapshot_coverage_status": APPROVED,
            "volume_test_seconds": VOLUME_TEST_SECONDS,
            "volume_test_time_status": VOLUME_TEST_TIME_STATUS,
        },
        "plan": {"issued_on": "2026-11-23", "revision": "9", "version": "1"},
        "result_key": ["input_row_id", "snapshot_id"],
        "role_assignment": ROLE_ASSIGNMENT,
        "stage": "1",
        "stage_status": "recorded_without_biological_acceptance",
        "subclass_comparison": {
            "class_subclass_pairs": [],
            "comparison_pairs_status": UNSET,
            "direct_vocabulary": sorted({label for _, label in TYPE_SUBCLASS_PAIRS}),
            "local_vocabulary": [],
            "rule": (
                "совпадение; класс–подкласс; иначе несовместимость; "
                "подкласс вне словаря своего слоя — дефект контракта; "
                "подкласс без отображения в другой слой — несовместим"
            ),
            "same_pairs": [],
            "status": UNSET,
            "vocabulary_issue": (
                "https://github.com/SatoryKono/BioactivityDataAcquisition/issues/13313"
            ),
            "vocabulary_status": APPROVED,
        },
        "unknown_type_status": "unmapped_type",
        "working_classes": list(WORKING_CLASSES),
    }


def publish_policy(output_dir: Path, *, root: Path) -> None:
    """Write ``policy.json`` atomically inside ``root``."""
    payload = canonical_json_bytes(policy_document())
    atomic_write_bytes(output_dir / "policy.json", payload, root=root)


def _rule_payload(rule: RuleRecord) -> dict[str, object]:
    return {
        "family": rule.family,
        "input_conditions": rule.input_conditions,
        "justification_source": rule.justification_source,
        "limits": rule.limits,
        "marks_direct_layer": rule.marks_direct_layer,
        "output": rule.output,
        "priority": rule.priority,
        "rule_id": rule.rule_id,
        "version": rule.version,
    }


def _reject_foreign_targets(mapping: Mapping[str, str]) -> None:
    foreign = sorted(
        {value for value in mapping.values() if value not in WORKING_CLASSES}
    )
    if foreign:
        message = "mapping target is outside the class dictionary: " + ", ".join(
            foreign,
        )
        raise ValueError(message)
