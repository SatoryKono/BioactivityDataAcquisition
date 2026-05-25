"""Split strict-profile and control-plane manifest tests for runtime runner builder."""

from __future__ import annotations

# ruff: noqa: F403,F405
from tests.unit.composition.runtime_builders.runner_builder_test_support import *  # noqa: F403,F405

def test_build_pipeline_runner_rejects_exact_replay_without_materialized_cached_bronze_batches(
    tmp_path: Path,
) -> None:
    """Exact replay must fail closed when cached-Bronze snapshots are missing."""
    fake_factory = _FakeFactory()
    fake_registry = _FakeRegistry(factory=fake_factory)
    empty_bronze_root = tmp_path / "cached_bronze" / "chembl" / "activity"
    empty_bronze_root.mkdir(parents=True)

    context = SimpleNamespace(
        pipeline_name="chembl_activity",
        run_id=uuid4(),
        log_level="INFO",
        vacuum=None,
        run_type="incremental",
        resume=False,
        limit=25,
        query=None,
        dry_run=False,
        skip_gold=False,
        start_offset=None,
        exact_replay=True,
        input_filter=SimpleNamespace(enabled=False),
    )

    with pytest.raises(
        RuntimeError,
        match="Cached Bronze execution requires at least one persisted batch file for snapshot provenance",
    ):
        runner_builder.build_pipeline_runner(
            context,
            registry=fake_registry,
            ensure_providers_loaded_fn=lambda: None,
            register_all_pipelines_fn=lambda registry=None: None,
            get_settings_fn=lambda: SimpleNamespace(
                data_dir=str(tmp_path),
                pipeline=SimpleNamespace(heartbeat_interval=30),
                test_mode=False,
            ),
            load_pipeline_config_fn=lambda _: SimpleNamespace(
                provider="chembl",
                entity_type="activity",
                version="2.0.0",
                maintenance=SimpleNamespace(
                    auto_vacuum=False,
                    vacuum_retention_days=7,
                ),
                input_filter=SimpleNamespace(),
                business_primary_keys=["activity_id"],
                technical_primary_key="entity_id",
                sink={
                    "bronze": SimpleNamespace(enabled=True, save_metadata=True),
                    "silver": SimpleNamespace(enabled=True, save_metadata=True),
                    "gold": SimpleNamespace(enabled=True, save_metadata=True),
                },
            ),
            build_observability_bundle_fn=lambda **_: _namespace_observability(
                SimpleNamespace(info=lambda *_, **__: None),
            ),
            assemble_vacuum_settings_fn=lambda **_: "vacuum",
            assemble_runtime_config_fn=lambda **_: SimpleNamespace(
                run_type="incremental",
                limit=25,
                exact_replay=True,
            ),
            assemble_filter_config_fn=lambda **_: None,
            assemble_cached_bronze_context_fn=lambda _: SimpleNamespace(
                enabled=True,
                bronze_path=str(empty_bronze_root),
                bronze_date="2026-01-01",
            ),
        )

    assert fake_factory.kwargs is None


def test_build_pipeline_runner_keeps_snapshot_backed_execution_identity_stable_across_repeated_exact_replays(
    tmp_path: Path,
) -> None:
    """Repeated exact replays over the same snapshots should keep one canonical identity."""
    bronze_root = tmp_path / "bronze-cache"
    bronze_day = bronze_root / "2026-01-01"
    bronze_day.mkdir(parents=True)
    (bronze_day / "batch_2026-01-01_demo.jsonl.zst").write_bytes(b"snapshot-bytes")
    (bronze_day / "batch_2026-01-01_extra.jsonl.zst").write_bytes(b"snapshot-bytes-2")

    def _build_context() -> SimpleNamespace:
        return SimpleNamespace(
            pipeline_name="chembl_activity",
            run_id=uuid4(),
            log_level="INFO",
            vacuum=None,
            run_type="incremental",
            resume=False,
            limit=100,
            query=None,
            dry_run=False,
            skip_gold=False,
            start_offset=None,
            exact_replay=True,
            input_filter=SimpleNamespace(enabled=False),
        )

    def _build_runner_once() -> dict[str, object]:
        fake_factory = _FakeFactory()
        fake_registry = _FakeRegistry(factory=fake_factory)
        with patch(
            "bioetl.composition.runtime_builders._run_manifest_builder_policy.get_code_revision_provenance",
            return_value=SimpleNamespace(
                git_commit="deadbeef" * 5,
                source_revision_state="clean",
                dependency_lock_hash="sha256:test-lock",
            ),
        ):
            runner_builder.build_pipeline_runner(
                _build_context(),
                registry=fake_registry,
                ensure_providers_loaded_fn=lambda: None,
                register_all_pipelines_fn=lambda registry=None: None,
                get_settings_fn=lambda: SimpleNamespace(
                    data_dir=str(tmp_path),
                    pipeline=SimpleNamespace(heartbeat_interval=30),
                    test_mode=False,
                ),
                load_pipeline_config_fn=lambda _: SimpleNamespace(
                    provider="chembl",
                    entity_type="activity",
                    version="2.0.0",
                    maintenance={"retain_days": 7},
                    input_filter=SimpleNamespace(),
                    business_primary_keys=["activity_id"],
                    technical_primary_key="entity_id",
                ),
                build_observability_bundle_fn=lambda **_: _namespace_observability(
                    SimpleNamespace(info=lambda *_, **__: None),
                ),
                assemble_vacuum_settings_fn=lambda **_: "vacuum",
                assemble_runtime_config_fn=lambda **_: SimpleNamespace(
                    run_type="incremental",
                    limit=100,
                    exact_replay=True,
                ),
                assemble_filter_config_fn=lambda **_: None,
                assemble_cached_bronze_context_fn=lambda _: SimpleNamespace(
                    enabled=True,
                    bronze_path=str(bronze_root),
                    bronze_date="2026-01-01",
                ),
            )
        manifest_id = fake_factory.kwargs["manifest_id"]
        manifest_path = (
            tmp_path / "output" / "control" / "run_manifest" / f"{manifest_id}.json"
        )
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    first_manifest = _build_runner_once()
    second_manifest = _build_runner_once()

    assert first_manifest["manifest_id"] != second_manifest["manifest_id"]
    assert first_manifest["run_id"] != second_manifest["run_id"]
    assert (
        first_manifest["execution_fingerprint"]
        == second_manifest["execution_fingerprint"]
    )
    assert first_manifest["replay_capability"] == "exact_replay_supported"
    assert second_manifest["replay_capability"] == "exact_replay_supported"
    assert first_manifest["source_refs"] == second_manifest["source_refs"]


