# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Tests for deterministic protein-class target type derivation."""

from __future__ import annotations

import pytest

from bioetl.domain.mapping import protein_class_target_type as mapping_module
from bioetl.domain.mapping import protein_class_target_type_helpers as helper_module
from bioetl.domain.mapping.protein_class_target_type import (
    ProteinClassTargetTypeMappingData,
    ProteinClassTopLevelMappingEntry,
    current_protein_class_target_type_mapping,
    derive_major_families,
    derive_protein_class_target_type,
    initialize_protein_class_target_type_mapping,
    is_protein_class_target_type_mapping_initialized,
    normalize_protein_class_label,
    normalize_protein_class_top_level,
)

pytestmark = pytest.mark.unit


def _mapping_data() -> ProteinClassTargetTypeMappingData:
    return ProteinClassTargetTypeMappingData(
        mapping_version="protein_class_l1_map_v1",
        entries=(
            ProteinClassTopLevelMappingEntry("Enzyme", "enzyme", True),
            ProteinClassTopLevelMappingEntry("Ion channel", "ion_channel", True),
            ProteinClassTopLevelMappingEntry(
                "Transporter",
                "transporter",
                True,
            ),
            ProteinClassTopLevelMappingEntry(
                "Membrane receptor",
                "membrane_receptor",
                True,
            ),
            ProteinClassTopLevelMappingEntry(
                "Transcription factor",
                "transcription_factor",
                True,
            ),
            ProteinClassTopLevelMappingEntry(
                "Epigenetic regulator",
                "epigenetic_regulator",
                True,
            ),
            ProteinClassTopLevelMappingEntry(
                "Auxiliary transport protein",
                "auxiliary_transport_protein",
                True,
            ),
            ProteinClassTopLevelMappingEntry(
                "Secreted protein", "secreted_protein", True
            ),
            ProteinClassTopLevelMappingEntry("Adhesion", "adhesion", True),
            ProteinClassTopLevelMappingEntry(
                "Unclassified protein",
                "unclassified_protein",
                False,
            ),
        ),
    )


@pytest.mark.parametrize(
    ("rows", "expected_type", "expected_count"),
    [
        ([{"l1": "Enzyme", "l2": "Kinase"}], "enzyme", 1),
        (
            [{"l1": "Membrane receptor", "l2": "Family A G protein-coupled receptor"}],
            "membrane_receptor",
            1,
        ),
        (
            [{"l1": "Transcription factor", "l2": "Nuclear receptor"}],
            "transcription_factor",
            1,
        ),
        (
            [{"l1": "Enzyme", "l2": "Kinase"}, {"l1": "Enzyme", "l2": "Hydrolase"}],
            "enzyme",
            1,
        ),
        (
            [
                {"l1": "Epigenetic regulator", "l2": "Writer"},
                {"l1": "Epigenetic regulator", "l2": "Reader"},
            ],
            "epigenetic_regulator",
            1,
        ),
        (
            [{"l1": "Unclassified protein"}, {"l1": "Ion channel"}],
            "ion_channel",
            1,
        ),
        ([{"l1": "Ion channel"}, {"l1": "Transporter"}], "multifunctional", 2),
        (
            [{"l1": "Auxiliary transport protein"}, {"l1": "Ion channel"}],
            "multifunctional",
            2,
        ),
        ([{"l1": "Adhesion"}, {"l1": "Secreted protein"}], "multifunctional", 2),
        ([{"l1": "Unclassified protein"}], "unknown", 0),
        ([], "unknown", 0),
        ([{"level_1": "  Ion   channel "}, {"l1": "Ion channel"}], "ion_channel", 1),
        ([{"l1": "Scaffold protein"}], "other_classified_protein", 1),
        ([{"l1": None}, {"l1": "Unclassified protein"}], "unknown", 0),
    ],
)
def test_derive_target_type_strategy_cases(
    rows: list[dict[str, object]],
    expected_type: str,
    expected_count: int,
) -> None:
    result = derive_protein_class_target_type(rows, _mapping_data())

    assert result.target_protein_class_type == expected_type
    assert result.top_level_count == expected_count


def test_normalize_top_level_exposes_fallback_status() -> None:
    result = normalize_protein_class_top_level("Scaffold protein", _mapping_data())

    assert result.canonical_l1 == "other_classified_protein"
    assert result.counts_for_target_type is True
    assert result.normalization_status == "fallback"


def test_major_family_uses_deeper_levels_without_overriding_l1() -> None:
    rows = [
        {"l1": "Membrane receptor", "l2": "Family A G protein-coupled receptor"},
        {"l1": "Transcription factor", "l2": "Nuclear receptor"},
        {"l1": "Enzyme", "l3": "Serine/threonine kinase"},
    ]

    assert derive_major_families(rows) == ("gpcr", "kinase", "nuclear_receptor")


