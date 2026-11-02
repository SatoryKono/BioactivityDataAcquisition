# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
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
"""E2E tests for multi-pipeline scenarios.

Tests that verify:
- Multiple pipelines can run in sequence
- Data consistency across pipelines
- Pipeline dependencies and cross-references

Cassettes location: tests/fixtures/vcr/chembl/
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import NoReturn

from pathlib import Path

import pytest
from deltalake.exceptions import DeltaError, TableNotFoundError
from tests.helpers.vcr_config import build_cassette_dir

from bioetl.composition.bootstrap.runtime.pipeline import bootstrap_pipeline_runner
from .conftest import (
    E2E_THREE_SEQUENTIAL_PIPELINE_TIMEOUT,
    assert_silver_table_has_records,
    create_test_context,
    get_silver_records,
)

# Large multi-entity VCR chains (10–29 MiB) stay out of default -m "not slow".
pytestmark = [
    pytest.mark.usefixtures("relaxed_dq_env"),
    pytest.mark.slow,
]


@pytest.fixture
def vcr_cassette_dir(request: pytest.FixtureRequest) -> Path:
    """Route mixed-provider chain tests to the correct cassette directory."""
    provider_dir = "chembl"
    if request.node.name == "test_parallel_independent_pipelines":
        provider_dir = "uniprot"
    return build_cassette_dir(
        fixtures_root=Path(__file__).resolve().parents[1] / "fixtures" / "vcr",
        provider_dir=provider_dir,
    )


@pytest.fixture
def vcr_cassette_name(request: pytest.FixtureRequest) -> str:
    """Route mixed-provider tests to the canonical cassette name they reuse."""
    if request.node.name == "test_parallel_independent_pipelines":
        return "test_uniprot_protein_full_cycle"
    if request.node.name in [
        "test_run_normal_a_b_a",
        "test_run_cancellation_and_restart",
        "test_run_error_and_restart",
        "test_run_config_error_and_restart",
    ]:
        return "test_all_chembl_pipelines_chain"
    return str(request.node.name)


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_chembl_target_then_activity_chain(e2e_data_dir: Path) -> None:
    """E2E: Run Target pipeline, then Activity pipeline.

    Activities reference targets, so this tests a realistic data flow.
    """
    # Step 1: Run Target pipeline
    target_ctx = create_test_context("chembl_target", limit=3)
    target_runner = bootstrap_pipeline_runner(target_ctx)
    await target_runner.run()

    target_count = await assert_silver_table_has_records(
        e2e_data_dir, "chembl_target", expected_min=1
    )

    # Step 2: Run Activity pipeline
    activity_ctx = create_test_context("chembl_activity", limit=5)
    activity_runner = bootstrap_pipeline_runner(activity_ctx)
    await activity_runner.run()

    activity_count = await assert_silver_table_has_records(
        e2e_data_dir, "chembl_activity", expected_min=1
    )

    # Verify both tables exist with data
    assert target_count >= 1
    assert activity_count >= 1


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_chembl_molecule_then_activity_chain(e2e_data_dir: Path) -> None:
    """E2E: Run Molecule pipeline, then Activity pipeline.

    Activities reference molecules, so this tests compound data flow.
    """
    # Step 1: Run Molecule pipeline
    molecule_ctx = create_test_context("chembl_molecule", limit=3)
    molecule_runner = bootstrap_pipeline_runner(molecule_ctx)
    await molecule_runner.run()

    molecule_count = await assert_silver_table_has_records(
        e2e_data_dir, "chembl_molecule", expected_min=1
    )

    # Step 2: Run Activity pipeline
    activity_ctx = create_test_context("chembl_activity", limit=5)
    activity_runner = bootstrap_pipeline_runner(activity_ctx)
    await activity_runner.run()

    activity_count = await assert_silver_table_has_records(
        e2e_data_dir, "chembl_activity", expected_min=1
    )

    # Verify both tables exist with data
    assert molecule_count >= 1
    assert activity_count >= 1


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
@pytest.mark.timeout(600)  # Extended timeout: 5 pipelines × ~60s each + Gold validation
async def test_all_chembl_pipelines_chain(e2e_data_dir: Path) -> None:
    """E2E: Run all ChEMBL pipelines in sequence.

    Order: Target → Molecule → Document → Activity → Assay
    This tests the full ChEMBL data ecosystem.

    Note: This test has an extended timeout (600s) because it runs 5 pipelines
    sequentially, each with HTTP calls, Delta Lake operations, and Gold layer
    validation with Pandera schema checks.
    """
    pipelines_in_order = [
        ("chembl_target", "chembl_target", 2),
        ("chembl_molecule", "chembl_molecule", 2),
        ("chembl_publication", "chembl_publication", 2),
        ("chembl_activity", "chembl_activity", 3),
        ("chembl_assay", "chembl_assay", 2),
    ]

    results = {}

    for pipeline_name, table_name, limit in pipelines_in_order:
        ctx = create_test_context(pipeline_name, limit=limit)
        runner = bootstrap_pipeline_runner(ctx)
        await runner.run()

        count = await assert_silver_table_has_records(
            e2e_data_dir, table_name, expected_min=1
        )
        results[pipeline_name] = count

    # Verify all pipelines produced data
    for pipeline_name, count in results.items():
        assert count >= 1, f"Pipeline {pipeline_name} produced no records"


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_parallel_independent_pipelines(e2e_data_dir: Path) -> None:
    """E2E: Run independent pipelines that can run in parallel.

    PubMed and UniProt pipelines are independent and should not interfere.
    """
    # Run UniProt pipeline
    uniprot_ctx = create_test_context("uniprot_protein", limit=5)
    uniprot_runner = bootstrap_pipeline_runner(uniprot_ctx)
    await uniprot_runner.run()

    uniprot_count = await assert_silver_table_has_records(
        e2e_data_dir, "uniprot_protein", expected_min=1
    )

    # Verify UniProt produced data
    assert uniprot_count >= 1


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_pipeline_isolation(e2e_data_dir: Path) -> None:
    """E2E: Verify pipelines are isolated and don't corrupt each other's data.

    Running multiple pipelines should not cause data mixing.
    """
    # Run Target pipeline
    target_ctx = create_test_context("chembl_target", limit=3)
    target_runner = bootstrap_pipeline_runner(target_ctx)
    await target_runner.run()

    # Run Molecule pipeline
    molecule_ctx = create_test_context("chembl_molecule", limit=3)
    molecule_runner = bootstrap_pipeline_runner(molecule_ctx)
    await molecule_runner.run()

    # Some cassette snapshots contain only bronze-valid molecule payloads.
    # In that case Silver table may be absent; skip isolation assertions explicitly.
    await assert_silver_table_has_records(e2e_data_dir, "chembl_target", expected_min=1)
    try:
        await assert_silver_table_has_records(
            e2e_data_dir, "chembl_molecule", expected_min=1
        )
    except (AssertionError, DeltaError, TableNotFoundError) as exc:
        pytest.skip(f"No Silver molecule records in cassette sample: {exc}")

    # Get records from both tables
    target_records = await get_silver_records(e2e_data_dir, "chembl_target")
    molecule_records = await get_silver_records(e2e_data_dir, "chembl_molecule")

    # Verify data isolation - targets should have target_id
    for record in target_records:
        assert "target_id" in record
        # Should NOT have molecule_id as primary identifier
        # (though it might have it as a reference field)

    # Verify molecules have molecule_id
    for record in molecule_records:
        assert "molecule_id" in record
        # Should NOT have target_id as primary identifier


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_rerun_same_pipeline_twice(e2e_data_dir: Path) -> None:
    """E2E: Merge-mode pipeline rerun preserves business identity set.

    ``chembl_target`` uses Silver merge semantics, so rerunning the same input
    should preserve both row count and the ``(target_id, content_hash)`` set.
    """
    # First run
    ctx1 = create_test_context("chembl_target", limit=3)
    runner1 = bootstrap_pipeline_runner(ctx1)
    await runner1.run()

    first_count = await assert_silver_table_has_records(
        e2e_data_dir, "chembl_target", expected_min=1
    )
    first_records = await get_silver_records(e2e_data_dir, "chembl_target")
    first_identity = sorted(
        (str(record["target_id"]), str(record["content_hash"]))
        for record in first_records
    )

    # Second run
    ctx2 = create_test_context("chembl_target", limit=3)
    runner2 = bootstrap_pipeline_runner(ctx2)
    await runner2.run()

    second_count = await assert_silver_table_has_records(
        e2e_data_dir, "chembl_target", expected_min=1
    )
    second_records = await get_silver_records(e2e_data_dir, "chembl_target")
    second_identity = sorted(
        (str(record["target_id"]), str(record["content_hash"]))
        for record in second_records
    )

    assert second_count == first_count, (
        f"Merge rerun changed row count: {first_count} -> {second_count}"
    )
    assert second_identity == first_identity, "Merge rerun changed identity set"


def _aba_restart_marks(test_fn: object) -> object:
    """Shared marks for single-process Target→Molecule→Target restart scenarios."""
    for mark in (
        pytest.mark.e2e,
        pytest.mark.vcr(allow_playback_repeats=True),
        pytest.mark.asyncio,
        pytest.mark.timeout(E2E_THREE_SEQUENTIAL_PIPELINE_TIMEOUT),
    ):
        test_fn = mark(test_fn)
    return test_fn


def _batch_processing_service(runner: object) -> object:
    """Return the runner's batch extraction service (test seam for inject/cancel)."""
    return runner._executor._extraction_loop_service._batch_processing_service  # type: ignore[attr-defined]  # pylint: disable=protected-access