def test_build_pipeline_runner_persists_resume_launch_context_when_resume_enabled(
    tmp_path: Path,
) -> None:
    """Resume requests should still persist manifest + ledger control-plane state."""
    fake_factory, fake_registry = _build_factory_registry()
    context = _build_context(resume=True, limit=25, query="status=active")

    result = _call_build_pipeline_runner(
        context,
        registry=fake_registry,
        settings=_build_settings(data_dir=str(tmp_path)),
        pipeline_config=_build_pipeline_config(
            maintenance=SimpleNamespace(auto_vacuum=False, vacuum_retention_days=7),
        ),
        assemble_vacuum_settings_fn=lambda **_: "vacuum",
        assemble_runtime_config_fn=lambda **_: SimpleNamespace(
            run_type="incremental",
            limit=25,
        ),
    )

    assert result == "runner-instance"
    assert isinstance(fake_factory.kwargs, dict)
    manifest_id = fake_factory.kwargs["manifest_id"]
    assert isinstance(manifest_id, str)

    manifest_path = (
        tmp_path / "output" / "control" / "run_manifest" / f"{manifest_id}.json"
    )
    assert manifest_path.exists()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    launch_context = payload["launch_context"]
    assert isinstance(launch_context, dict)
    assert launch_context["resume"] is True
    assert payload["replay_capability"] == "exact_replay_supported"
    assert launch_context["query"] == "status=active"
    assert launch_context["pipeline_name"] == "chembl_activity"

    ledger_path = (
        tmp_path / "output" / "control" / "run_ledger" / f"{manifest_id}.jsonl"
    )
    assert ledger_path.exists()
    ledger_payload = json.loads(ledger_path.read_text(encoding="utf-8").splitlines()[0])
    assert ledger_payload["manifest_id"] == manifest_id
    assert ledger_payload["event_type"] == "manifest_created"


def test_build_pipeline_runner_aborts_before_factory_create_when_manifest_persistence_fails(
    tmp_path: Path,
) -> None:
    fake_factory, fake_registry = _build_factory_registry()
    context = _build_context(limit=25)

    with (
        patch(
            "bioetl.composition.runtime_builders._run_manifest_publication_support.FileRunManifestStore.save",
            side_effect=OSError("manifest write failed"),
        ),
        pytest.raises(OSError, match="manifest write failed"),
    ):
        _call_build_pipeline_runner(
            context,
            registry=fake_registry,
            settings=_build_settings(data_dir=str(tmp_path)),
            pipeline_config=_build_pipeline_config(
                maintenance=SimpleNamespace(
                    auto_vacuum=False,
                    vacuum_retention_days=7,
                ),
            ),
            assemble_vacuum_settings_fn=lambda **_: "vacuum",
            assemble_runtime_config_fn=lambda **_: SimpleNamespace(
                run_type="incremental",
                limit=25,
            ),
        )

    assert fake_factory.kwargs is None
    assert not (tmp_path / "output" / "control" / "run_ledger").exists()