@pytest.mark.parametrize(
    ("mapping_version", "entries", "match"),
    [
        (" ", (ProteinClassTopLevelMappingEntry("Enzyme", "enzyme", True),), "blank"),
        ("v1", (), "must not be empty"),
        (
            "v1",
            (
                ProteinClassTopLevelMappingEntry("Enzyme", "enzyme", True),
                ProteinClassTopLevelMappingEntry(" enzyme ", "enzyme", True),
            ),
            "duplicate",
        ),
        (
            "v1",
            (ProteinClassTopLevelMappingEntry(" ", "missing", False),),
            "must not be blank",
        ),
    ],
)
def test_mapping_data_rejects_invalid_contracts(
    mapping_version: str,
    entries: tuple[ProteinClassTopLevelMappingEntry, ...],
    match: str,
) -> None:
    with pytest.raises(ValueError, match=match):
        ProteinClassTargetTypeMappingData(
            mapping_version=mapping_version,
            entries=entries,
        )


def test_current_mapping_fails_closed_before_initialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(mapping_module, "_mapping_data", None)

    assert is_protein_class_target_type_mapping_initialized() is False
    with pytest.raises(RuntimeError, match="not initialized"):
        current_protein_class_target_type_mapping()


def test_initialize_current_mapping_round_trips_domain_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = _mapping_data()
    monkeypatch.setattr(mapping_module, "_mapping_data", None)

    initialize_protein_class_target_type_mapping(data)

    assert is_protein_class_target_type_mapping_initialized() is True
    assert current_protein_class_target_type_mapping() is data


def test_canonical_rows_drive_counting_defaults_and_bool_coercion() -> None:
    rows = [
        {
            "canonical_l1": "enzyme",
            "l1_counts_for_target_type": "yes",
            "level_1": " Enzyme ",
            "l1_normalization_status": " ",
        },
        {
            "canonical_l1": "unclassified_protein",
            "l1_counts_for_target_type": "no",
            "l1": "Unclassified protein",
        },
        {
            "canonical_l1": "transporter",
            "l1_counts_for_target_type": 0,
            "level1": "Transporter",
        },
        {
            "canonical_l1": "ion_channel",
            "l1_counts_for_target_type": "maybe",
            "l1_name": "",
        },
        {},
    ]

    result = derive_protein_class_target_type(rows, _mapping_data())

    assert result.target_protein_class_type == "multifunctional"
    assert result.counted_top_levels == ("enzyme", "ion_channel")
    assert result.ignored_top_levels == (
        "missing",
        "transporter",
        "unclassified_protein",
    )


@pytest.mark.unit
def test_helper_module_covers_decision_and_normalization_edges() -> None:
    assert helper_module.target_type_decision(
        (),
        multifunctional_class=helper_module.MULTIFUNCTIONAL_CLASS,
        unknown_target_type=helper_module.UNKNOWN_TARGET_TYPE,
    ) == ("unknown", None, "no_informative_top_level")
    assert helper_module.target_type_decision(
        ("enzyme",),
        multifunctional_class=helper_module.MULTIFUNCTIONAL_CLASS,
        unknown_target_type=helper_module.UNKNOWN_TARGET_TYPE,
    ) == ("enzyme", "enzyme", "single_informative_top_level")
    assert helper_module.target_type_decision(
        ("enzyme", "ion_channel"),
        multifunctional_class=helper_module.MULTIFUNCTIONAL_CLASS,
        unknown_target_type=helper_module.UNKNOWN_TARGET_TYPE,
    ) == ("multifunctional", None, "multiple_informative_top_levels")

    rows = (
        {"l2": " Family A G protein-coupled receptor "},
        {"level_3": "Serine/threonine kinase"},
        {"level_4": "Nuclear receptor"},
    )
    assert helper_module.normalized_deeper_level_labels(
        rows,
        normalize_label=normalize_protein_class_label,
    ) == (
        "family a g protein-coupled receptor",
        "nuclear receptor",
        "serine/threonine kinase",
    )
    assert helper_module.matching_major_families(
        "family a g protein-coupled receptor"
    ) == ("gpcr",)
    assert helper_module.matching_major_families("nuclear receptor kinase") == (
        "kinase",
        "nuclear_receptor",
    )
    assert (
        helper_module.first_normalized_label(
            {"l1": "  Ion   channel "},
            ("l1", "l2"),
            normalize_label=normalize_protein_class_label,
        )
        == "ion channel"
    )
    assert (
        helper_module.first_present_value(
            {"l1": None, "level_1": "Transporter"},
            ("l1", "level_1"),
        )
        == "Transporter"
    )
    assert (
        helper_module.coerce_counts_for_target_type(
            "yes",
            default=False,
            normalize_label=normalize_protein_class_label,
        )
        is True
    )
    assert (
        helper_module.coerce_counts_for_target_type(
            "unknown-token",
            default=False,
            normalize_label=normalize_protein_class_label,
        )
        is False
    )
    assert (
        helper_module.normalized_status(
            " ",
            normalize_label=normalize_protein_class_label,
        )
        == "ok"
    )