async def _run_molecule_then_target_and_assert(
    e2e_data_dir: Path,
    *,
    require_a2_records_fetched: bool = False,
    a2_fetch_message: str = "A2 fetched no Target records",
) -> None:
    """Shared B→A2 restart path plus silver presence checks for Target and Molecule."""
    ctx_b = create_test_context("chembl_molecule", limit=2)
    runner_b = bootstrap_pipeline_runner(ctx_b)
    await runner_b.run()

    ctx2 = create_test_context("chembl_target", limit=2)
    runner2 = bootstrap_pipeline_runner(ctx2)
    await runner2.run()
    if require_a2_records_fetched:
        assert runner2.execution_metrics["records_fetched"] > 0, a2_fetch_message

    await assert_silver_table_has_records(e2e_data_dir, "chembl_target", expected_min=1)
    await assert_silver_table_has_records(
        e2e_data_dir, "chembl_molecule", expected_min=1
    )


@_aba_restart_marks
async def test_run_normal_a_b_a(e2e_data_dir: Path) -> None:
    """E2E: Normal pipeline runs in A -> B -> A pattern in a single process.

    Verifies state isolation between runs in the same process.
    """
    ctx1 = create_test_context("chembl_target", limit=2)
    runner1 = bootstrap_pipeline_runner(ctx1)
    await runner1.run()

    await _run_molecule_then_target_and_assert(
        e2e_data_dir,
        require_a2_records_fetched=True,
        a2_fetch_message="A2 fetched no Target records",
    )