def test_build_pipeline_runner_binds_manifest_id_into_observability_bundle(
    tmp_path: Path,
) -> None:
    """Builder should enrich bundle logger context once manifest_id exists."""
    fake_factory, fake_registry = _build_factory_registry()
    base_logger = MagicMock()
    bound_logger = MagicMock()
    base_logger.bind.return_value = bound_logger
    bundle = ObservabilityBundle(
        logger=base_logger,
        metrics=MagicMock(),
        tracer=NoOpTracing(),
        audit=NoOpAudit(),
    )

    context = _build_context(limit=25)

    _call_build_pipeline_runner(
        context,
        registry=fake_registry,
        settings=_build_settings(data_dir=str(tmp_path)),
        pipeline_config=_build_pipeline_config(),
        build_observability_bundle_fn=lambda **_: bundle,
        assemble_runtime_config_fn=lambda **_: SimpleNamespace(run_type="incremental"),
    )

    assert isinstance(fake_factory.kwargs, dict)
    manifest_id = fake_factory.kwargs["manifest_id"]
    assert isinstance(manifest_id, str)
    base_logger.bind.assert_called_once_with(manifest_id=manifest_id)
    assert fake_factory.kwargs["observability"].logger is bound_logger


def test_build_pipeline_runner_binds_manifest_id_into_namespace_logger(
    tmp_path: Path,
) -> None:
    """Builder should support lightweight namespace observability doubles."""
    fake_factory, fake_registry = _build_factory_registry()
    base_logger = MagicMock()
    bound_logger = MagicMock()
    base_logger.bind.return_value = bound_logger
    observability = _namespace_observability(base_logger)

    context = _build_context(limit=25)

    _call_build_pipeline_runner(
        context,
        registry=fake_registry,
        settings=_build_settings(data_dir=str(tmp_path)),
        pipeline_config=_build_pipeline_config(),
        build_observability_bundle_fn=lambda **_: observability,
        assemble_runtime_config_fn=lambda **_: SimpleNamespace(run_type="incremental"),
    )

    assert isinstance(fake_factory.kwargs, dict)
    manifest_id = fake_factory.kwargs["manifest_id"]
    assert isinstance(manifest_id, str)
    base_logger.bind.assert_called_once_with(manifest_id=manifest_id)
    assert fake_factory.kwargs["observability"].logger is bound_logger


def test_build_pipeline_runner_requires_manifest_control_plane_when_manifest_disabled(
    tmp_path: Path,
) -> None:
    """Builder should fail closed when manifest rollout is disabled."""
    fake_factory, fake_registry = _build_factory_registry()
    context = _build_context(limit=25)

    with pytest.raises(
        RuntimeError,
        match="Pipeline execution requires run manifests",
    ):
        _call_build_pipeline_runner(
            context,
            registry=fake_registry,
            settings=_build_settings(
                data_dir=str(tmp_path),
                control_plane=SimpleNamespace(
                    run_manifest_enabled=False,
                    run_ledger_enabled=False,
                ),
            ),
            pipeline_config=_build_pipeline_config(),
            assemble_runtime_config_fn=lambda **_: SimpleNamespace(
                run_type="incremental"
            ),
        )

    assert fake_factory.kwargs is None
    assert not (tmp_path / "output" / "control" / "run_manifest").exists()
    assert not (tmp_path / "output" / "control" / "run_ledger").exists()


def test_build_pipeline_runner_promotes_family_floor_and_rejects_ledger_disable(
    tmp_path: Path,
) -> None:
    """Registered strict families must fail closed when ledger is disabled."""
    fake_factory, fake_registry = _build_factory_registry()

    with pytest.raises(
        RuntimeError,
        match="required persistence profile 'replay_ready'",
    ):
        _call_build_pipeline_runner(
            _build_context(limit=25),
            registry=fake_registry,
            settings=_build_settings(
                data_dir=str(tmp_path),
                control_plane=SimpleNamespace(
                    run_manifest_enabled=True,
                    run_ledger_enabled=False,
                    required_persistence_profile="degraded_observable",
                ),
            ),
            pipeline_config=_build_pipeline_config(),
            assemble_runtime_config_fn=lambda **_: SimpleNamespace(
                run_type="incremental"
            ),
        )

    assert fake_factory.kwargs is None


def test_build_pipeline_runner_requires_ledger_for_forensic_grade_profile(
    tmp_path: Path,
) -> None:
    """Forensic-grade runtime profile must fail closed when ledger is disabled."""
    fake_registry = _build_factory_registry()[1]

    with pytest.raises(
        RuntimeError,
        match="required persistence profile 'forensic_grade'",
    ):
        _call_build_pipeline_runner(
            _build_context(limit=25),
            registry=fake_registry,
            settings=_build_settings(
                data_dir=str(tmp_path),
                control_plane=SimpleNamespace(
                    run_manifest_enabled=True,
                    run_ledger_enabled=False,
                    required_persistence_profile="forensic_grade",
                ),
            ),
            pipeline_config=_build_pipeline_config(),
            assemble_runtime_config_fn=lambda **_: SimpleNamespace(
                run_type="incremental"
            ),
        )


