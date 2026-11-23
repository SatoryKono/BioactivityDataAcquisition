"""Independent RF-008 expectations and an offline qualification receipt.

Expected labels are taken from the pinned GtoPdb family table, the IUBMB EC
names, and the written anchor policy. This module does not copy classifier
output into the expectation document, and it does not admit enrich.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from .bioetl_input import project_target_fields, target_input_eligibility
from .comparison import Stage0Reference, compare_stage0
from .gtopdb_2026_3_1 import (
    ARCHIVE_SHA256,
    FAMILY_ROWS,
    RELEASE,
    SPECIES_TAXON_IDS,
    SQL_SHA256,
    TARGETS_CSV_SHA256,
    TYPE_CLASS_PAIRS,
)
from .hierarchy import (
    FamilyNode,
    normalize_approved_provider_class,
    normalize_provider_class,
)
from .local_layer import apply_local
from .matching import CatalogTarget, MatchQuery, resolve_match
from .normalization import normalize_missing, parse_ec_numbers
from .policy import (
    BASE_MISSING_MARKERS,
    PLAN_VERSION,
    UNSET,
    WORKING_CLASSES,
    all_rules,
    local_rules,
    policy_document,
)
from .stage0.io import canonical_json_bytes, sha256_bytes, sha256_file

QUALIFICATION_VERSION = "rf008-2026-11-23"
NORMALIZATION_VERSION = "bioetl-iuphar-input-v1"
CLASSIFICATION_SCHEMA_VERSION = "3.1.0"
ISSUE = "https://github.com/SatoryKono/BioactivityDataAcquisition/issues/13316"
EPIC = "https://github.com/SatoryKono/BioactivityDataAcquisition/issues/13308"
_SINGLE_PROTEIN = "SINGLE PROTEIN"

CONTROL_INPUTS = 1000
AUDIT_MATCHED = 117
AUDIT_AMBIGUOUS = 547
AUDIT_SOURCE_UNAVAILABLE = 189
AUDIT_OUTSIDE_TAXA = 147
COUNTERFACTUAL_MATCHED = 633
INTERSECTION_MATCHES = 374
HISTORICAL_REVIEWED = 6
HISTORICAL_UNREVIEWED = 994

REQUIRED_CATEGORIES = (
    "auxiliary_anchor",
    "broad_tf_tag",
    "comparison_evidence",
    "complex",
    "cycle",
    "direct_type",
    "ec_category",
    "identity_conflict",
    "missing_marker",
    "missing_node",
    "multi_parent",
    "multiple_ec",
    "name_only",
    "partial_source",
    "primary_anchor",
    "species",
)

_HISTORICAL_ARTIFACTS = (
    "data/iuphar_target_class/acceptance/stages_0_3_report.json",
    "data/iuphar_target_class/acceptance/tc10/engineering-evidence.md",
    "data/iuphar_target_class/acceptance/tc10/engineering-run-receipt.json",
    "data/iuphar_target_class/acceptance/tc10/traceability.json",
)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SUPPORTED_TAXA = frozenset(str(item) for item in SPECIES_TAXON_IDS)


def build_independent_expectations() -> dict[str, object]:
    """Freeze dictionary and policy expectations before any classifier call."""
    cases = _expectation_cases()
    found = {str(case["category"]) for case in cases}
    missing = [name for name in REQUIRED_CATEGORIES if name not in found]
    if missing:
        message = "independent expectations omit categories: " + ", ".join(missing)
        raise ValueError(message)
    return {
        "artifact": "bioetl_iuphar_rf008_independent_expectations",
        "biological_accuracy_accepted": False,
        "built_from_classifier_output": False,
        "cases": cases,
        "issue": ISSUE,
        "qualification_version": QUALIFICATION_VERSION,
        "source_release": RELEASE,
    }


def build_cohort_partition() -> dict[str, object]:
    """Split the audited 1000 inputs without promoting unreviewed rows."""
    status_total = (
        AUDIT_MATCHED + AUDIT_AMBIGUOUS + AUDIT_SOURCE_UNAVAILABLE + AUDIT_OUTSIDE_TAXA
    )
    reviewed_total = HISTORICAL_REVIEWED + HISTORICAL_UNREVIEWED
    verified = 0
    acceptable = AUDIT_SOURCE_UNAVAILABLE
    unsupported = AUDIT_OUTSIDE_TAXA
    unreviewed = AUDIT_MATCHED + AUDIT_AMBIGUOUS
    if (
        status_total != CONTROL_INPUTS
        or reviewed_total != CONTROL_INPUTS
        or verified + acceptable + unsupported + unreviewed != CONTROL_INPUTS
    ):
        message = "control registry partitions do not cover 1000 inputs"
        raise ValueError(message)
    return {
        "acceptable_incompleteness": {
            "count": acceptable,
            "row_identities_verified": False,
            "status": "source_unavailable",
            "why": (
                "The pinned snapshot is family_only and its completeness is "
                "not certified, so these rows are a source gap rather than a "
                "negative match. Row ids are not in the repository."
            ),
        },
        "artifact": "bioetl_iuphar_rf008_cohort_partition",
        "axes": {
            "admission_buckets_sum": CONTROL_INPUTS,
            "historical_review_sum": CONTROL_INPUTS,
            "note": (
                "Match-status buckets and the historical 6/994 review cut are "
                "different axes of the same 1000-input audit. The review cut "
                "is not reused as the new admission partition."
            ),
        },
        "diagnostic_observations_not_acceptance_kpis": {
            "acceptance_kpi": False,
            "counterfactual_matched": COUNTERFACTUAL_MATCHED,
            "counterfactual_source": (
                "Epic #13308 / RF-002: dropping auxiliary UniProt xrefs was "
                "counted as 633 matched. That count is not an accuracy KPI."
            ),
            "intersection_matches": INTERSECTION_MATCHES,
            "intersection_source": (
                "Issue #13316 names 374 intersection matches. The row table "
                "is not in the repository, so this receipt does not recompute "
                "or accept that figure."
            ),
        },
        "historical_review_not_reused": {
            "reviewed": HISTORICAL_REVIEWED,
            "reused_as_new_semantics_admission": False,
            "unreviewed": HISTORICAL_UNREVIEWED,
            "why": (
                "The previous 6 reviewed cases follow the old anchor policy. "
                "They do not admit the separated primary/auxiliary semantics."
            ),
        },
        "inputs": CONTROL_INPUTS,
        "issue": ISSUE,
        "qualification_version": QUALIFICATION_VERSION,
        "row_identities_in_repository": False,
        "unsupported": {
            "count": unsupported,
            "status": "outside_supported_taxa",
            "supported_taxa": sorted(_SUPPORTED_TAXA),
            "why": "Taxa outside 9606, 10090 and 10116 are outside the contract.",
        },
        "unreviewed": {
            "ambiguous": AUDIT_AMBIGUOUS,
            "count": unreviewed,
            "declared_verified": False,
            "matched": AUDIT_MATCHED,
            "why": (
                "Matched and ambiguous audit rows have no independent "
                "row-level review in this repository. Unreviewed rows are "
                "not labeled verified."
            ),
        },
        "verified_expectations": {
            "count": verified,
            "why": (
                "No control-row identity is pinned here, and the historical "
                "6 cases are not a verified set for the new semantics."
            ),
        },
    }


def build_profile() -> dict[str, object]:
    """Version and hash pins for a candidate that is not enrich-admitted."""
    return {
        "acceptance": None,
        "admitted_for_enrich": False,
        "artifact": "bioetl_iuphar_rf008_profile_candidate",
        "biological_accuracy_accepted": False,
        "classification_schema_version": CLASSIFICATION_SCHEMA_VERSION,
        "issue": ISSUE,
        "normalization": _normalization_pin(),
        "offline_reproducible": True,
        "qualification_version": QUALIFICATION_VERSION,
        "retained_profile": {
            "acceptance": None,
            "mode": "off",
            "why": "New materials are not qualified, so the last profile stays off.",
        },
        "rules": _rules_pin(),
        "schema_version": 2,
        "snapshot": {
            "admitted": False,
            "annotation_capability": "family_only",
            "archive_sha256": ARCHIVE_SHA256,
            "completeness_certified": False,
            "gtopdb_release": RELEASE,
            "sql_sha256": SQL_SHA256,
            "targets_csv_sha256": TARGETS_CSV_SHA256,
        },
    }


def qualification_materials() -> dict[str, bytes]:
    """Return the canonical qualification files, including the executed receipt."""
    expectations = build_independent_expectations()
    partition = build_cohort_partition()
    profile = build_profile()
    expectation_bytes = canonical_json_bytes(expectations)
    partition_bytes = canonical_json_bytes(partition)
    profile_bytes = canonical_json_bytes(profile)
    receipt = _receipt(
        expectations,
        expectation_sha256=sha256_bytes(expectation_bytes),
        partition_sha256=sha256_bytes(partition_bytes),
        profile_sha256=sha256_bytes(profile_bytes),
    )
    receipt_bytes = canonical_json_bytes(receipt)
    pins = {
        "artifact": "bioetl_iuphar_rf008_material_pins",
        "biological_accuracy_accepted": False,
        "files": {
            "cohort_partition.json": sha256_bytes(partition_bytes),
            "independent_expectations.json": sha256_bytes(expectation_bytes),
            "profile.json": sha256_bytes(profile_bytes),
            "qualification_receipt.json": sha256_bytes(receipt_bytes),
        },
        "qualification_version": QUALIFICATION_VERSION,
    }
    return {
        "cohort_partition.json": partition_bytes,
        "independent_expectations.json": expectation_bytes,
        "material_sha256.json": canonical_json_bytes(pins),
        "profile.json": profile_bytes,
        "qualification_receipt.json": receipt_bytes,
    }


def evaluate_categories(categories: tuple[str, ...]) -> dict[str, object]:
    """Execute one category slice and count unexplained disagreements."""
    selected = [
        case
        for case in _cases(build_independent_expectations())
        if str(case["category"]) in categories
    ]
    found = {str(case["category"]) for case in selected}
    missing = [name for name in categories if name not in found]
    if missing:
        message = "requested qualification categories are absent: " + ", ".join(missing)
        raise ValueError(message)
    results = [_evaluate(case) for case in selected]
    unexplained = [
        str(item["case_id"]) for item in results if item["disposition"] == "unexplained"
    ]
    return {
        "cases": results,
        "unexplained_case_ids": unexplained,
        "unexplained_error_count": len(unexplained),
    }


def _expectation_cases() -> list[dict[str, object]]:
    cases = [
        *_direct_type_cases(),
        _partial_source_case(),
        _multi_parent_case(),
        _grouping_case(),
        _cycle_case(),
        _missing_node_case(),
        *_ec_cases(),
        _multiple_ec_case(),
        _broad_tf_case(),
        _missing_marker_case(),
        _primary_anchor_case(),
        _auxiliary_anchor_case(),
        _projection_case(),
        _conflict_case(),
        _name_only_case(),
        _species_gap_case(),
        _not_found_case(),
        _source_unavailable_case(),
        _supported_taxon_case(),
        _unsupported_taxon_case(),
        _complex_case(),
        _explained_change_case(),
        _unexplained_change_case(),
    ]
    return sorted(cases, key=lambda item: str(item["case_id"]))


def _direct_type_cases() -> list[dict[str, object]]:
    cases: list[dict[str, object]] = []
    for source_type, mapped in TYPE_CLASS_PAIRS:
        family_id = _representative(source_type)
        cases.append(
            _case(
                f"direct-type-{source_type}",
                "direct_type",
                "approved_hierarchy",
                {
                    "record": [source_type, mapped],
                    "source": "gtopdb_2026_3_1.TYPE_CLASS_PAIRS",
                },
                {
                    "family_ids": [str(family_id)],
                    "release": RELEASE,
                    "type_name": source_type,
                },
                {
                    "annotation_status": "available",
                    "iuphar_class": mapped,
                    "root_to_leaf_paths": _dictionary_paths(family_id),
                },
                claim="dictionary_class",
            )
        )
    return cases


def _partial_source_case() -> dict[str, object]:
    family_id = _representative("gpcr")
    mapped = dict(TYPE_CLASS_PAIRS)["gpcr"]
    return _case(
        "graph-partial-family",
        "partial_source",
        "approved_hierarchy",
        {
            "family_id": family_id,
            "source": "FAMILY_ROWS gpcr without a direct type; family_only snapshot",
            "type_class": mapped,
        },
        {"family_ids": [str(family_id)], "release": RELEASE, "type_name": None},
        {
            "annotation_status": "partial",
            "iuphar_class": mapped,
            "root_to_leaf_paths": _dictionary_paths(family_id),
        },
        claim="dictionary_class",
    )


def _multi_parent_case() -> dict[str, object]:
    family_id = _multi_parent_family()
    source_type, parents = _family_index()[family_id]
    mapped = dict(TYPE_CLASS_PAIRS)[source_type]
    return _case(
        "graph-multi-parent",
        "multi_parent",
        "approved_hierarchy",
        {
            "family_id": family_id,
            "parents": list(parents),
            "source": "FAMILY_ROWS immediate parents",
            "type_class": mapped,
        },
        {
            "family_ids": [str(family_id)],
            "release": RELEASE,
            "type_name": source_type,
        },
        {
            "annotation_status": "available",
            "branch_count": len(parents),
            "iuphar_class": mapped,
            "root_to_leaf_paths": _dictionary_paths(family_id),
        },
        claim="dictionary_class",
    )


def _grouping_case() -> dict[str, object]:
    family_id = _representative("grouping")
    return _case(
        "graph-grouping-unmapped",
        "direct_type",
        "approved_hierarchy",
        {
            "family_id": family_id,
            "source": "FAMILY_ROWS grouping is excluded from the class map",
        },
        {
            "family_ids": [str(family_id)],
            "release": RELEASE,
            "type_name": "grouping",
        },
        {
            "annotation_status": "unmapped_type",
            "iuphar_class": None,
            "root_to_leaf_paths": _dictionary_paths(family_id),
        },
        claim="dictionary_class",
    )


def _cycle_case() -> dict[str, object]:
    return _case(
        "graph-cycle",
        "cycle",
        "synthetic_hierarchy",
        {"source": "graph policy: a cycle does not yield a class from a cut path"},
        {
            "family_ids": ["a"],
            "nodes": [
                {"family_id": "a", "parent_ids": ["b"], "payload": "a"},
                {"family_id": "b", "parent_ids": ["a"], "payload": "b"},
            ],
            "type_name": None,
        },
        {
            "annotation_status": "not_available",
            "iuphar_class": None,
            "paths_empty": True,
        },
        claim="engineering_rule",
    )


def _missing_node_case() -> dict[str, object]:
    return _case(
        "graph-missing-node",
        "missing_node",
        "synthetic_hierarchy",
        {"source": "graph policy: a missing parent does not invent a family class"},
        {
            "family_ids": ["leaf"],
            "nodes": [{"family_id": "leaf", "parent_ids": ["gone"], "payload": "leaf"}],
            "type_name": None,
        },
        {
            "annotation_status": "not_available",
            "iuphar_class": None,
            "paths_empty": True,
        },
        claim="engineering_rule",
    )


def _ec_cases() -> list[dict[str, object]]:
    return [
        _case(
            f"local-ec-{number}",
            "ec_category",
            "local_ec",
            {"number": number, "source": "IUBMB EC class via policy.EC_CATEGORIES"},
            {"ec": f"{number}.-.-.-"},
            {
                "direct_layer_rule_ids": [],
                "ec_categories": [name],
                "local_class": None,
                "not_an_iuphar_class": True,
                "rule_family": "ec",
                "rule_marks_direct_layer": False,
                "rule_output": name,
            },
            claim="dictionary_class",
        )
        for number, name in (
            (1, "Oxidoreductases"),
            (2, "Transferases"),
            (3, "Hydrolases"),
            (4, "Lyases"),
            (5, "Isomerases"),
            (6, "Ligases"),
            (7, "Translocases"),
        )
    ]


def _multiple_ec_case() -> dict[str, object]:
    return _case(
        "local-ec-multiple",
        "multiple_ec",
        "local_ec",
        {
            "source": "IUBMB classes 1 and 3; multiple categories are not one IUPHAR class"
        },
        {"ec": "1.-.-.-|3.-.-.-"},
        {
            "direct_layer_rule_ids": [],
            "ec_categories": ["Oxidoreductases", "Hydrolases"],
            "local_class": None,
            "multiple_ec_categories": True,
            "not_an_iuphar_class": True,
            "rule_marks_direct_layer": [False, False],
            "rule_outputs": ["Oxidoreductases", "Hydrolases"],
        },
        claim="dictionary_class",
    )


def _broad_tf_case() -> dict[str, object]:
    return _case(
        "local-tf-broad",
        "broad_tf_tag",
        "local_text",
        {
            "source": (
                "WORKING_CLASSES has no transcription-factor class, and an "
                "unregistered keyword is not an exact local rule"
            )
        },
        {
            "free_text": "transcription factor kinase channel zinc finger",
            "keyword_ids": ["KW-BROAD-TF"],
        },
        {
            "free_text_marks_direct_layer": [False],
            "free_text_rule_ids": ["free-text"],
            "local_class": None,
            "local_rule_ids": [],
            "local_status": "not_supported",
        },
        claim="engineering_rule",
    )


def _missing_marker_case() -> dict[str, object]:
    markers = [*BASE_MISSING_MARKERS, "   "]
    return _case(
        "local-missing-markers",
        "missing_marker",
        "missing_marker",
        {
            "markers": markers,
            "source": "policy BASE_MISSING_MARKERS; version remains unapproved",
        },
        {"markers": markers},
        {
            "normalized": [None for _ in markers],
            "version": None,
            "version_status": UNSET,
        },
        claim="engineering_rule",
    )


def _primary_anchor_case() -> dict[str, object]:
    return _case(
        "match-primary-uniprot",
        "primary_anchor",
        "match",
        {"source": "one primary accession and the requested species agree"},
        {
            "catalog": [
                {"target_id": "primary", "uniprot": "P35372", "species": "human"}
            ],
            "organism": "human",
            "snapshot_complete": True,
            "uniprot_ids": ["P35372"],
        },
        {"match_status": "matched", "matched_target_id": "primary"},
        claim="engineering_rule",
    )


def _auxiliary_anchor_case() -> dict[str, object]:
    return _case(
        "match-auxiliary-unknown-xref",
        "auxiliary_anchor",
        "match",
        {
            "source": (
                "RF-002: an unknown auxiliary UniProt xref must not be a "
                "required object id. Issue #13310."
            )
        },
        {
            "catalog": [
                {"target_id": "primary", "uniprot": "P35372", "species": "human"}
            ],
            "organism": "human",
            "snapshot_complete": True,
            "uniprot_ids": ["P35372", "Q99999"],
        },
        {"match_status": "matched", "matched_target_id": "primary"},
        previous_policy={"match_status": "ambiguous", "matched_target_id": None},
        claim="engineering_rule",
    )


def _projection_case() -> dict[str, object]:
    return _case(
        "match-auxiliary-projection",
        "auxiliary_anchor",
        "projection",
        {
            "source": (
                "component_accessions is the primary accession; "
                "target_xref_uniprot_ids is auxiliary. RF-002."
            )
        },
        {
            "component_accessions": ["P35372"],
            "target_xref_uniprot_ids": ["Q99999"],
            "taxon": "9606",
        },
        {
            "auxiliary_uniprot": ["Q99999"],
            "primary_uniprot": ["P35372"],
            "uniprot": "P35372",
        },
        previous_policy={"uniprot": "P35372|Q99999"},
        claim="engineering_rule",
    )


def _conflict_case() -> dict[str, object]:
    return _case(
        "match-conflict-two-primaries",
        "identity_conflict",
        "match",
        {"source": "two reliable ids that hit different catalog targets conflict"},
        {
            "catalog": [
                {"target_id": "1", "uniprot": "P11111", "species": "human"},
                {"target_id": "2", "uniprot": "P22222", "species": "human"},
            ],
            "organism": "human",
            "snapshot_complete": True,
            "target_id": "1",
            "uniprot_ids": ["P22222"],
        },
        {"match_status": "identity_conflict", "matched_target_id": None},
        claim="engineering_rule",
    )


def _name_only_case() -> dict[str, object]:
    return _case(
        "match-name-only",
        "name_only",
        "match",
        {"source": "an exact name does not confirm identity"},
        {
            "catalog": [
                {
                    "name": "Mu opioid receptor",
                    "species": "human",
                    "target_id": "1",
                }
            ],
            "name": "Mu opioid receptor",
            "snapshot_complete": True,
        },
        {"match_status": "ambiguous", "matched_target_id": None},
        claim="engineering_rule",
    )


def _species_gap_case() -> dict[str, object]:
    return _case(
        "match-species-gene",
        "species",
        "match",
        {"source": "the same gene symbol in two species needs the requested taxon"},
        {
            "catalog": [
                {"gene": "GENE1", "species": "human", "target_id": "human-id"},
                {"gene": "GENE1", "species": "mouse", "target_id": "mouse-id"},
            ],
            "gene_symbol": "GENE1",
            "organism": "human",
            "snapshot_complete": True,
        },
        {"match_status": "matched", "matched_target_id": "human-id"},
        claim="engineering_rule",
    )


def _not_found_case() -> dict[str, object]:
    return _case(
        "match-complete-absence",
        "partial_source",
        "match",
        {"source": "a complete snapshot with no hit is not_found, not a class"},
        {"catalog": [], "snapshot_complete": True, "target_id": "missing"},
        {"match_status": "not_found", "matched_target_id": None},
        claim="engineering_rule",
    )


def _source_unavailable_case() -> dict[str, object]:
    return _case(
        "match-incomplete-snapshot",
        "partial_source",
        "match",
        {
            "source": (
                "an incomplete snapshot stays source_unavailable; absence is "
                "not confirmed"
            )
        },
        {"catalog": [], "snapshot_complete": False, "target_id": "missing"},
        {"match_status": "source_unavailable", "matched_target_id": None},
        claim="engineering_rule",
    )


def _supported_taxon_case() -> dict[str, object]:
    return _case(
        "taxon-human",
        "species",
        "eligibility",
        {"source": "SPECIES_TAXON_IDS includes 9606 Homo sapiens"},
        {
            "organism": "Homo sapiens",
            "target_type": _SINGLE_PROTEIN,
            "taxonomy_id": "9606",
        },
        {"reason": None, "taxon": "9606"},
        claim="engineering_rule",
    )


def _unsupported_taxon_case() -> dict[str, object]:
    return _case(
        "taxon-drosophila",
        "species",
        "eligibility",
        {"source": "7227 is outside SPECIES_TAXON_IDS and is unsupported"},
        {
            "organism": "Drosophila melanogaster",
            "target_type": _SINGLE_PROTEIN,
            "taxonomy_id": "7227",
        },
        {"reason": "unsupported_taxon", "taxon": "7227"},
        claim="engineering_rule",
    )


def _complex_case() -> dict[str, object]:
    return _case(
        "match-complex",
        "complex",
        "eligibility",
        {
            "source": (
                "PROTEIN COMPLEX is outside single-protein eligibility; a "
                "subunit accession does not prove the complex"
            )
        },
        {
            "component_accessions": ["P35372"],
            "target_type": "PROTEIN COMPLEX",
            "taxonomy_id": "9606",
        },
        {"reason": "unsupported_target_type", "taxon": None},
        claim="engineering_rule",
    )


def _explained_change_case() -> dict[str, object]:
    return _case(
        "cmp-explained-direct-class",
        "comparison_evidence",
        "comparison",
        {"source": "a direct-class change is kept only with a sign and an explanation"},
        {
            "m_rows": [{"input_row_id": "1", "legacy_iuphar_class": "Receptor"}],
            "python_rows": [
                {
                    "change_sign": "dictionary_change",
                    "explanation": "dictionary record, not a classifier label",
                    "input_row_id": "1",
                    "iuphar_class": "Enzyme",
                }
            ],
        },
        {"change_count": 1, "residual_count": 0},
        claim="engineering_rule",
    )


def _unexplained_change_case() -> dict[str, object]:
    return _case(
        "cmp-unexplained-direct-class",
        "comparison_evidence",
        "comparison",
        {"source": "a direct-class change without evidence stays residual"},
        {
            "m_rows": [{"input_row_id": "1", "legacy_iuphar_class": "Receptor"}],
            "python_rows": [{"input_row_id": "1", "iuphar_class": "Enzyme"}],
        },
        {"change_count": 0, "residual_count": 1},
        claim="engineering_rule",
    )


def _case(
    case_id: str,
    category: str,
    executor: str,
    evidence: dict[str, object],
    fixture: dict[str, object],
    expected: dict[str, object],
    *,
    previous_policy: dict[str, object] | None = None,
    claim: str,
) -> dict[str, object]:
    document: dict[str, object] = {
        "case_id": case_id,
        "category": category,
        "claim": claim,
        "evidence": evidence,
        "executor": executor,
        "expected": expected,
        "fixture": fixture,
    }
    if previous_policy is not None:
        document["previous_policy"] = previous_policy
    return document


def _receipt(
    expectations: Mapping[str, object],
    *,
    expectation_sha256: str,
    partition_sha256: str,
    profile_sha256: str,
) -> dict[str, object]:
    results = [_evaluate(case) for case in _cases(expectations)]
    unexplained = [
        str(item["case_id"]) for item in results if item["disposition"] == "unexplained"
    ]
    explained = [
        str(item["case_id"])
        for item in results
        if item["disposition"] == "explained_previous_policy"
    ]
    verified = [
        str(item["case_id"]) for item in results if item["disposition"] == "verified"
    ]
    engineering = "PASS" if not unexplained else "FAIL"
    return {
        "admitted_identity_or_direct_class_changes": [],
        "artifact": "bioetl_iuphar_rf008_qualification_receipt",
        "biological_acceptance": {
            "biological_accuracy_accepted": False,
            "scientific_status": "independent_expectations_only",
            "why": (
                "Dictionary checks and explained residuals do not review the "
                "1000 control rows and do not admit biological accuracy."
            ),
        },
        "coverage": _coverage(results),
        "diagnostic_observations_not_acceptance_kpis": {
            "acceptance_kpi": False,
            "counterfactual_matched": COUNTERFACTUAL_MATCHED,
            "intersection_matches": INTERSECTION_MATCHES,
        },
        "engineering_acceptance": {
            "explained_previous_policy_count": len(explained),
            "independent_case_count": len(results),
            "status": engineering,
            "unexplained_error_count": len(unexplained),
            "verified_expectation_count": len(verified),
        },
        "enrich_admitted": False,
        "explained_previous_policy_case_ids": explained,
        "historical_acceptance_not_reused": _historical_pin(),
        "issue": ISSUE,
        "pins": {
            "classification_schema_version": CLASSIFICATION_SCHEMA_VERSION,
            "expectations_sha256": expectation_sha256,
            "normalization": _normalization_pin(),
            "partition_sha256": partition_sha256,
            "profile_sha256": profile_sha256,
            "rules": _rules_pin(),
            "snapshot": {
                "admitted": False,
                "archive_sha256": ARCHIVE_SHA256,
                "sql_sha256": SQL_SHA256,
                "targets_csv_sha256": TARGETS_CSV_SHA256,
            },
        },
        "qualification_version": QUALIFICATION_VERSION,
        "results": results,
        "unexplained_case_ids": unexplained,
    }


def _coverage(results: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[str]] = {}
    for item in results:
        grouped.setdefault(str(item["category"]), []).append(str(item["case_id"]))
    return [
        {
            "case_ids": grouped[name],
            "category": name,
            "count": len(grouped[name]),
        }
        for name in sorted(grouped)
    ]


def _historical_pin() -> dict[str, object]:
    files = {
        relative: sha256_file(_REPO_ROOT / relative)
        for relative in _HISTORICAL_ARTIFACTS
    }
    return {
        "files_sha256": files,
        "reviewed_case_count": HISTORICAL_REVIEWED,
        "reused_as_new_semantics_admission": False,
        "unreviewed_case_count": HISTORICAL_UNREVIEWED,
    }


def _rules_pin() -> dict[str, object]:
    payload = [
        {
            "family": rule.family,
            "input_conditions": rule.input_conditions,
            "limits": rule.limits,
            "marks_direct_layer": rule.marks_direct_layer,
            "output": rule.output,
            "rule_id": rule.rule_id,
            "version": rule.version,
        }
        for rule in all_rules()
    ]
    body = canonical_json_bytes(payload)
    return {
        "rules_sha256": sha256_bytes(body),
        "rules_version": PLAN_VERSION,
        "working_classes": list(WORKING_CLASSES),
    }


def _normalization_pin() -> dict[str, object]:
    payload = {
        "missing_markers_base": list(BASE_MISSING_MARKERS),
        "missing_markers_version": None,
        "missing_markers_version_status": UNSET,
        "normalization_version": NORMALIZATION_VERSION,
    }
    return {
        "normalization_sha256": sha256_bytes(canonical_json_bytes(payload)),
        "normalization_version": NORMALIZATION_VERSION,
        "version_status": UNSET,
    }


def _evaluate(case: Mapping[str, object]) -> dict[str, object]:
    observed = _execute(case)
    expected = _mapping(case["expected"])
    if "previous_policy" in case:
        previous = _mapping(case["previous_policy"])
        if _matches(observed, expected):
            disposition = "verified"
        elif _matches(observed, previous):
            disposition = "explained_previous_policy"
        else:
            disposition = "unexplained"
    else:
        disposition = "verified" if _matches(observed, expected) else "unexplained"
    return {
        "case_id": case["case_id"],
        "category": case["category"],
        "claim": case["claim"],
        "disposition": disposition,
        "evidence": case["evidence"],
        "expected": expected,
        "observed": observed,
    }


def _execute(case: Mapping[str, object]) -> dict[str, object]:
    executor = str(case["executor"])
    fixture = _mapping(case["fixture"])
    if executor == "approved_hierarchy":
        return _execute_approved(fixture)
    if executor == "synthetic_hierarchy":
        return _execute_synthetic(fixture)
    if executor == "local_ec":
        return _execute_ec(fixture)
    if executor == "local_text":
        return _execute_text(fixture)
    if executor == "missing_marker":
        return _execute_markers(fixture)
    if executor == "match":
        return _execute_match(fixture)
    if executor == "projection":
        return _execute_projection(fixture)
    if executor == "eligibility":
        return _execute_eligibility(fixture)
    if executor == "comparison":
        return _execute_comparison(fixture)
    message = f"unknown qualification executor: {executor}"
    raise ValueError(message)


def _execute_approved(fixture: Mapping[str, object]) -> dict[str, object]:
    type_name = fixture["type_name"]
    result = normalize_approved_provider_class(
        release=str(fixture["release"]),
        type_name=type_name if isinstance(type_name, str) else None,
        family_ids=tuple(str(item) for item in _sequence(fixture["family_ids"])),
    )
    paths = [list(path.root_to_leaf) for path in result.paths]
    return {
        "annotation_status": result.annotation_status,
        "branch_count": len(paths),
        "iuphar_class": result.iuphar_class,
        "root_to_leaf_paths": paths,
    }


def _execute_synthetic(fixture: Mapping[str, object]) -> dict[str, object]:
    nodes = tuple(
        FamilyNode(
            str(item["family_id"]),
            tuple(str(parent) for parent in _sequence(item["parent_ids"])),
            str(item["payload"]),
        )
        for item in _mappings(fixture["nodes"])
    )
    type_name = fixture["type_name"]
    result = normalize_provider_class(
        type_name=type_name if isinstance(type_name, str) else None,
        family_ids=tuple(str(item) for item in _sequence(fixture["family_ids"])),
        nodes=nodes,
        type_to_class={},
        family_to_class={},
    )
    return {
        "annotation_status": result.annotation_status,
        "iuphar_class": result.iuphar_class,
        "paths_empty": result.paths == (),
    }


def _execute_ec(fixture: Mapping[str, object]) -> dict[str, object]:
    rules = local_rules()
    result = apply_local(parse_ec_numbers(str(fixture["ec"])), rules=rules)
    numbers = [
        int(token.split(".", maxsplit=1)[0])
        for token in str(fixture["ec"]).split("|")
        if token
    ]
    selected = [
        rule for number in numbers for rule in rules if rule.rule_id == f"ec:{number}"
    ]
    iuphar_fields = [
        name for name in result.__dataclass_fields__ if name.startswith("iuphar_")
    ]
    observed: dict[str, object] = {
        "direct_layer_rule_ids": [
            rule.rule_id for rule in rules if rule.marks_direct_layer
        ],
        "ec_categories": list(result.ec_categories),
        "local_class": result.local_class,
        "multiple_ec_categories": result.multiple_ec_categories,
        "not_an_iuphar_class": not iuphar_fields and result.local_class is None,
    }
    if len(selected) == 1:
        observed["rule_family"] = selected[0].family
        observed["rule_marks_direct_layer"] = selected[0].marks_direct_layer
        observed["rule_output"] = selected[0].output
    else:
        observed["rule_marks_direct_layer"] = [
            rule.marks_direct_layer for rule in selected
        ]
        observed["rule_outputs"] = [rule.output for rule in selected]
    return observed


def _execute_text(fixture: Mapping[str, object]) -> dict[str, object]:
    rules = local_rules()
    result = apply_local(
        (),
        rules=rules,
        keyword_ids=tuple(str(item) for item in _sequence(fixture["keyword_ids"])),
        free_text=str(fixture["free_text"]),
    )
    free_text_rules = [rule for rule in rules if rule.family == "free_text"]
    return {
        "free_text_marks_direct_layer": [
            rule.marks_direct_layer for rule in free_text_rules
        ],
        "free_text_rule_ids": [rule.rule_id for rule in free_text_rules],
        "local_class": result.local_class,
        "local_rule_ids": list(result.local_rule_ids),
        "local_status": result.local_status,
    }


def _execute_markers(fixture: Mapping[str, object]) -> dict[str, object]:
    markers = [
        None if item is None else str(item) for item in _sequence(fixture["markers"])
    ]
    parameters = policy_document()["parameters"]
    if not isinstance(parameters, dict):
        message = "policy parameters are missing"
        raise ValueError(message)
    return {
        "normalized": [normalize_missing(item) for item in markers],
        "version": parameters.get("missing_markers_version"),
        "version_status": parameters.get("missing_markers_version_status"),
    }


def _execute_match(fixture: Mapping[str, object]) -> dict[str, object]:
    catalog = tuple(
        _catalog_target(item) for item in _mappings(fixture.get("catalog", []))
    )
    query = MatchQuery(
        _optional_str(fixture.get("target_id")),
        tuple(str(item) for item in _sequence(fixture.get("uniprot_ids", []))),
        _optional_str(fixture.get("gene_symbol")),
        None,
        _optional_str(fixture.get("organism")),
        _optional_str(fixture.get("name")),
        tuple(str(item) for item in _sequence(fixture.get("synonyms", []))),
    )
    result = resolve_match(
        query, catalog, snapshot_complete=bool(fixture["snapshot_complete"])
    )
    return {
        "match_status": result.match_status,
        "matched_target_id": result.matched_target_id,
    }


def _execute_projection(fixture: Mapping[str, object]) -> dict[str, object]:
    projected = project_target_fields(
        {
            "component_accessions": list(_sequence(fixture["component_accessions"])),
            "target_id": "CHEMBL1",
            "target_type": _SINGLE_PROTEIN,
            "target_xref_uniprot_ids": list(
                _sequence(fixture["target_xref_uniprot_ids"])
            ),
        },
        str(fixture["taxon"]),
    )
    observed: dict[str, object] = {
        key: projected[key]
        for key in ("auxiliary_uniprot", "primary_uniprot", "uniprot")
        if key in projected
    }
    return observed


def _execute_eligibility(fixture: Mapping[str, object]) -> dict[str, object]:
    taxon, reason = target_input_eligibility(
        {
            "organism": fixture.get("organism"),
            "target_type": fixture["target_type"],
            "taxonomy_id": fixture["taxonomy_id"],
        },
        _SUPPORTED_TAXA,
    )
    return {"reason": reason, "taxon": taxon}


def _execute_comparison(fixture: Mapping[str, object]) -> dict[str, object]:
    reference = Stage0Reference(
        "rf008",
        1,
        tuple(_string_row(item) for item in _mappings(fixture["m_rows"])),
    )
    report = compare_stage0(
        reference,
        tuple(_string_row(item) for item in _mappings(fixture["python_rows"])),
    )
    return {
        "change_count": len(report.changes),
        "residual_count": len(report.residual),
    }


def _catalog_target(item: Mapping[str, object]) -> CatalogTarget:
    uniprot = _optional_str(item.get("uniprot"))
    name = _optional_str(item.get("name"))
    return CatalogTarget(
        str(item["target_id"]),
        (uniprot,) if uniprot else (),
        _optional_str(item.get("gene")),
        None,
        _optional_str(item.get("species")),
        (name,) if name else (),
        (),
    )


def _matches(observed: Mapping[str, object], expected: Mapping[str, object]) -> bool:
    return all(observed.get(key) == value for key, value in expected.items())


def _dictionary_paths(family_id: int) -> list[list[str]]:
    """Root-to-leaf paths from the pinned family table, one branch per parent."""
    index = _family_index()
    paths: list[list[str]] = []

    def walk(current: int, leaf_to_root: list[int]) -> None:
        if current in leaf_to_root:
            message = f"GtoPdb family {family_id} contains a cycle"
            raise ValueError(message)
        row = index.get(current)
        if row is None:
            message = f"GtoPdb family {family_id} references missing node {current}"
            raise ValueError(message)
        chain = [*leaf_to_root, current]
        parents = row[1]
        if not parents:
            paths.append([str(node) for node in reversed(chain)])
            return
        for parent in parents:
            walk(parent, chain)

    walk(family_id, [])
    return paths


def _family_index() -> dict[int, tuple[str, tuple[int, ...]]]:
    return {
        family_id: (source_type, parents)
        for family_id, source_type, parents in FAMILY_ROWS
    }


def _representative(source_type: str) -> int:
    index = _family_index()
    found = sorted(
        family_id
        for family_id, (kind, _) in index.items()
        if kind == source_type and _closed(family_id, index)
    )
    if not found:
        message = f"no closed GtoPdb family for {source_type}"
        raise ValueError(message)
    return found[0]


def _multi_parent_family() -> int:
    index = _family_index()
    found = sorted(
        family_id
        for family_id, (kind, parents) in index.items()
        if kind != "grouping" and len(parents) > 1 and _closed(family_id, index)
    )
    if not found:
        message = "no closed multi-parent GtoPdb family"
        raise ValueError(message)
    return found[0]


def _closed(family_id: int, index: Mapping[int, tuple[str, tuple[int, ...]]]) -> bool:
    pending = [family_id]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        row = index.get(current)
        if row is None:
            return False
        seen.add(current)
        pending.extend(row[1])
    return True


def _cases(document: Mapping[str, object]) -> tuple[Mapping[str, object], ...]:
    return _mappings(document["cases"])


def _mappings(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, list):
        message = "qualification document expected a list"
        raise ValueError(message)
    rows: list[Mapping[str, object]] = []
    for item in value:
        rows.append(_mapping(item))
    return tuple(rows)


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        message = "qualification document expected an object"
        raise TypeError(message)
    return value


def _sequence(value: object) -> tuple[object, ...]:
    if isinstance(value, list | tuple):
        return tuple(value)
    message = "qualification document expected a sequence"
    raise TypeError(message)


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _string_row(item: Mapping[str, object]) -> dict[str, str]:
    return {str(key): str(value) for key, value in item.items()}


__all__ = [
    "QUALIFICATION_VERSION",
    "build_cohort_partition",
    "build_independent_expectations",
    "build_profile",
    "evaluate_categories",
    "qualification_materials",
]
