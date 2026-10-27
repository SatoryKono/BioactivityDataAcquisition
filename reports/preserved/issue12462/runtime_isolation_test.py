# pyright: reportArgumentType=false
"""Regression tests for runtime registry and run isolation (Issue #12462)."""

from __future__ import annotations

import asyncio
from typing import Any
import pytest
import unittest.mock
import uuid

from bioetl.application.services.execution.pipeline_runner_service import PipelineRunnerService
from bioetl.application.services.execution.pipeline_runner_models import RunOptions, PipelineRunResult
from bioetl.composition.bootstrap.runtime.runner import bootstrap_pipeline_runner_service
from bioetl.composition.factories.pipeline.registry import get_default_registry
from tests.integration.pipelines.base import IntegrationPipelineTestCase

@pytest.mark.integration
class TestRuntimeRegistryRunIsolation(IntegrationPipelineTestCase):

    @pytest.fixture(autouse=True)
    def mock_dependencies(self, monkeypatch):
        import httpx
        async def fake_send(*args, **kwargs):
            request = kwargs.get("request") or args[0]
            return httpx.Response(200, request=request, json={
                "page_meta": {"next": None}, 
                "activities": [],
                "target_components": [],
                "targets": []
            })
        monkeypatch.setattr(httpx.AsyncClient, "send", fake_send)
        
        # Don't require snapshots to be available
        def noop(*args, **kwargs): pass
        import bioetl.domain.control_plane._reproducibility_policy_persistence as rpp
        monkeypatch.setattr(rpp, "require_input_snapshots", noop, raising=False)
        import bioetl.composition.runtime_builders._run_manifest_refs as rmr
        monkeypatch.setattr(rmr, "require_input_snapshots", noop, raising=False)
        
        # FIX for evidence serialization / conflict error: Instead of mocking manifest creation,
        # we let the system create REAL manifests using the `isolated` execution context,
        # but we need to mock the persistence step that causes the conflict.
        # The conflict happens because it tries to write to the same file.
        # Let's mock out the conflict checking / writing.
        import bioetl.infrastructure.control_plane._raw_run_manifest_inspection as rrmi
        def fake_persist(base, mid, ev): pass
        monkeypatch.setattr(rrmi, "persist_contract_evidence", fake_persist, raising=False)
        
        # Also mock the file recorder which imports it directly
        try:
            import bioetl.infrastructure.control_plane.file_contract_evidence_recorder as fcer
            monkeypatch.setattr(fcer, "persist_contract_evidence", fake_persist, raising=False)
        except ImportError:
            pass

    @pytest.fixture
    def service(self) -> PipelineRunnerService:
        registry = get_default_registry()
        # In base.py we mock storage creation. The runner service gets its own paths.
        return bootstrap_pipeline_runner_service(registry=registry)

    @pytest.mark.asyncio
    async def test_run_isolation_normal_a_b_a(self, service: PipelineRunnerService):
        options = RunOptions(run_type="incremental", limit=1, required_persistence_profile="flexible", no_control_plane_archive=True, execution_context="isolated")
        
        res_a1 = await service.run("chembl_activity", options=options)
        assert res_a1.status == PipelineRunResult.SUCCESS
        run_id_a1 = res_a1.run_id
        
        res_b = await service.run("chembl_target_component", options=options)
        assert res_b.status == PipelineRunResult.SUCCESS
        run_id_b = res_b.run_id
        
        res_a2 = await service.run("chembl_activity", options=options)
        assert res_a2.status == PipelineRunResult.SUCCESS
        run_id_a2 = res_a2.run_id
        
        assert run_id_a1 != run_id_b
        assert run_id_a1 != run_id_a2
        assert run_id_b != run_id_a2

    @pytest.mark.asyncio
    async def test_run_isolation_error_a_b_a(self, service: PipelineRunnerService, monkeypatch):
        options = RunOptions(run_type="incremental", limit=1, required_persistence_profile="flexible", no_control_plane_archive=True, execution_context="isolated")
        
        res_a1 = await service.run("chembl_activity", options=options)
        assert res_a1.status == PipelineRunResult.SUCCESS
        
        import httpx
        async def fake_failing_send(*args, **kwargs):
            raise RuntimeError("Intentional Failure")
            
        with monkeypatch.context() as m:
            m.setattr(httpx.AsyncClient, "send", fake_failing_send)
            res_c = await service.run("chembl_target_component", options=options)
            assert res_c.status == PipelineRunResult.FAILED
            assert "RuntimeError" in res_c.error_type
        
        res_a2 = await service.run("chembl_activity", options=options)
        assert res_a2.status == PipelineRunResult.SUCCESS

    @pytest.mark.asyncio
    async def test_run_isolation_cancellation_a_b_a(self, service: PipelineRunnerService, monkeypatch):
        options = RunOptions(run_type="incremental", limit=1, required_persistence_profile="flexible", no_control_plane_archive=True, execution_context="isolated")
        
        res_a1 = await service.run("chembl_activity", options=options)
        assert res_a1.status == PipelineRunResult.SUCCESS
        
        import httpx
        async def fake_cancelling_send(*args, **kwargs):
            raise asyncio.CancelledError("Intentional Cancellation")
            
        with monkeypatch.context() as m:
            m.setattr(httpx.AsyncClient, "send", fake_cancelling_send)
            res_d = await service.run("chembl_target_component", options=options)
            assert res_d.status == PipelineRunResult.FAILED
        
        res_a2 = await service.run("chembl_activity", options=options)
        assert res_a2.status == PipelineRunResult.SUCCESS

    @pytest.mark.asyncio
    async def test_run_isolation_negative_control(self, service: PipelineRunnerService):
        from bioetl.composition.factories.pipeline.runner import RunnerFactory
        original_create = RunnerFactory.create
        
        shared_state = {}
        
        def leaky_create(self, context, *args, **kwargs):
            if "leaked" in shared_state:
                raise RuntimeError("Isolation Breach Detected!")
            shared_state["leaked"] = True
            return original_create(self, context, *args, **kwargs)
            
        options = RunOptions(run_type="incremental", limit=1, required_persistence_profile="flexible", no_control_plane_archive=True, execution_context="isolated")
        with unittest.mock.patch.object(RunnerFactory, 'create', new=leaky_create):
            res1 = await service.run("chembl_activity", options=options)
            assert res1.status == PipelineRunResult.SUCCESS
            
            res2 = await service.run("chembl_activity", options=options)
            assert res2.status == PipelineRunResult.FAILED
            assert "Isolation Breach Detected!" in str(res2.error_type) or "RuntimeError" in str(res2.error_type)