def test_build_pipeline_runner_requires_ledger_for_replay_ready_profile(
    tmp_path: Path,
) -> None:
    """Replay-ready runtime profile must fail closed when ledger is disabled."""
    fake_registry = _build_factory_registry()[1]

    with pytest.raises(
        RuntimeError,
        match="required persistence profile 'replay_ready'",
    ):
        _call_build_pipeline_runner(
            _build_context(limit=25),
            registry=fake_registry,
            settings=_build_settings(
                data_dir=str(tmp_path),
                control_plane=SimpleNamespace(
                    run_manifest_enabled=True,
                    run_ledger_enabled=False,
                    required_persistence_profile="replay_ready",
                ),
            ),
            pipeline_config=_build_pipeline_config(),
            assemble_runtime_config_fn=lambda **_: SimpleNamespace(
                run_type="incremental"
            ),
        )


def test_build_pipeline_runner_requires_lineage_sidecars_for_forensic_grade_profile(
    tmp_path: Path,
) -> None:
    """Forensic-grade profile must fail when active sink layers skip metadata."""
    fake_registry = _build_factory_registry()[1]

    with pytest.raises(
        RuntimeError,
        match="metadata sidecars / lineage persistence for active layers",
    ):
        _call_build_pipeline_runner(
            _build_context(limit=25),
            registry=fake_registry,
            settings=_build_settings(
                data_dir=str(tmp_path),
                control_plane=SimpleNamespace(
                    run_manifest_enabled=True,
                    run_ledger_enabled=True,
                    required_persistence_profile="forensic_grade",
                ),
            ),
            pipeline_config=_build_pipeline_config(
                sink={
                    "bronze": SimpleNamespace(enabled=True, save_metadata=False),
                    "silver": SimpleNamespace(enabled=True, save_metadata=True),
                    "gold": SimpleNamespace(enabled=True, save_metadata=False),
                },
            ),
            assemble_runtime_config_fn=lambda **_: SimpleNamespace(
                run_type="incremental"
            ),
        )


def test_build_pipeline_runner_requires_lineage_sidecars_for_replay_ready_profile(
    tmp_path: Path,
) -> None:
    """Replay-ready profile must fail when active sink layers skip metadata."""
    fake_registry = _build_factory_registry()[1]

    with pytest.raises(
        RuntimeError,
        match="metadata sidecars / lineage persistence for active layers",
    ):
        _call_build_pipeline_runner(
            _build_context(limit=25),
            registry=fake_registry,
            settings=_build_settings(
                data_dir=str(tmp_path),
                control_plane=SimpleNamespace(
                    run_manifest_enabled=True,
                    run_ledger_enabled=True,
                    required_persistence_profile="replay_ready",
                ),
            ),
            pipeline_config=_build_pipeline_config(
                sink={
                    "bronze": SimpleNamespace(enabled=True, save_metadata=True),
                    "silver": SimpleNamespace(enabled=True, save_metadata=False),
                    "gold": SimpleNamespace(enabled=False, save_metadata=False),
                },
            ),
            assemble_runtime_config_fn=lambda **_: SimpleNamespace(
                run_type="incremental"
            ),
        )


def test_build_pipeline_runner_requires_git_commit_for_replay_ready_profile(
    tmp_path: Path,
) -> None:
    """Replay-ready runs must pin code provenance before manifest persistence."""
    fake_factory, fake_registry = _build_factory_registry()
    bronze_root = tmp_path / "bronze-cache"
    bronze_day = bronze_root / "2026-01-01"
    bronze_day.mkdir(parents=True)
    (bronze_day / "batch_2026-01-01_demo.jsonl.zst").write_bytes(b"snapshot-bytes")

    with (
        patch(
            "bioetl.composition.runtime_builders._run_manifest_builder_policy.get_code_revision_provenance",
            return_value=SimpleNamespace(
                git_commit=None,
                source_revision_state="git_unavailable",
                dependency_lock_hash=None,
            ),
        ),
        pytest.raises(RuntimeError, match="requires git_commit code provenance"),
    ):
        _call_build_pipeline_runner(
            _build_context(limit=25, exact_replay=True),
            registry=fake_registry,
            settings=_build_settings(
                data_dir=str(tmp_path),
                control_plane=SimpleNamespace(
                    run_manifest_enabled=True,
                    run_ledger_enabled=True,
                    required_persistence_profile="replay_ready",
                ),
            ),
            pipeline_config=_build_pipeline_config(
                sink={
                    "bronze": SimpleNamespace(enabled=True, save_metadata=True),
                    "silver": SimpleNamespace(
                        enabled=True,
                        save_metadata=True,
                        mode="merge",
                    ),
                    "gold": SimpleNamespace(
                        enabled=True,
                        save_metadata=True,
                        mode="scd2",
                    ),
                },
            ),
            assemble_runtime_config_fn=lambda **_: SimpleNamespace(
                run_type="incremental"
            ),
            assemble_cached_bronze_context_fn=lambda _: SimpleNamespace(
                enabled=True,
                bronze_path=str(bronze_root),
                bronze_date="2026-01-01",
            ),
        )

    assert fake_factory.kwargs is None


