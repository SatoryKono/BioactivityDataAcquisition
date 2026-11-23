"""Stage-1 policy: class dictionary, comparison rule, and recorded limits.

Direct class mappings, graph limits and the HTTP adapter configuration were
recorded on 2026-11-15. Biological accuracy is not yet accepted. Unapproved
plan parameters stay null. EC, L1, and L2 rules stay on the local layer.

RF-001 (#13309) embeds the field-layer / status / capability semantics contract
without changing biological acceptance or rewriting historical artifacts.
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
from .iuphar_mapping import approved_class_mappings
from .semantics import semantics_document
from .stage0.io import atomic_write_bytes, canonical_json_bytes

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


def local_rules() -> tuple[RuleRecord, ...]:
    """Plan step D rules. None of them write the direct layer."""
    rules = [
        RuleRecord(
            rule_id=f"ec:{number}",
            family="ec",
            input_conditions=f"EC с подтверждённой категорией {number}",
            output=name,
            justification_source="план v1 r8 шаг D, справочник IUBMB",
            version=PLAN_VERSION,
            limits=(
                "категория EC, не класс IUPHAR; EC 7 не становится "
                "Transporter; слой local"
            ),
            marks_direct_layer=False,
        )
        for number, name in EC_CATEGORIES
    ]
    rules.append(
        RuleRecord(
            rule_id="predicted-l1-l2",
            family="l1_l2",
            input_conditions="predicted L1/L2 при неизвестном происхождении",
            output="candidate_only",
            justification_source="план v1 r8 шаг D; этап 0: происхождение не установлено",
            version=PLAN_VERSION,
            limits="не независимое подтверждение и не direct-слой",
            marks_direct_layer=False,
        ),
    )
    rules.append(
        RuleRecord(
            rule_id="free-text",
            family="free_text",
            input_conditions="свободный текст, подстроки kinase/channel/zinc finger",
            output="кандидат ручного разбора",
            justification_source="план v1 r8 шаг D",
            version=PLAN_VERSION,
            limits="класс автоматически не определяется",
            marks_direct_layer=False,
        ),
    )
    return tuple(rules)


def all_rules() -> tuple[RuleRecord, ...]:
    """Dictionary rules followed by local rules."""
    return class_rules() + local_rules()


def validate_rules(rules: tuple[RuleRecord, ...]) -> None:
    """Reject a rule config that omits a field or marks EC/L1/L2 as direct."""
    required = (
        "rule_id",
        "family",
        "input_conditions",
        "output",
        "justification_source",
        "version",
        "limits",
    )
    for rule in rules:
        for field_name in required:
            if not getattr(rule, field_name):
                message = f"rule {rule.rule_id} missing {field_name}"
                raise ValueError(message)
        if (
            rule.family in {"ec", "ec_class", "annotation", "l1_l2", "l2"}
            and rule.marks_direct_layer
        ):
            message = f"rule {rule.rule_id} must not be marked direct"
            raise ValueError(message)
        if rule.family == "dictionary" and rule.output not in WORKING_CLASSES:
            message = f"rule {rule.rule_id} output is outside the class dictionary"
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