@pytest.mark.unit
def test_helper_module_covers_fallback_and_none_paths() -> None:
    missing = helper_module.missing_top_level(
        mapping_module.NormalizedProteinClassTopLevel
    )
    assert missing.canonical_l1 == helper_module.MISSING_CLASS
    assert missing.counts_for_target_type is False
    assert missing.normalization_status == "missing"

    fallback = helper_module.fallback_top_level(
        "Scaffold protein",
        mapping_module.NormalizedProteinClassTopLevel,
    )
    assert fallback.canonical_l1 == helper_module.UNKNOWN_NONEMPTY_CLASS
    assert fallback.counts_for_target_type is True
    assert fallback.normalization_status == "fallback"

    non_counting_entry = ProteinClassTopLevelMappingEntry(
        "Unclassified protein",
        "unclassified_protein",
        False,
    )
    mapped = helper_module.mapped_top_level(
        "Unclassified protein",
        non_counting_entry,
        mapping_module.NormalizedProteinClassTopLevel,
    )
    assert mapped.canonical_l1 == "unclassified_protein"
    assert mapped.counts_for_target_type is False
    assert mapped.normalization_status == "non_counting"

    assert (
        helper_module.coerce_counts_for_target_type(
            None,
            default=True,
            normalize_label=normalize_protein_class_label,
        )
        is True
    )
    assert (
        helper_module.coerce_counts_for_target_type(
            True,
            default=False,
            normalize_label=normalize_protein_class_label,
        )
        is True
    )
    assert (
        helper_module.coerce_counts_for_target_type(
            " ",
            default=False,
            normalize_label=normalize_protein_class_label,
        )
        is False
    )
    assert (
        helper_module.first_normalized_label(
            {"l1": " ", "l2": None},
            ("l1", "l2"),
            normalize_label=normalize_protein_class_label,
        )
        is None
    )
    assert helper_module.first_present_value({"l1": None}, ("l1", "l2")) is None


@pytest.mark.parametrize("canonical", ["", " ", "\t\n"])
def test_mapping_entry_rejects_blank_canonical_label(canonical):
    with pytest.raises(ValueError, match="canonical_l1 must not be blank"):
        ProteinClassTopLevelMappingEntry("enzyme", canonical, True)


def test_mapping_scope_restores_nested_and_uninitialized_context(monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(mapping_module, "_mapping_data", None)
    outer = _mapping_data()
    inner = replace(outer, mapping_version="historical-v2")
    with mapping_module.scoped_protein_class_target_type_mapping(outer):
        assert is_protein_class_target_type_mapping_initialized()
        with pytest.raises(ValueError, match="replay failed"):
            with mapping_module.scoped_protein_class_target_type_mapping(inner):
                assert current_protein_class_target_type_mapping() is inner
                raise ValueError("replay failed")
        assert current_protein_class_target_type_mapping() is outer
    assert not is_protein_class_target_type_mapping_initialized()
    with pytest.raises(RuntimeError, match="not initialized"):
        current_protein_class_target_type_mapping()


async def test_mapping_scopes_isolate_concurrent_tasks_and_cancellation(monkeypatch):
    import asyncio
    from dataclasses import replace

    default = _mapping_data()
    monkeypatch.setattr(mapping_module, "_mapping_data", default)
    arrived = 0
    ready = asyncio.Event()

    async def worker(data):
        nonlocal arrived
        with mapping_module.scoped_protein_class_target_type_mapping(data):
            arrived += 1
            if arrived == 2:
                ready.set()
            await ready.wait()
            await asyncio.sleep(0)
            assert current_protein_class_target_type_mapping() is data
        assert current_protein_class_target_type_mapping() is default

    await asyncio.gather(
        worker(replace(default, mapping_version="first")),
        worker(replace(default, mapping_version="second")),
    )
    entered = asyncio.Event()

    async def cancelled_worker():
        try:
            with mapping_module.scoped_protein_class_target_type_mapping(
                replace(default, mapping_version="cancelled")
            ):
                entered.set()
                await asyncio.Event().wait()
        finally:
            assert current_protein_class_target_type_mapping() is default

    task = asyncio.create_task(cancelled_worker())
    await entered.wait()
    assert current_protein_class_target_type_mapping() is default
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert current_protein_class_target_type_mapping() is default


def test_explicit_mappings_stay_isolated_from_each_other() -> None:
    enzyme = ProteinClassTargetTypeMappingData(
        "enzyme-v1",
        (ProteinClassTopLevelMappingEntry("Enzyme", "enzyme", True),),
    )
    channel = ProteinClassTargetTypeMappingData(
        "channel-v1",
        (ProteinClassTopLevelMappingEntry("Ion channel", "ion_channel", True),),
    )
    assert normalize_protein_class_top_level("Enzyme", enzyme).canonical_l1 == "enzyme"
    assert (
        normalize_protein_class_top_level("Ion channel", channel).canonical_l1
        == "ion_channel"
    )
    with pytest.raises(RuntimeError, match="passed explicitly"):
        normalize_protein_class_top_level("Enzyme")