def test_build_pipeline_runner_requires_dependency_lock_for_replay_ready_profile(
    tmp_path: Path,
) -> None:
    """Strict replay readiness must pin dependency lock provenance."""
    fake_factory, fake_registry = _build_factory_registry()
    bronze_root = tmp_path / "bronze-cache"
    bronze_day = bronze_root / "2026-01-01"
    bronze_day.mkdir(parents=True)
    (bronze_day / "batch_2026-01-01_demo.jsonl.zst").write_bytes(b"snapshot-bytes")

    with (
        patch(
            "bioetl.composition.runtime_builders._run_manifest_builder_policy.get_code_revision_provenance",
            return_value=SimpleNamespace(
                git_commit="abc1234",
                source_revision_state="clean",
                dependency_lock_hash=None,
            ),
        ),
        pytest.raises(RuntimeError, match="requires dependency_lock_hash"),
    ):
        _call_build_pipeline_runner(
            _build_context(limit=25, exact_replay=True),
            registry=fake_registry,
            settings=_build_settings(
                data_dir=str(tmp_path),
                control_plane=SimpleNamespace(
                    run_manifest_enabled=True,
                    run_ledger_enabled=True,
                    required_persistence_profile="replay_ready",
                ),
            ),
            pipeline_config=_build_pipeline_config(
                sink={
                    "bronze": SimpleNamespace(enabled=True, save_metadata=True),
                    "silver": SimpleNamespace(
                        enabled=True,
                        save_metadata=True,
                        mode="merge",
                    ),
                    "gold": SimpleNamespace(
                        enabled=True,
                        save_metadata=True,
                        mode="scd2",
                    ),
                },
            ),
            assemble_runtime_config_fn=lambda **_: SimpleNamespace(
                run_type="incremental"
            ),
            assemble_cached_bronze_context_fn=lambda _: SimpleNamespace(
                enabled=True,
                bronze_path=str(bronze_root),
                bronze_date="2026-01-01",
            ),
        )

    assert fake_factory.kwargs is None


def test_build_pipeline_runner_rejects_append_silver_for_replay_ready_profile(
    tmp_path: Path,
) -> None:
    """Replay-ready semantic outputs cannot use append-mode Silver/Gold sinks."""
    fake_factory, fake_registry = _build_factory_registry()

    with pytest.raises(RuntimeError, match=r"sink\.silver\.mode=append"):
        _call_build_pipeline_runner(
            _build_context(limit=25, exact_replay=False),
            registry=fake_registry,
            settings=_build_settings(
                data_dir=str(tmp_path),
                control_plane=SimpleNamespace(
                    run_manifest_enabled=True,
                    run_ledger_enabled=True,
                    required_persistence_profile="replay_ready",
                ),
            ),
            pipeline_config=_build_pipeline_config(
                sink={
                    "bronze": SimpleNamespace(enabled=True, save_metadata=True),
                    "silver": SimpleNamespace(
                        enabled=True,
                        save_metadata=True,
                        mode="append",
                        idempotency_contract="append_log",
                    ),
                    "gold": SimpleNamespace(
                        enabled=False,
                        save_metadata=True,
                        mode="append",
                        idempotency_contract="append_log",
                    ),
                },
            ),
            assemble_runtime_config_fn=lambda **_: SimpleNamespace(
                run_type="incremental"
            ),
        )

    assert fake_factory.kwargs is None


def test_build_pipeline_runner_requires_explicit_data_dir_for_strict_profiles() -> None:
    """Strict reproducibility profiles must not derive control-plane roots from fallback."""
    _, fake_registry = _build_factory_registry()

    with pytest.raises(RuntimeError, match=r"explicit settings\.data_dir"):
        _call_build_pipeline_runner(
            _build_context(limit=25, exact_replay=True),
            registry=fake_registry,
            settings=_build_settings(
                data_dir=None,
                control_plane=SimpleNamespace(
                    run_manifest_enabled=True,
                    run_ledger_enabled=True,
                    required_persistence_profile="replay_ready",
                ),
            ),
            pipeline_config=_build_pipeline_config(
                sink={
                    "bronze": SimpleNamespace(enabled=True, save_metadata=True),
                    "silver": SimpleNamespace(
                        enabled=True,
                        save_metadata=True,
                        mode="merge",
                        idempotency_contract="merge_upsert",
                    ),
                    "gold": SimpleNamespace(
                        enabled=True,
                        save_metadata=True,
                        mode="scd2",
                        idempotency_contract="scd2",
                    ),
                },
            ),
        )


