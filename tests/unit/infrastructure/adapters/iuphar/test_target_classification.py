"""Synthetic contract fixtures; these tests do not accept biological accuracy."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import url2pathname

import pytest

from bioetl.domain.entities.target_classification_boundary import (
    TargetClassificationArtifact,
    TargetClassificationInput,
)
from bioetl.infrastructure.adapters.iuphar import (
    IupharTargetClassificationAdapter,
    LocalTargetClassificationEvidenceStore,
    load_profile,
    load_snapshot_manifest,
    parse_target_payloads,
    validate_acceptance_receipt,
)
from iuphar_target_class.bioetl_input import project_target_fields
from iuphar_target_class.identifier_roles import (
    ANCHOR_PRIORITY_POLICY_VERSION,
    CHANNEL_EC_POLICY_VERSION,
    RANKED_CLASS_POLICY_VERSION,
    TRANSCRIPTION_FACTOR_POLICY_VERSION,
)
from iuphar_target_class.policy import (
    LOCAL_CATALOG_VERSION,
    LOCAL_RULE_CATALOG_VERSION,
)
from bioetl.infrastructure.adapters.iuphar.snapshot_loader import (
    OUTPUT_NAMES,
    REQUIRED_ACCEPTANCE_CHECKS,
)
from tests.helpers.iuphar_snapshot import (
    synthetic_export_row,
    synthetic_snapshot_bundle,
    synthetic_reference_receipt,
)

pytestmark = pytest.mark.unit


def _write(root: Path, name: str, value: object) -> dict[str, str]:
    content = json.dumps(value, sort_keys=True).encode()
    (root / name).write_bytes(content)
    return {"path": name, "sha256": hashlib.sha256(content).hexdigest()}


def _receipt(snapshot_hash: str) -> dict[str, object]:
    return {
        "artifact": "bioetl_iuphar_acceptance",
        "schema_version": 1,
        "fixture_kind": "synthetic_contract_fixture",
        "scope": "offline_target_integration",
        "status": "PASS",
        "snapshot_manifest_sha256": snapshot_hash,
        "stage0_manifest_sha256": "a" * 64,
        "expected_labels_sha256": "b" * 64,
        "output_sha256": dict.fromkeys(OUTPUT_NAMES, "c" * 64),
        "checks": dict.fromkeys(REQUIRED_ACCEPTANCE_CHECKS, "PASS"),
        "reference_cases_accepted": True,
        "biological_accuracy_accepted": False,
        "run_id": "contract-run",
        "reviewer_reference": "synthetic-unit-test-expectations",
        "normalization_version": "bioetl-iuphar-input-v1",
        "rules_version": "local-rules-2026.11.23",
        "classification_schema_version": "3.1.0",
        "matching_policy_version": "rf002-uniprot-roles-2026-11-23",
    }


def _profile(
    tmp_path: Path,
    *,
    accepted: bool = False,
    target_changes: dict[str, object] | None = None,
    rules_version: str = LOCAL_CATALOG_VERSION,
    schema_version: str = "3.1.0",
    **snapshot_changes: object,
):
    if accepted:
        root, bundle = synthetic_snapshot_bundle(
            tmp_path / "verified",
            rows=[synthetic_export_row(family_id="471", family_type="enzyme")],
        )
        acceptance = _write(
            root,
            "acceptance.json",
            synthetic_reference_receipt(
                bundle.snapshot_sha256, root=root / "reference-fixture"
            ),
        )
        document = json.loads((root / "profile.json").read_bytes())
        document["acceptance"] = acceptance
        reference = _write(root, "enrich-profile.json", document)
        return load_profile(root / reference["path"], reference["sha256"])
    targets = _write(
        tmp_path,
        "targets.json",
        [
            {
                "targetId": 1,
                "type": "enzyme",
                "familyIds": [],
                "taxonId": "9606",
                "uniprotIds": ["P12345"],
                "name": "known enzyme",
                "synonyms": ["enzyme alias"],
                **(target_changes or {}),
            },
        ],
    )
    snapshot = {
        "artifact": "bioetl_iuphar_snapshot",
        "schema_version": 1,
        "format": "gtopdb_target_payload_v1",
        "snapshot_id": "synthetic-snapshot",
        "provider_release": "2026.3.1",
        "retrieved_at": "2026-11-16T00:00:00Z",
        "targets": targets,
        "species_taxon_ids": ["9606"],
        "required_target_types": ["enzyme"],
        "expected_target_count": 1,
        "provider_versions": "совпали",
        "coverage_approval_reference": "synthetic-fixture-scope",
        "pagination_complete": True,
        **snapshot_changes,
    }
    snapshot_ref = _write(tmp_path, "snapshot.json", snapshot)
    acceptance = (
        _write(tmp_path, "acceptance.json", _receipt(snapshot_ref["sha256"]))
        if accepted
        else None
    )
    profile = {
        "artifact": "bioetl_iuphar_profile",
        "schema_version": 1,
        "snapshot": snapshot_ref,
        "acceptance": acceptance,
        "normalization_version": "bioetl-iuphar-input-v1",
        "rules_version": rules_version,
        "classification_schema_version": schema_version,
        "matching_policy_version": "rf002-uniprot-roles-2026-11-23",
    }
    ref = _write(tmp_path, "profile.json", profile)
    return load_profile(
        tmp_path / ref["path"], ref["sha256"], require_acceptance=accepted
    )


def _business(**overrides: object) -> dict[str, object]:
    return {
        "target_id": "CHEMBL1",
        "target_type": "SINGLE PROTEIN",
        "taxonomy_id": 9606,
        "organism": "Homo sapiens",
        "component_accessions": '["P12345"]',
        "target_xref_uniprot_ids": "unknown",
        "target_protein_synonyms": "enzyme alias|unknown",
        "target_gene_synonyms": "unknown",
        "target_ec_numbers": "unknown",
        "pref_name": "known enzyme",
        **overrides,
    }


def _classify(adapter, **overrides):
    return adapter.classify_record(
        _business(**overrides),
        input_row_id="target:1",
        run_id="run-a",
        run_started_at="2026-11-16T00:01:00Z",
    )


def _profile_path(profile) -> Path:
    return Path(url2pathname(urlsplit(profile.profile_uri).path))


def test_direct_class_uses_payload_and_preserves_input(tmp_path):
    profile = _profile(tmp_path)
    adapter = IupharTargetClassificationAdapter(profile)
    data = _business()
    before = json.dumps(data, sort_keys=True)
    result = adapter.classify_record(
        data, input_row_id="target:1", run_id="run-a", run_started_at="fixed"
    )
    assert json.dumps(data, sort_keys=True) == before
    assert result.projection["iuphar_class"] == "Enzyme"
    assert result.projection["iuphar_target_id"] == "1"
    assert result.projection["iuphar_match_status"] == "matched"
    assert result.projection["target_class_profile_sha256"] == profile.profile_sha256
    output = json.loads(
        next(a.payload for a in result.artifacts if a.name == "classification.json")
    )[0]
    assert output["raw_fields"]["source_organism"] == "Homo sapiens"
    assert output["normalized_fields"]["organism"] == "9606"
    assert output["raw_fields"]["ec"] is None


def test_enrich_requires_accepted_references_and_publishable_snapshot(tmp_path):
    profile = _profile(tmp_path)
    path = _profile_path(profile)
    with pytest.raises(ValueError, match="source-verified snapshot schema 2"):
        load_profile(path, profile.profile_sha256)


def test_valid_reference_receipt_admits_enrich_contract_fixture(tmp_path):
    profile = _profile(tmp_path, accepted=True)
    assert profile.acceptance_sha256 is not None
    assert profile.snapshot.completeness.publishable


@pytest.mark.parametrize(
    "field",
    [
        "normalization_version",
        "rules_version",
        "classification_schema_version",
        "matching_policy_version",
    ],
)
def test_receipt_from_another_execution_version_cannot_admit_enrich(field):
    receipt = _receipt("a" * 64)
    receipt[field] = "unreviewed-version"
    with pytest.raises(ValueError, match="acceptance versions"):
        validate_acceptance_receipt(receipt, snapshot_manifest_sha256="a" * 64)


def test_receipt_cannot_admit_a_different_profile_version(tmp_path):
    profile = _profile(tmp_path, accepted=True)
    path = _profile_path(profile)
    document = json.loads(path.read_bytes())
    document["rules_version"] = LOCAL_RULE_CATALOG_VERSION
    document["classification_schema_version"] = "3.2.0"
    rewritten = _write(path.parent, "shifted-profile.json", document)
    with pytest.raises(ValueError, match="selected IUPHAR profile"):
        load_profile(path.parent / rewritten["path"], rewritten["sha256"])


def test_candidate_reclassification_uses_the_stored_row_identity(tmp_path):
    from bioetl.infrastructure.storage.target_migration_classification_checks import (
        verify_source_classifications,
    )

    profile = _profile(
        tmp_path,
        target_changes={"type": "gpcr"},
        required_target_types=["gpcr"],
        rules_version=LOCAL_RULE_CATALOG_VERSION,
        schema_version="3.2.0",
    )
    business = _business(target_ec_numbers="3.4.21.1")
    result = IupharTargetClassificationAdapter(profile).classify_record(
        business,
        input_row_id="candidate:CHEMBL1",
        run_id="run-a",
        run_started_at="2026-11-16T00:01:00Z",
    )
    row = {**business, **result.projection, "target_id": "CHEMBL1"}
    verify_source_classifications({"silver": [row], "gold": [row]}, profile)


def test_candidate_reclassification_rejects_v32_detail_drift(tmp_path):
    from bioetl.domain.config.target_classification import (
        TARGET_CLASSIFICATION_DETAIL_FIELDS,
    )
    from bioetl.infrastructure.storage.target_migration_classification_checks import (
        verify_source_classifications,
    )

    profile = _profile(
        tmp_path,
        target_changes={"type": "gpcr"},
        required_target_types=["gpcr"],
        rules_version=LOCAL_RULE_CATALOG_VERSION,
        schema_version="3.2.0",
    )
    business = _business(target_ec_numbers="3.4.21.1")
    result = IupharTargetClassificationAdapter(
        profile, table_contract="3.2.0"
    ).classify_record(
        business,
        input_row_id="candidate:CHEMBL1",
        run_id="run-a",
        run_started_at="2026-11-16T00:01:00Z",
    )
    row = {**business, **result.projection, "target_id": "CHEMBL1"}
    verify_source_classifications({"silver": [row], "gold": [row]}, profile, "3.2.0")
    field = TARGET_CLASSIFICATION_DETAIL_FIELDS[0]
    corrupt = {**row, field: "incorrect"}
    with pytest.raises(ValueError, match="candidate classification differs"):
        verify_source_classifications(
            {"silver": [corrupt], "gold": [row]}, profile, "3.2.0"
        )


def test_previous_plan_rules_version_cannot_admit_the_new_catalog():
    receipt = _receipt("a" * 64)
    receipt["rules_version"] = "plan-v1-r8"
    with pytest.raises(ValueError, match="acceptance versions"):
        validate_acceptance_receipt(receipt, snapshot_manifest_sha256="a" * 64)


def test_pre_rf002_receipt_format_is_rejected_for_new_matching():
    """Real prior receipt shape (schema 2, no matching_policy_version) cannot admit."""
    receipt = _receipt("a" * 64)
    assert "matching_policy_version" in receipt
    del receipt["matching_policy_version"]
    assert {
        "normalization_version",
        "rules_version",
        "classification_schema_version",
    }.issubset(receipt)
    with pytest.raises(ValueError, match="acceptance versions"):
        validate_acceptance_receipt(receipt, snapshot_manifest_sha256="a" * 64)


def test_pre_rf002_profile_format_is_rejected_for_new_matching(tmp_path):
    from bioetl.infrastructure.adapters.iuphar._manifest import sha256
    from iuphar_target_class.stage0.io import canonical_json_bytes

    profile = _profile(tmp_path)
    path = _profile_path(profile)
    document = json.loads(path.read_bytes())
    del document["matching_policy_version"]
    path.write_bytes(canonical_json_bytes(document))
    with pytest.raises(
        ValueError, match="matching_policy_version|IUPHAR profile versions"
    ):
        load_profile(path, sha256(path.read_bytes()), require_acceptance=False)


def test_complete_version_unverified_snapshot_is_not_publishable(tmp_path):
    profile = _profile(
        tmp_path,
        provider_versions="недоступны",
        version_limitation_reference="fixture-limitation",
    )
    assert profile.snapshot.completeness.complete
    assert not profile.snapshot.completeness.publishable
    path = _profile_path(profile)
    with pytest.raises(ValueError, match="source-verified snapshot schema 2"):
        load_profile(path, profile.profile_sha256)


def test_incomplete_snapshot_does_not_rewrite_known_match_semantics(tmp_path):
    profile = _profile(tmp_path, pagination_complete=False)
    assert not profile.snapshot.completeness.complete
    assert (
        _classify(IupharTargetClassificationAdapter(profile)).projection[
            "iuphar_match_status"
        ]
        == "matched"
    )


def test_partial_type_proof_keeps_the_direct_class(tmp_path):
    profile = _profile(tmp_path, target_changes={"familyIds": [99999999]})
    result = _classify(IupharTargetClassificationAdapter(profile))
    assert result.projection["iuphar_class"] == "Enzyme"
    assert result.projection["iuphar_annotation_status"] == "partial"


def test_an_ec_input_does_not_replace_direct_iuphar(tmp_path):
    profile = _profile(
        tmp_path, target_changes={"type": "gpcr"}, required_target_types=["gpcr"]
    )
    result = _classify(
        IupharTargetClassificationAdapter(profile), target_ec_numbers="3.4.21.1"
    )
    assert result.projection["iuphar_class"] == "Receptor"
    # EC 3 is a local Enzyme witness. It stays in local_class and does not
    # replace the official IUPHAR class.
    assert result.projection["local_class"] == "Enzyme"
    assert result.projection["effective_class"] == "Receptor"
    assert result.projection["effective_source"] == "iuphar_normalized"
    assert result.projection["decision_status"] == "requires_review"
    output = json.loads(
        next(a.payload for a in result.artifacts if a.name == "classification.json")
    )[0]
    assert output["iuphar_subclass"] == "G protein-coupled receptors"
    assert output["iuphar_subclasses"] == ["G protein-coupled receptors"]


def _channel_ec_adapter(profile, policy=CHANNEL_EC_POLICY_VERSION):
    snapshot = profile.snapshot.snapshot
    snapshot = replace(
        snapshot,
        species_annotations={
            (key, annotation.taxon): annotation
            for key, annotation in snapshot.annotations.items()
        },
    )
    return IupharTargetClassificationAdapter(
        replace(
            profile,
            matching_policy_version=policy,
            snapshot=replace(profile.snapshot, snapshot=snapshot),
        )
    )


def test_shadow_hgnc_profile_requires_source_verified_snapshot_schema(tmp_path):
    profile_path = _profile_path(_profile(tmp_path))
    source = json.loads(profile_path.read_bytes())
    source["matching_policy_version"] = ANCHOR_PRIORITY_POLICY_VERSION
    reference = _write(profile_path.parent, "legacy-hgnc-profile.json", source)
    with pytest.raises(
        ValueError,
        match="HGNC anchor priority requires source-verified snapshot schema 2",
    ):
        load_profile(
            profile_path.parent / reference["path"],
            reference["sha256"],
            require_acceptance=False,
        )


@pytest.mark.parametrize(
    ("taxon", "organism", "hgnc", "accession", "method"),
    [
        (9606, "Homo sapiens", "HGNC:101", "Q88888", "hgnc"),
        (9606, "Homo sapiens", "unknown", "P12345", "uniprot_xref"),
        (10090, "Mus musculus", "HGNC:101", "Q88888", None),
    ],
)
def test_verified_hgnc_profile_uses_canonical_input_fields(
    tmp_path, taxon, organism, hgnc, accession, method
):
    provider = synthetic_export_row()
    provider["HGNC id"] = "101"
    root, _ = synthetic_snapshot_bundle(
        tmp_path, rows=[provider], species=("9606", "10090")
    )
    profile = json.loads((root / "profile.json").read_bytes())
    profile["matching_policy_version"] = ANCHOR_PRIORITY_POLICY_VERSION
    reference = _write(root, "hgnc-profile.json", profile)
    adapter = IupharTargetClassificationAdapter(
        load_profile(
            root / reference["path"], reference["sha256"], require_acceptance=False
        )
    )
    business = _business(
        pref_name="Other name",
        target_protein_synonyms="unknown",
        taxonomy_id=taxon,
        organism=organism,
        component_accessions=accession,
        target_xref_hgnc_ids=hgnc,
    )
    result = _classify(adapter, **business)
    assert result.projection["iuphar_target_id"] == ("1" if method else None)
    assert result.projection["iuphar_class"] == ("Receptor" if method else None)
    classification = json.loads(
        next(a.payload for a in result.artifacts if a.name == "classification.json")
    )[0]
    expected = project_target_fields(business, str(taxon))
    assert "hgnc" not in classification["raw_fields"]
    assert (
        classification["raw_fields"]["source_business_data"]
        == expected["source_business_data"]
    )
    assert classification["match_method"] == ([method] if method else [])


@pytest.mark.parametrize(
    "policy", [RANKED_CLASS_POLICY_VERSION, TRANSCRIPTION_FACTOR_POLICY_VERSION]
)
def test_ranked_channel_candidate_blocks_ec_when_identity_is_unresolved(
    tmp_path, policy
):
    adapter = _channel_ec_adapter(
        _profile(tmp_path, target_changes={"type": "vgic"}), policy
    )
    result = _classify(
        adapter, component_accessions="Q9BW60", target_ec_numbers="3.1.1.1"
    )
    assert result.projection["iuphar_target_id"] is None
    assert result.projection["effective_class"] is None


@pytest.mark.parametrize(
    ("ec", "expected", "source"),
    [
        ("3.4.21.1", "Receptor", "iuphar_normalized"),
        (
            "2.3.1.-|2.3.2.13|3.4.-.-|3.5.1.44",
            "Enzyme.Multitarget",
            "ec_rule",
        ),
    ],
)
def test_channel_ec_policy_layers_ec_over_existing_nonchannel_class(
    tmp_path, ec, expected, source
):
    adapter = _channel_ec_adapter(
        _profile(
            tmp_path, target_changes={"type": "gpcr"}, required_target_types=["gpcr"]
        )
    )
    result = _classify(adapter, target_ec_numbers=ec)
    assert result.projection["iuphar_target_id"] == "1"
    assert result.projection["iuphar_class"] == "Receptor"
    assert result.projection["effective_class"] == expected
    assert result.projection["effective_source"] == source


def test_channel_wins_against_both_enzyme_and_multiple_ec_categories(tmp_path):
    adapter = _channel_ec_adapter(
        _profile(tmp_path, target_changes={"type": "vgic", "familyIds": [78, 471]})
    )
    result = _classify(adapter, target_ec_numbers="2.7.11.1|3.4.21.1")
    assert result.projection["iuphar_target_id"] == "1"
    assert result.projection["iuphar_annotation_status"] == "conflicting"
    assert result.projection["iuphar_class"] is None
    assert result.projection["effective_class"] == "Ion Channel"
    assert result.projection["effective_source"] == "channel_priority"
    assert "ion_channel_over_enzyme" in result.diagnostic_codes


def test_unconfirmed_channel_candidate_blocks_ec_override(tmp_path):
    adapter = _channel_ec_adapter(_profile(tmp_path, target_changes={"type": "vgic"}))
    result = _classify(
        adapter, component_accessions=None, target_ec_numbers="2.7.11.1|3.4.21.1"
    )
    assert result.projection["iuphar_target_id"] is None
    assert result.projection["effective_class"] is None
    output = {a.name: json.loads(a.payload) for a in result.artifacts}
    assert output["candidates.json"]


@pytest.mark.parametrize(
    ("ec", "expected"),
    [
        ("2.3.1.-|2.3.2.13|invalid", "Enzyme.Transferase"),
        ("7.1.-.-", "Enzyme.Translocase"),
        ("2.3.1.-|3.4.-.-", "Enzyme.Multitarget"),
        ("2.-.1.-|8.4.-.-", None),
    ],
)
def test_channel_ec_policy_classifies_proteins_outside_provider_species(
    tmp_path, ec, expected
):
    adapter = _channel_ec_adapter(_profile(tmp_path))
    result = _classify(
        adapter,
        taxonomy_id=9823,
        organism="Sus scrofa",
        target_ec_numbers=ec,
        target_protein_synonyms="[tau protein] kinase",
    )
    assert result.projection["iuphar_target_id"] is None
    assert result.projection["effective_class"] == expected
    assert "unsupported_taxon" in result.diagnostic_codes
    if expected:
        assert result.projection["iuphar_match_status"] == "source_unavailable"
        assert result.projection["effective_source"] == "ec_rule"
        output = {a.name: json.loads(a.payload) for a in result.artifacts}
        assert any(
            item["source_id"] == "ec_effective_class"
            for item in output["evidence.json"]
        )


@pytest.mark.parametrize(
    ("ec", "label"),
    [
        ("2.3.1.199", "Enzyme.Transferase"),
        ("3.1.26.n2", "Enzyme.Hydrolase"),
        ("3.1.26.N2|2.3.1.-", "Enzyme.Multitarget"),
    ],
)
def test_ranked_policy_uses_ec_before_synonyms(tmp_path, ec, label):
    adapter = _channel_ec_adapter(
        _profile(tmp_path, target_changes={"type": "vgic", "synonyms": ["SSC1"]}),
        RANKED_CLASS_POLICY_VERSION,
    )
    result = _classify(
        adapter,
        pref_name="Another protein",
        component_accessions="Q9BW60",
        target_gene_synonyms="SSC1",
        target_ec_numbers=ec,
    )
    assert result.projection["iuphar_target_id"] is None
    assert result.projection["effective_class"] == label
    assert result.projection["effective_source"] == "ec_rule"
    assert "invalid_ec" not in result.diagnostic_codes
    artifacts = {a.name: json.loads(a.payload) for a in result.artifacts}
    assert artifacts["candidates.json"] == []
    assert any(
        ec.split("|")[0] in item["content"] for item in artifacts["evidence.json"]
    )


@pytest.mark.parametrize(
    ("fields", "method"),
    [
        ({"target_ec_numbers": "3.1.26.n2"}, "exact_name"),
        (
            {"pref_name": "alternate label", "target_gene_synonyms": "TARGET1"},
            "exact_synonym",
        ),
    ],
)
def test_ranked_policy_accepts_exact_name_or_safe_synonym(tmp_path, fields, method):
    adapter = _channel_ec_adapter(
        _profile(tmp_path, target_changes={"type": "gpcr", "geneSymbol": "TARGET1"}),
        RANKED_CLASS_POLICY_VERSION,
    )
    result = _classify(adapter, component_accessions=None, **fields)
    assert result.projection["iuphar_target_id"] == "1"
    assert result.projection["iuphar_class"] == "Receptor"
    assert result.projection["effective_class"] == "Receptor"
    outputs = {a.name: json.loads(a.payload) for a in result.artifacts}
    assert method in {row["match_method"] for row in outputs["candidates.json"]}


def test_ranked_synonym_needs_corroboration_when_provider_lacks_anchors(tmp_path):
    adapter = _channel_ec_adapter(
        _profile(
            tmp_path,
            target_changes={
                "uniprotIds": [],
                "geneSymbol": "RIPK2",
                "synonyms": ["CCK"],
            },
        ),
        RANKED_CLASS_POLICY_VERSION,
    )
    result = _classify(adapter, pref_name="Cholecystokinin", target_gene_synonyms="CCK")
    assert result.projection["iuphar_target_id"] is None
    assert result.projection["effective_class"] is None
    rows = json.loads(
        next(a.payload for a in result.artifacts if a.name == "candidates.json")
    )
    assert [row["match_method"] for row in rows] == ["exact_synonym"]


@pytest.mark.parametrize("name", ["known enzyme", "alternate label"])
def test_ranked_text_match_does_not_override_incompatible_uniprot(tmp_path, name):
    target = _profile(tmp_path)
    adapter = _channel_ec_adapter(target, RANKED_CLASS_POLICY_VERSION)
    result = _classify(adapter, pref_name=name, component_accessions="Q9BW60")
    assert result.projection["iuphar_target_id"] is None
    assert result.projection["effective_class"] is None


@pytest.mark.parametrize(
    ("name", "taxonomy_id", "organism", "ec", "label"),
    [
        (
            "Sodium channel protein type 7",
            9606,
            "Homo sapiens",
            "unknown",
            "Ion Channel",
        ),
        (
            "Acetylcholine receptor alpha chain",
            9823,
            "Sus scrofa",
            "unknown",
            "Receptor",
        ),
        (
            "Long chain fatty acid elongase",
            9606,
            "Homo sapiens",
            "3.n2.26.9",
            "Enzyme.Transferase",
        ),
        (
            "Alcohol dehydrogenase",
            9606,
            "Homo sapiens",
            "unknown",
            "Enzyme.Oxidoreductase",
        ),
        ("Cyclin-dependent kinase inhibitor", 9606, "Homo sapiens", "unknown", None),
        (
            "Transmembrane sodium channel and receptor",
            9606,
            "Homo sapiens",
            "unknown",
            None,
        ),
    ],
)
def test_ranked_policy_uses_unambiguous_name_keywords_as_last_fallback(
    tmp_path, name, taxonomy_id, organism, ec, label
):
    adapter = _channel_ec_adapter(_profile(tmp_path), RANKED_CLASS_POLICY_VERSION)
    result = _classify(
        adapter,
        pref_name=name,
        taxonomy_id=taxonomy_id,
        organism=organism,
        target_ec_numbers=ec,
        component_accessions=None,
        target_protein_synonyms=None,
    )
    assert result.projection["iuphar_target_id"] is None
    assert result.projection["effective_class"] == label
    if label:
        assert result.projection["effective_source"] == "keyword_rule"
        assert result.projection["local_class"] == label


@pytest.mark.parametrize(
    ("kwargs", "expected_class", "expected_id"),
    [
        ({"pref_name": "Transcription factor MafG"}, "Receptor.Nuclear receptor", None),
        (
            {
                "pref_name": "Transcription-factor Jun",
                "taxonomy_id": 9913,
                "organism": "Bos taurus",
            },
            "Receptor.Nuclear receptor",
            None,
        ),
        ({"pref_name": "General transcription factor IIF subunit 2"}, None, None),
        ({"pref_name": "Inhibitor of transcription factor Jun"}, None, None),
        ({"pref_name": "Protein binding to transcription factor Jun"}, None, None),
        ({"pref_name": "Protein bound to the transcription factor Jun"}, None, None),
        (
            {"pref_name": "Protein interacting with transcription factor Jun"},
            None,
            None,
        ),
        ({"pref_name": "Protein associated with transcription factor Jun"}, None, None),
        ({"pref_name": "Transcription factor Jun coactivator"}, None, None),
        (
            {"pref_name": "Membrane-bound transcription factor site-1 protease"},
            "Enzyme.Hydrolase",
            None,
        ),
        (
            {
                "pref_name": "Transcription factor MafG",
                "component_accessions": "P12345",
            },
            "Enzyme",
            "1",
        ),
        (
            {
                "pref_name": "Transcription factor MafG",
                "target_ec_numbers": "3.1.26.n2",
            },
            "Enzyme.Hydrolase",
            None,
        ),
    ],
)
def test_global_transcription_factor_fallback(
    tmp_path, kwargs, expected_class, expected_id
):
    adapter = _channel_ec_adapter(
        _profile(tmp_path), TRANSCRIPTION_FACTOR_POLICY_VERSION
    )
    result = _classify(
        adapter,
        **({"component_accessions": None, "target_protein_synonyms": None} | kwargs),
    )
    assert result.projection["effective_class"] == expected_class
    assert result.projection["iuphar_target_id"] == expected_id
    if expected_class == "Receptor.Nuclear receptor":
        assert result.projection["local_class"] == expected_class
        assert result.projection["effective_source"] == "keyword_rule"


def test_older_ranked_policy_keeps_transcription_factor_outcome(tmp_path):
    adapter = _channel_ec_adapter(_profile(tmp_path), RANKED_CLASS_POLICY_VERSION)
    result = _classify(
        adapter,
        pref_name="Transcription factor MafG",
        component_accessions=None,
        target_protein_synonyms=None,
    )
    assert result.projection["effective_class"] is None


def test_current_rule_catalog_records_the_enzyme_subclass(tmp_path):
    profile = _profile(
        tmp_path,
        target_changes={"type": "gpcr"},
        required_target_types=["gpcr"],
        rules_version=LOCAL_RULE_CATALOG_VERSION,
        schema_version="3.2.0",
    )
    adapter = IupharTargetClassificationAdapter(profile, table_contract="3.2.0")
    result = _classify(adapter, target_ec_numbers="3.4.21.1")
    assert profile.classification_schema_version == "3.2.0"
    assert result.projection["iuphar_class"] == "Receptor"
    assert result.projection["effective_class"] == "Receptor"
    assert result.projection["local_class"] == "Enzyme"
    assert result.projection["iuphar_subclasses"] == '["G protein-coupled receptors"]'
    assert (
        result.projection["effective_subclasses"] == '["G protein-coupled receptors"]'
    )
    # Local subclasses stay empty: local inference does not propagate EC
    # subclasses into local_subclasses yet (open subclass-propagation gap).
    assert result.projection["local_subclasses"] == "[]"


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"target_type": "PROTEIN COMPLEX"}, "unsupported_target_type"),
        ({"taxonomy_id": 10116, "organism": "Rattus norvegicus"}, "unsupported_taxon"),
        ({"taxonomy_id": True}, "invalid_taxonomy_id"),
        ({"organism": "Mus musculus"}, "taxonomy_name_conflict"),
        (
            {"taxonomy_id": None, "organism": "Mus musculus"},
            "missing_taxonomy_for_known_organism",
        ),
    ],
)
def test_unsupported_inputs_keep_identity_without_assigning_class(
    tmp_path, changes, reason
):
    result = _classify(IupharTargetClassificationAdapter(_profile(tmp_path)), **changes)
    assert result.input_row_id == "target:1"
    assert result.projection["iuphar_class"] is None
    assert result.diagnostic_codes == (reason,)


def test_chembl_id_does_not_become_explicit_iuphar_id(tmp_path):
    result = _classify(
        IupharTargetClassificationAdapter(_profile(tmp_path)),
        target_id="1",
        component_accessions="unknown",
        pref_name="unknown",
        target_protein_synonyms="unknown",
    )
    assert result.projection["iuphar_target_id"] is None
    assert result.projection["iuphar_class"] is None


def test_batch_results_follow_keys_and_duplicate_identity_is_rejected(tmp_path):
    adapter = IupharTargetClassificationAdapter(_profile(tmp_path))
    rows = (
        TargetClassificationInput("z", _business()),
        TargetClassificationInput("a", _business()),
    )
    batch = adapter.classify_batch(rows, run_id="run", run_started_at="fixed")
    assert tuple(result.input_row_id for result in batch.results) == ("z", "a")
    individual = adapter.classify_record(
        _business(), input_row_id="a", run_id="run", run_started_at="fixed"
    )
    assert batch.results[1].artifacts == individual.artifacts
    with pytest.raises(ValueError, match="duplicate"):
        adapter.classify_batch((rows[0], rows[0]), run_id="run", run_started_at="fixed")


def test_payload_tampering_and_duplicate_json_keys_are_rejected(tmp_path):
    profile = _profile(tmp_path)
    (tmp_path / "targets.json").write_bytes(b"[]")
    with pytest.raises(ValueError, match="digest"):
        load_snapshot_manifest(
            tmp_path / "snapshot.json", profile.snapshot.snapshot_manifest_sha256
        )
    with pytest.raises(ValueError, match="duplicate JSON key"):
        parse_target_payloads(b'[{"targetId":1,"targetId":2}]')


@pytest.mark.parametrize(
    "key,value",
    [
        ("status", "NOT_RUN"),
        ("reference_cases_accepted", False),
        ("snapshot_manifest_sha256", "d" * 64),
    ],
)
def test_receipt_cannot_admit_unexecuted_or_other_snapshot_cases(key, value):
    receipt = {**_receipt("a" * 64), key: value}
    with pytest.raises(ValueError):
        validate_acceptance_receipt(receipt, snapshot_manifest_sha256="a" * 64)


def test_evidence_retries_and_completion_check_expected_rows(tmp_path):
    profile = _profile(tmp_path)
    result = _classify(IupharTargetClassificationAdapter(profile))
    store = LocalTargetClassificationEvidenceStore(
        tmp_path / "evidence",
        snapshot_manifest_sha256=profile.snapshot.snapshot_manifest_sha256,
        profile_sha256=profile.profile_sha256,
    )
    reference = store.publish_result(result, run_id="run-a", batch_id="batch-1")
    assert store.publish_result(result, run_id="run-a", batch_id="batch-1") == reference
    with pytest.raises(ValueError, match="expected rows"):
        store.finalize_run(
            run_id="run-a", expected_row_ids=(result.input_row_id, "missing")
        )
    final = store.finalize_run(run_id="run-a", expected_row_ids=(result.input_row_id,))
    assert (
        store.finalize_run(run_id="run-a", expected_row_ids=(result.input_row_id,))
        == final
    )
    document = json.loads((tmp_path / "evidence/run-a/manifest.json").read_bytes())
    assert document["status"] == "complete" and document["row_count"] == 1
    assert len(document["artifact_sha256"]) == 7
    other = replace(result, input_row_id="new-row")
    with pytest.raises(ValueError, match="already finalized"):
        store.publish_result(other, run_id="run-a", batch_id="batch-1")


def test_evidence_conflicting_retry_is_not_overwritten(tmp_path):
    profile = _profile(tmp_path)
    result = _classify(IupharTargetClassificationAdapter(profile))
    store = LocalTargetClassificationEvidenceStore(
        tmp_path / "evidence",
        snapshot_manifest_sha256=profile.snapshot.snapshot_manifest_sha256,
        profile_sha256=profile.profile_sha256,
    )
    store.publish_result(result, run_id="run-a", batch_id="batch-1")
    changed = replace(
        result,
        artifacts=tuple(
            TargetClassificationArtifact(item.name, b'{"rows":7}')
            if item.name == "metrics.json"
            else item
            for item in result.artifacts
        ),
    )
    with pytest.raises(ValueError, match="conflicting"):
        store.publish_result(changed, run_id="run-a", batch_id="batch-1")


def test_evidence_cannot_be_published_under_another_run(tmp_path):
    profile = _profile(tmp_path)
    result = _classify(IupharTargetClassificationAdapter(profile))
    store = LocalTargetClassificationEvidenceStore(
        tmp_path / "evidence",
        snapshot_manifest_sha256=profile.snapshot.snapshot_manifest_sha256,
        profile_sha256=profile.profile_sha256,
    )
    with pytest.raises(ValueError, match="another run"):
        store.publish_result(result, run_id="run-b", batch_id="batch-1")


def test_profile_cannot_claim_an_unexecuted_normalization_version(tmp_path):
    profile = _profile(tmp_path)
    document = json.loads((tmp_path / "profile.json").read_bytes())
    document["normalization_version"] = "unexecuted-rules"
    reference = _write(tmp_path, "profile.json", document)
    with pytest.raises(ValueError, match="executing adapter"):
        load_profile(
            tmp_path / "profile.json", reference["sha256"], require_acceptance=False
        )