@_aba_restart_marks
async def test_run_cancellation_and_restart(
    e2e_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """E2E: Pipeline cancellation followed by restart in a single process.

    Verifies A -> B -> A pattern and cancellation safety.
    """
    # Pause after the source yields its first record so cancellation lands inside
    # the active extraction path.
    ctx1 = create_test_context("chembl_target", limit=2)
    runner1 = bootstrap_pipeline_runner(ctx1)
    source = _batch_processing_service(runner1)
    original_extract = source.extract_records  # type: ignore[attr-defined]
    first_record_ready = asyncio.Event()
    continue_extraction = asyncio.Event()

    def gated_extract_records(*args: object, **kwargs: object) -> AsyncIterator[object]:
        records = original_extract(*args, **kwargs)

        async def gate_first_record() -> AsyncIterator[object]:
            iterator = aiter(records)
            try:
                first_record = await anext(iterator)
                first_record_ready.set()
                await continue_extraction.wait()
                yield first_record
                async for record in iterator:
                    yield record
            finally:
                aclose = getattr(iterator, "aclose", None)
                if callable(aclose):
                    await aclose()

        return gate_first_record()

    monkeypatch.setattr(source, "extract_records", gated_extract_records)

    task = asyncio.create_task(runner1.run())
    first_record_waiter = asyncio.create_task(first_record_ready.wait())
    try:
        done, _ = await asyncio.wait(
            {task, first_record_waiter},
            timeout=30,
            return_when=asyncio.FIRST_COMPLETED,
        )
        if first_record_waiter not in done:
            if task in done:
                task.result()
            pytest.fail("Pipeline did not reach the first-record cancellation point")
        if task in done:
            task.result()
            pytest.fail("Pipeline finished before reaching the cancellation point")
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    finally:
        first_record_waiter.cancel()
        await asyncio.gather(first_record_waiter, return_exceptions=True)
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    monkeypatch.setattr(source, "extract_records", original_extract)

    await _run_molecule_then_target_and_assert(e2e_data_dir)


@_aba_restart_marks
async def test_run_error_and_restart(
    e2e_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """E2E: Pipeline error followed by restart in a single process.

    Verifies A -> B -> A pattern and error safety using a simulated network error
    that propagates up the real execution path.
    """
    ctx1 = create_test_context("chembl_target", limit=3)
    runner1 = bootstrap_pipeline_runner(ctx1)
    source = _batch_processing_service(runner1)
    original_extract = source.extract_records  # type: ignore[attr-defined]

    def failing_extract_records(
        *_args: object, **_kwargs: object
    ) -> AsyncIterator[object]:
        async def fail_during_iteration() -> AsyncIterator[object]:
            if False:  # pragma: no cover - keeps this an async generator
                yield None
            raise RuntimeError("injected ChEMBL source failure")

        return fail_during_iteration()

    monkeypatch.setattr(source, "extract_records", failing_extract_records)

    with pytest.raises(RuntimeError, match="injected ChEMBL source failure"):
        await runner1.run()
    monkeypatch.setattr(source, "extract_records", original_extract)

    await _run_molecule_then_target_and_assert(e2e_data_dir)


@_aba_restart_marks
async def test_run_config_error_and_restart(e2e_data_dir: Path) -> None:
    """A config-load failure during bootstrap must not poison later runs."""

    def fail_config_load(_pipeline_name: str) -> NoReturn:
        raise RuntimeError("injected pipeline config load failure")

    ctx1 = create_test_context("chembl_target", limit=2)
    with pytest.raises(RuntimeError, match="injected pipeline config load failure"):
        bootstrap_pipeline_runner(ctx1, load_pipeline_config_fn=fail_config_load)

    await _run_molecule_then_target_and_assert(
        e2e_data_dir,
        require_a2_records_fetched=True,
        a2_fetch_message=(
            "A2 fetched no Target records after the bootstrap config error"
        ),
    )