def test_build_pipeline_runner_forensic_grade_fails_when_recorder_attachment_missing(
    tmp_path: Path,
) -> None:
    """Forensic-grade runs must fail closed when no attachable metadata writer exists."""
    fake_factory, fake_registry = _build_factory_registry()
    fake_factory.runner.services = SimpleNamespace(
        metadata_writer=object(), storage=None
    )
    bronze_root = tmp_path / "bronze-cache"
    bronze_day = bronze_root / "2026-01-01"
    bronze_day.mkdir(parents=True)
    (bronze_day / "batch_2026-01-01_demo.jsonl.zst").write_bytes(b"snapshot-bytes")

    with (
        patch(
            "bioetl.composition.runtime_builders._run_manifest_builder_policy.get_code_revision_provenance",
            return_value=SimpleNamespace(
                git_commit="deadbeef" * 5,
                source_revision_state="clean",
                dependency_lock_hash="sha256:test-lock",
            ),
        ),
        pytest.raises(RuntimeError, match="artifact publication closure"),
    ):
        _call_build_pipeline_runner(
            _build_context(limit=25, exact_replay=True),
            registry=fake_registry,
            settings=_build_settings(
                data_dir=str(tmp_path),
                control_plane=SimpleNamespace(
                    run_manifest_enabled=True,
                    run_ledger_enabled=True,
                    required_persistence_profile="forensic_grade",
                ),
            ),
            pipeline_config=_build_pipeline_config(
                sink={
                    "bronze": SimpleNamespace(enabled=True, save_metadata=True),
                    "silver": SimpleNamespace(enabled=True, save_metadata=True),
                    "gold": SimpleNamespace(enabled=True, save_metadata=True),
                },
            ),
            assemble_runtime_config_fn=lambda **_: SimpleNamespace(
                run_type="incremental"
            ),
            assemble_cached_bronze_context_fn=lambda _: SimpleNamespace(
                enabled=True,
                bronze_path=str(bronze_root),
                bronze_date="2026-01-01",
            ),
        )


def test_build_pipeline_runner_replay_ready_fails_when_recorder_attachment_missing(
    tmp_path: Path,
) -> None:
    """Replay-ready runs must fail closed when artifact publication is not wired."""
    fake_factory, fake_registry = _build_factory_registry()
    fake_factory.runner.services = SimpleNamespace(
        metadata_writer=object(), storage=None
    )
    bronze_root = tmp_path / "bronze-cache"
    bronze_day = bronze_root / "2026-01-01"
    bronze_day.mkdir(parents=True)
    (bronze_day / "batch_2026-01-01_demo.jsonl.zst").write_bytes(b"snapshot-bytes")

    with (
        patch(
            "bioetl.composition.runtime_builders._run_manifest_builder_policy.get_code_revision_provenance",
            return_value=SimpleNamespace(
                git_commit="deadbeef" * 5,
                source_revision_state="clean",
                dependency_lock_hash="sha256:test-lock",
            ),
        ),
        pytest.raises(RuntimeError, match="artifact publication closure"),
    ):
        _call_build_pipeline_runner(
            _build_context(limit=25, exact_replay=True),
            registry=fake_registry,
            settings=_build_settings(
                data_dir=str(tmp_path),
                control_plane=SimpleNamespace(
                    run_manifest_enabled=True,
                    run_ledger_enabled=True,
                    required_persistence_profile="replay_ready",
                ),
            ),
            pipeline_config=_build_pipeline_config(
                sink={
                    "bronze": SimpleNamespace(enabled=True, save_metadata=True),
                    "silver": SimpleNamespace(enabled=True, save_metadata=True),
                    "gold": SimpleNamespace(enabled=True, save_metadata=True),
                },
            ),
            assemble_runtime_config_fn=lambda **_: SimpleNamespace(
                run_type="incremental"
            ),
            assemble_cached_bronze_context_fn=lambda _: SimpleNamespace(
                enabled=True,
                bronze_path=str(bronze_root),
                bronze_date="2026-01-01",
            ),
        )


def test_build_pipeline_runner_allows_forensic_grade_with_exact_replay_and_sidecars(
    tmp_path: Path,
) -> None:
    """Forensic-grade profile should succeed when replay and sidecar surfaces exist."""
    fake_factory, fake_registry = _build_factory_registry()
    bronze_root = tmp_path / "bronze-cache"
    bronze_day = bronze_root / "2026-01-01"
    bronze_day.mkdir(parents=True)
    (bronze_day / "batch_2026-01-01_demo.jsonl.zst").write_bytes(b"snapshot-bytes")

    with patch(
        "bioetl.composition.runtime_builders._run_manifest_builder_policy.get_code_revision_provenance",
        return_value=SimpleNamespace(
            git_commit="deadbeef" * 5,
            source_revision_state="clean",
            dependency_lock_hash="sha256:test-lock",
        ),
    ):
        result = _call_build_pipeline_runner(
            _build_context(limit=25, exact_replay=True),
            registry=fake_registry,
            settings=_build_settings(
                data_dir=str(tmp_path),
                control_plane=SimpleNamespace(
                    run_manifest_enabled=True,
                    run_ledger_enabled=True,
                    required_persistence_profile="forensic_grade",
                ),
            ),
            pipeline_config=_build_pipeline_config(
                sink={
                    "bronze": SimpleNamespace(enabled=True, save_metadata=True),
                    "silver": SimpleNamespace(enabled=True, save_metadata=True),
                    "gold": SimpleNamespace(enabled=True, save_metadata=True),
                },
            ),
            assemble_runtime_config_fn=lambda **_: SimpleNamespace(
                run_type="incremental"
            ),
            assemble_cached_bronze_context_fn=lambda _: SimpleNamespace(
                enabled=True,
                bronze_path=str(bronze_root),
                bronze_date="2026-01-01",
            ),
        )

    assert result == "runner-instance"
    assert isinstance(fake_factory.kwargs, dict)
    manifest_id = fake_factory.kwargs["manifest_id"]
    assert isinstance(manifest_id, str)
    assert fake_factory.runner.attached_run_ledger_service is not None

    manifest_path = (
        tmp_path / "output" / "control" / "run_manifest" / f"{manifest_id}.json"
    )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["launch_context"]["required_persistence_profile"] == (
        "forensic_grade"
    )
    assert payload["replay_capability"] == "exact_replay_supported"


