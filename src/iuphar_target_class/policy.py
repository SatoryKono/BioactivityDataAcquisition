"""Stage-1 policy: class dictionary, comparison rule, and unset parameters.

Biological mappings are not approved. Values marked [...] in plan v1 r8 stay
null. EC, L1, and L2 rules stay on the local layer.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .stage0.io import atomic_write_bytes, canonical_json_bytes

WORKING_CLASSES: tuple[str, ...] = (
    "Receptor",
    "Ion Channel",
    "Enzyme",
    "Transporter",
    "Other Protein Target",
)
PLAN_SOURCE = "план v1 r8 §2.1"
PLAN_SECTION_5 = "план v1 r8 §5"
DOCUMENTARY_STATUS = "подтверждено документально"
PLAN_VERSION = "plan-v1-r8"
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
NOT_RUN = "NOT_RUN"
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
        if rule.family in {"ec", "l1_l2", "l2"} and rule.marks_direct_layer:
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
    if type_name and type_name in type_to_class:
        mapped = type_to_class[type_name]
        return ClassAssignment(
            iuphar_class=mapped,
            status="available",
            proof="type",
            candidates=(mapped,),
            rule_id=f"class:{mapped}",
        )
    family_classes = tuple(
        family_to_class[family_id]
        for family_id in sorted(family_ids)
        if family_id in family_to_class
    )
    distinct = tuple(sorted(set(family_classes)))
    if len(distinct) == 1:
        mapped = distinct[0]
        return ClassAssignment(
            iuphar_class=mapped,
            status="partial",
            proof="family_mapping",
            candidates=family_classes,
            rule_id=f"class:{mapped}",
        )
    if len(distinct) > 1:
        return ClassAssignment(
            iuphar_class=None,
            status="conflicting",
            proof=None,
            candidates=family_classes,
            rule_id=None,
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
    if direct_subclass is None or local_subclass is None:
        return "empty"
    if direct_subclass not in direct_vocabulary:
        return "contract_defect"
    if local_subclass not in local_vocabulary:
        return "contract_defect"
    pair = (direct_subclass, local_subclass)
    if direct_subclass == local_subclass or pair in same_pairs:
        return "same"
    if pair in class_subclass_pairs:
        return "class_subclass"
    return "incompatible"


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
        "direct_mappings": {
            "families": [],
            "reason": "выпуск снимка не выбран: охват и набор видов не утверждены",
            "release": None,
            "types": [],
        },
        "gold_cases": {
            "cases": [],
            "checker": "Cursor",
            "reason": "закреплённый источник IUPHAR в этапе 0 отсутствует",
            "status": "не подтверждены",
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
                "keys": ["max_depth", "max_visited_nodes"],
                "max_depth": None,
                "max_visited_nodes": None,
                "status": UNSET,
            },
            "isoform_policy": None,
            "isoform_policy_status": UNSET,
            "missing_markers_base": list(BASE_MISSING_MARKERS),
            "missing_markers_null": True,
            "missing_markers_version": None,
            "missing_markers_whitespace_only": True,
            "missing_markers_version_status": UNSET,
            "snapshot_coverage": None,
            "snapshot_species": None,
            "snapshot_coverage_status": UNSET,
            "volume_test_seconds": None,
            "volume_test_time_status": UNSET,
        },
        "plan": {"issued_on": "2026-11-10", "revision": "8", "version": "1"},
        "result_key": ["input_row_id", "snapshot_id"],
        "role_assignment": ROLE_ASSIGNMENT,
        "stage": "1",
        "stage_status": "recorded_without_biological_acceptance",
        "subclass_comparison": {
            "class_subclass_pairs": [],
            "direct_vocabulary": [],
            "local_vocabulary": [],
            "rule": (
                "совпадение; класс–подкласс; иначе несовместимость; "
                "подкласс вне словаря своего слоя — дефект контракта; "
                "подкласс без отображения в другой слой — несовместим"
            ),
            "same_pairs": [],
            "status": UNSET,
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