def test_build_pipeline_runner_promotes_supported_exact_replay_to_family_default_profile(
    tmp_path: Path,
) -> None:
    """Supported exact-replay launches inherit the published replay-ready default."""
    fake_factory, fake_registry = _build_factory_registry()
    bronze_root = tmp_path / "bronze-cache"
    bronze_day = bronze_root / "2026-01-01"
    bronze_day.mkdir(parents=True)
    (bronze_day / "batch_2026-01-01_demo.jsonl.zst").write_bytes(b"snapshot-bytes")

    with patch(
        "bioetl.composition.runtime_builders._run_manifest_builder_policy.get_code_revision_provenance",
        return_value=SimpleNamespace(
            git_commit="deadbeef" * 5,
            source_revision_state="clean",
            dependency_lock_hash="sha256:test-lock",
        ),
    ):
        _call_build_pipeline_runner(
            _build_context(limit=25, exact_replay=True),
            registry=fake_registry,
            settings=_build_settings(
                data_dir=str(tmp_path),
                control_plane=SimpleNamespace(
                    run_manifest_enabled=True,
                    run_ledger_enabled=True,
                    required_persistence_profile="degraded_observable",
                ),
            ),
            pipeline_config=_build_pipeline_config(
                sink={
                    "bronze": SimpleNamespace(enabled=True, save_metadata=True),
                    "silver": SimpleNamespace(enabled=True, save_metadata=True),
                    "gold": SimpleNamespace(enabled=True, save_metadata=True),
                },
            ),
            assemble_runtime_config_fn=lambda **_: SimpleNamespace(
                run_type="incremental"
            ),
            assemble_cached_bronze_context_fn=lambda _: SimpleNamespace(
                enabled=True,
                bronze_path=str(bronze_root),
                bronze_date="2026-01-01",
            ),
        )

    assert isinstance(fake_factory.kwargs, dict)
    manifest_id = fake_factory.kwargs["manifest_id"]
    manifest_path = (
        tmp_path / "output" / "control" / "run_manifest" / f"{manifest_id}.json"
    )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["launch_context"]["required_persistence_profile"] == "replay_ready"
    assert payload["launch_context"]["replay_readiness_verdict"] == (
        "exact_replay_ready"
    )
    assert payload["launch_context"]["strict_exact_replay_supported"] is True
    assert payload["launch_context"]["replay_family_contract"] == (
        "snapshot_backed_exact_replay"
    )


def test_build_pipeline_runner_promoted_replay_ready_requires_ledger(
    tmp_path: Path,
) -> None:
    """Exact replay auto-promotion must re-check ledger after profile resolution."""
    fake_factory, fake_registry = _build_factory_registry()
    bronze_root = tmp_path / "bronze-cache"
    bronze_day = bronze_root / "2026-01-01"
    bronze_day.mkdir(parents=True)
    (bronze_day / "batch_2026-01-01_demo.jsonl.zst").write_bytes(b"snapshot-bytes")

    with (
        patch(
            "bioetl.composition.runtime_builders._run_manifest_builder_policy.get_code_revision_provenance",
            return_value=SimpleNamespace(
                git_commit="deadbeef" * 5,
                source_revision_state="clean",
                dependency_lock_hash="sha256:test-lock",
            ),
        ),
        pytest.raises(
            RuntimeError, match="required persistence profile 'replay_ready'"
        ),
    ):
        _call_build_pipeline_runner(
            _build_context(limit=25, exact_replay=True),
            registry=fake_registry,
            settings=_build_settings(
                data_dir=str(tmp_path),
                control_plane=SimpleNamespace(
                    run_manifest_enabled=True,
                    run_ledger_enabled=False,
                    required_persistence_profile="degraded_observable",
                ),
            ),
            pipeline_config=_build_pipeline_config(
                sink={
                    "bronze": SimpleNamespace(enabled=True, save_metadata=True),
                    "silver": SimpleNamespace(enabled=True, save_metadata=True),
                    "gold": SimpleNamespace(enabled=True, save_metadata=True),
                },
            ),
            assemble_runtime_config_fn=lambda **_: SimpleNamespace(
                run_type="incremental"
            ),
            assemble_cached_bronze_context_fn=lambda _: SimpleNamespace(
                enabled=True,
                bronze_path=str(bronze_root),
                bronze_date="2026-01-01",
            ),
        )

    assert fake_factory.kwargs is None
    assert not (tmp_path / "output" / "control" / "run_manifest").exists()


def test_build_pipeline_runner_attaches_artifact_recorder_to_metadata_writers(
    tmp_path: Path,
) -> None:
    fake_factory = _FakeFactory()
    fake_registry = _FakeRegistry(factory=fake_factory)
    top_writer = _RecorderAwareMetadataWriter()
    bronze_writer = _RecorderAwareMetadataWriter()
    silver_writer = _RecorderAwareMetadataWriter()
    gold_writer = _RecorderAwareMetadataWriter()
    fake_factory.runner.services = SimpleNamespace(
        metadata_writer=top_writer,
        storage=SimpleNamespace(
            bronze=SimpleNamespace(_metadata_writer=bronze_writer),
            silver=SimpleNamespace(_metadata_writer=silver_writer),
            gold=SimpleNamespace(_metadata_writer=gold_writer),
        ),
    )

    context = SimpleNamespace(
        pipeline_name="chembl_activity",
        run_id=uuid4(),
        log_level="INFO",
        vacuum=None,
        run_type="incremental",
        resume=False,
        limit=25,
        query=None,
        dry_run=False,
        skip_gold=False,
        start_offset=None,
        input_filter=SimpleNamespace(enabled=False),
    )

    with _clean_provenance_context_if_unpatched():
        runner_builder.build_pipeline_runner(
            context,
            registry=fake_registry,
            ensure_providers_loaded_fn=lambda: None,
            register_all_pipelines_fn=lambda registry=None: None,
            get_settings_fn=lambda: SimpleNamespace(
                data_dir=str(tmp_path),
                pipeline=SimpleNamespace(
                    heartbeat_interval=30,
                    control_plane=SimpleNamespace(
                        required_persistence_profile="degraded_observable",
                        checkpoint_compatibility_policy="hard_fail",
                        run_manifest_enabled=True,
                        run_ledger_enabled=True,
                    ),
                ),
                test_mode=False,
            ),
            load_pipeline_config_fn=lambda _: SimpleNamespace(
                provider="chembl",
                entity_type="activity",
                version="2.0.0",
                maintenance=None,
                input_filter=SimpleNamespace(),
                business_primary_keys=["activity_id"],
                technical_primary_key="entity_id",
                sink={
                    "bronze": SimpleNamespace(enabled=True, save_metadata=True),
                    "silver": SimpleNamespace(enabled=True, save_metadata=True),
                    "gold": SimpleNamespace(enabled=True, save_metadata=True),
                },
            ),
            build_observability_bundle_fn=lambda **_: _namespace_observability(
                SimpleNamespace(info=lambda *_, **__: None),
            ),
            assemble_vacuum_settings_fn=lambda **_: None,
            assemble_runtime_config_fn=lambda **_: SimpleNamespace(
                run_type="incremental"
            ),
            assemble_filter_config_fn=lambda **_: None,
            assemble_cached_bronze_context_fn=lambda _: _ensure_default_cached_bronze_fixture(
                settings=SimpleNamespace(
                    data_dir=str(tmp_path),
                    pipeline=SimpleNamespace(
                        heartbeat_interval=30,
                        control_plane=SimpleNamespace(
                            required_persistence_profile="degraded_observable",
                            checkpoint_compatibility_policy="hard_fail",
                            run_manifest_enabled=True,
                            run_ledger_enabled=True,
                        ),
                    ),
                    test_mode=False,
                ),
                pipeline_config=SimpleNamespace(
                    provider="chembl",
                    entity_type="activity",
                ),
            ),
        )

    for writer in (top_writer, bronze_writer, silver_writer, gold_writer):
        assert writer.recorder is not None

    manifest_id = fake_factory.kwargs["manifest_id"]
    assert isinstance(manifest_id, str)
    silver_writer.recorder(
        "silver",
        SILVER_OUTPUT_PATH,
        {
            "metadata_path": SILVER_METADATA_PATH,
            "dataset_ref": "silver:chembl.activity@1",
            "lineage_fragment_id": "silver:fragment-1",
        },
    )
    ledger_path = (
        tmp_path / "output" / "control" / "run_ledger" / f"{manifest_id}.jsonl"
    )
    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    ledger_payload = json.loads(lines[1])
    assert ledger_payload["event_type"] == "artifact_published"
    assert ledger_payload["stage"] == "silver"
    assert ledger_payload["dataset_ref"] == "silver:chembl.activity@1"
    assert ledger_payload["lineage_fragment_id"] == "silver:fragment-1"


