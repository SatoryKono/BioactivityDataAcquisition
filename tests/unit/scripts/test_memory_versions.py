"""Immutable dependency identity and fail-closed profile dispatch controls."""

from __future__ import annotations

import argparse
import hashlib
import json
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.ai.mcp import memory_versions as versions

pytestmark = pytest.mark.unit


@pytest.fixture
def bundle_factory(tmp_path):
    def build(dependency):
        source = tmp_path / "building"
        (source / "runtime").mkdir(parents=True)
        (source / "runtime/dependency.py").write_bytes(dependency)
        manifest = {
            "schema": 2,
            "files": {
                "runtime/dependency.py": versions.sha(source / "runtime/dependency.py")
            },
        }
        raw = versions.canonical(manifest)
        (source / "bundle.json").write_bytes(raw)
        target = tmp_path / hashlib.sha256(raw).hexdigest()
        source.rename(target)
        return target

    return build


@pytest.fixture
def bundle(bundle_factory):
    return bundle_factory(b"VERSION = 'qualified'\n")


def test_dependency_drift_is_rejected(bundle):
    assert versions.verify(bundle)["schema"] == 2
    (bundle / "runtime/dependency.py").write_bytes(b"VERSION = 'changed'\n")
    with pytest.raises(ValueError, match="drift"):
        versions.verify(bundle)


def test_unlisted_executable_file_is_rejected(bundle):
    (bundle / "runtime/injected.py").write_bytes(b"print('unexpected')")
    with pytest.raises(ValueError, match="file set"):
        versions.verify(bundle)


def test_manifest_change_cannot_reuse_version_name(bundle):
    manifest = json.loads((bundle / "bundle.json").read_bytes())
    manifest["schema"] = 3
    (bundle / "bundle.json").write_bytes(versions.canonical(manifest))
    with pytest.raises(ValueError, match="identity"):
        versions.verify(bundle)


def test_pending_migration_never_falls_back_to_legacy(tmp_path):
    directory = tmp_path / "profile"
    directory.mkdir()
    (directory / "migration-v2.json").write_text(
        json.dumps({"phase": "PREPARING"}), encoding="utf-8"
    )
    (directory / "runtime-binding.json").write_text(
        json.dumps({"schema": 2, "state": "legacy"}), encoding="utf-8"
    )
    with pytest.raises(PermissionError, match="not committed"):
        versions.select_bundle(tmp_path, "profile")


def test_disabled_incompatible_profile_is_not_legacy_fallback(tmp_path):
    directory = tmp_path / "profile"
    directory.mkdir()
    (directory / "runtime-binding.json").write_text(
        json.dumps({"schema": 2, "state": "disabled"}), encoding="utf-8"
    )
    with pytest.raises(PermissionError, match="disabled"):
        versions.select_bundle(tmp_path, "profile")


def test_wrong_version_binding_is_rejected(tmp_path, bundle, monkeypatch):
    monkeypatch.setattr(versions, "VERSIONS", bundle.parent)
    directory = tmp_path / "profile"
    directory.mkdir()
    (directory / "runtime-binding.json").write_text(
        json.dumps(
            {"schema": 2, "state": "active", "bundle": str(bundle), "version": "other"}
        ),
        encoding="utf-8",
    )
    (directory / "migration-v2.json").write_text(
        json.dumps(
            {
                "schema": 2,
                "id": "fixture-transaction",
                "phase": "COMMITTED",
                "bundle": str(bundle),
                "version": "other",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(PermissionError, match="version mismatch"):
        versions.select_bundle(tmp_path, "profile")


def test_selected_profile_does_not_modify_neighbor_binding(
    tmp_path, bundle, monkeypatch
):
    monkeypatch.setattr(versions, "VERSIONS", bundle.parent)
    for name, binding in [
        (
            "target",
            {
                "schema": 2,
                "state": "active",
                "bundle": str(bundle),
                "version": bundle.name,
            },
        ),
        ("neighbor", {"schema": 2, "state": "legacy"}),
    ]:
        directory = tmp_path / name
        directory.mkdir()
        (directory / "runtime-binding.json").write_text(
            json.dumps(binding), encoding="utf-8"
        )
    (tmp_path / "target/migration-v2.json").write_text(
        json.dumps(
            {
                "schema": 2,
                "id": "completed-fixture",
                "phase": "COMMITTED",
                "bundle": str(bundle),
                "version": bundle.name,
            }
        ),
        encoding="utf-8",
    )
    neighbor = tmp_path / "neighbor/runtime-binding.json"
    before = neighbor.read_bytes()
    assert versions.select_bundle(tmp_path, "target") == bundle
    assert versions.select_bundle(tmp_path, "neighbor") is None
    assert neighbor.read_bytes() == before


@pytest.fixture
def predecessor(tmp_path):
    def read(path, **_kwargs):
        return json.loads(path.read_bytes()) if path.exists() else None

    owner = SimpleNamespace(state=SimpleNamespace(read=read))
    entry = {"id": "target"}
    binding = {
        "schema": 2,
        "state": "active",
        "version": "a" * 64,
        "bundle": "prior-version",
    }
    prior = {
        "id": "b" * 32,
        "phase": "COMMITTED",
        "after_entry": entry,
        "version": "a" * 64,
    }
    (tmp_path / "runtime-binding.json").write_text(
        json.dumps(binding), encoding="utf-8"
    )
    (tmp_path / "migration-v2.json").write_text(json.dumps(prior), encoding="utf-8")
    return owner, entry, binding, prior


@pytest.mark.parametrize("expected", [None, "legacy", "c" * 64])
def test_upgrade_requires_the_exact_reviewed_predecessor(
    tmp_path, predecessor, expected
):
    owner, entry, _, _ = predecessor
    before = {path: path.read_bytes() for path in tmp_path.iterdir()}
    with pytest.raises(ValueError, match="explicit"):
        versions.previous_migration(owner, tmp_path, entry, expected)
    assert {path: path.read_bytes() for path in tmp_path.iterdir()} == before


def test_interrupted_prior_migration_cannot_be_replaced(tmp_path, predecessor):
    owner, entry, _, prior = predecessor
    prior["phase"] = "PREPARING"
    path = tmp_path / "migration-v2.json"
    path.write_text(json.dumps(prior), encoding="utf-8")
    before = path.read_bytes()
    with pytest.raises(ValueError, match="does not match"):
        versions.previous_migration(owner, tmp_path, entry, "a" * 64)
    assert path.read_bytes() == before


def test_predecessor_entry_mismatch_keeps_its_history(tmp_path, predecessor):
    owner, _, _, _ = predecessor
    with pytest.raises(ValueError, match="does not match"):
        versions.previous_migration(owner, tmp_path, {"id": "another-target"}, "a" * 64)


def test_rollback_to_an_older_bundle_retains_that_bundle_identity(
    tmp_path, predecessor
):
    owner, entry, binding, prior = predecessor
    prior.update(
        phase="ROLLED_BACK",
        version="d" * 64,
        before={"entry": entry, "runtime_binding": binding},
    )
    (tmp_path / "migration-v2.json").write_text(json.dumps(prior), encoding="utf-8")
    selected, history = versions.previous_migration(owner, tmp_path, entry, "a" * 64)
    assert selected == binding and history == prior


@pytest.mark.parametrize("has_external_plan", [False, True])
def test_reconcile_apply_requires_a_private_plan_before_access(
    tmp_path, monkeypatch, has_external_plan
):
    plan = tmp_path / "other-profile/plan.json" if has_external_plan else None
    args = SimpleNamespace(profile="target", action="reconcile-apply", plan=plan)
    entry = {"state": str(tmp_path / "target")}
    selected = SimpleNamespace(specification=lambda *_args: (entry, {}))

    def forbidden_path_access(_path):
        pytest.fail("An absent or foreign plan must be refused before path access")

    monkeypatch.setattr(versions, "physical", forbidden_path_access)
    with pytest.raises(SystemExit) as error:
        versions._reconcile_profile(argparse.ArgumentParser(), args, selected, False)
    assert error.value.code == 2


@pytest.fixture
def transition_owner(tmp_path, bundle, monkeypatch):
    registry = tmp_path / "registry"
    directory = registry / "target"
    directory.mkdir(parents=True)
    graph = tmp_path / "graph.jsonl"
    graph.write_bytes(b'{"fixture":true}\n')

    def read(path, **_kwargs):
        return json.loads(path.read_bytes()) if path.exists() else None

    def write(path, value):
        assert path.is_relative_to(registry)
        path.write_bytes(versions.canonical(value))

    descriptor = {"profile": {"graph": str(graph)}, "service_pins": {"runtime": "old"}}
    write(directory / "profile.json", descriptor)
    write(directory / "active.json", {"hashes": {str(graph): versions.sha(graph)}})
    write(directory / "recovery-v2.json", {"schema": 2})
    write(
        registry / "profiles.json",
        {
            directory.name: {
                "state": str(directory),
                "descriptor_sha256": versions.sha(directory / "profile.json"),
            },
        },
    )

    def specification(identity, fixture=False):
        return read(registry / "profiles.json")[identity], read(
            directory / "profile.json"
        )

    def physical(path, *, exists=True):
        resolved = path.resolve(strict=exists)
        assert resolved.is_relative_to(registry)
        return resolved

    state = SimpleNamespace(
        read=read,
        write=write,
        scope=SimpleNamespace(canonical=versions.canonical, physical=physical),
    )
    owner = SimpleNamespace(
        state=state,
        registry=SimpleNamespace(
            ROOT=registry,
            provider=SimpleNamespace(hashes=lambda: {"runtime": "new"}),
        ),
        core=SimpleNamespace(LifetimeLock=lambda _path: nullcontext()),
        specification=specification,
        candidate=lambda _entry, _value: {"hashes": {}},
    )
    monkeypatch.setattr(versions, "VERSIONS", bundle.parent)
    monkeypatch.setattr(versions, "bundle_owner", lambda *_args: owner)
    monkeypatch.setattr(
        versions, "dormant", lambda *_args: {"graph_sha256": versions.sha(graph)}
    )
    return owner, directory, graph


@pytest.mark.parametrize(
    "operation, pending, completed",
    [
        ("migrate", "PREPARING", "COMMITTED"),
        ("rollback", "ROLLING_BACK", "ROLLED_BACK"),
    ],
)
@pytest.mark.parametrize(
    "interrupted_write",
    [
        "profile.json",
        "active.json",
        "profiles.json",
        "runtime-binding.json",
        "migration-v2.json",
    ],
)
def test_interrupted_transition_blocks_dispatch(
    transition_owner,
    bundle,
    monkeypatch,
    operation,
    pending,
    completed,
    interrupted_write,
):
    owner, directory, graph = transition_owner
    identity = directory.name
    if operation == "rollback":
        assert versions.migrate(owner, identity, bundle)["state"] == "COMMITTED"
        assert versions.select_bundle(directory.parent, identity) == bundle
    else:
        assert versions.select_bundle(directory.parent, identity) is None
    original_graph = graph.read_bytes()
    write = owner.state.write

    def interrupt(path, value):
        if path.name == interrupted_write and (
            path.name != "migration-v2.json" or value["phase"] == completed
        ):
            raise OSError("synthetic interrupted write")
        write(path, value)

    monkeypatch.setattr(owner.state, "write", interrupt)
    with pytest.raises(OSError, match="synthetic interrupted write"):
        if operation == "migrate":
            versions.migrate(owner, identity, bundle)
        else:
            versions.rollback(owner, identity)

    journal = owner.state.read(directory / "migration-v2.json")
    assert journal["phase"] == pending
    assert journal["before"]["graph"]["graph_sha256"] == versions.sha(graph)
    assert graph.read_bytes() == original_graph
    with pytest.raises(PermissionError, match="not committed"):
        versions.select_bundle(directory.parent, identity)


@pytest.mark.parametrize("legacy_disabled_record", [False, True])
def test_existing_migrate_command_recovers_only_the_exact_disabled_predecessor(
    transition_owner, bundle, bundle_factory, legacy_disabled_record
):
    owner, directory, graph = transition_owner
    identity = directory.name
    assert versions.migrate(owner, identity, bundle)["state"] == "COMMITTED"
    coordination = {"schema": 2, "generation": 2}
    owner.state.write(directory / "recovery-v2.json", coordination)
    assert (
        versions.rollback(owner, identity)["state"]
        == "BLOCKED_INCOMPATIBLE_COORDINATION"
    )

    binding_path = directory / "runtime-binding.json"
    binding = owner.state.read(binding_path)
    assert binding["bundle"] == str(bundle)
    if legacy_disabled_record:
        binding.pop("bundle")
        owner.state.write(binding_path, binding)
    journal_path = directory / "migration-v2.json"
    old_journal = journal_path.read_bytes()
    original_graph = graph.read_bytes()
    successor = bundle_factory(b"VERSION = 'successor'\n")
    args = SimpleNamespace(
        action="migrate",
        profile=identity,
        bundle=successor,
        from_version=None,
        fixture_registry=directory.parent,
    )
    parser = argparse.ArgumentParser()
    with pytest.raises(PermissionError, match="disabled"):
        versions.select_bundle(directory.parent, identity)
    with pytest.raises(PermissionError, match="disabled"):
        versions._profile_action(parser, args, owner, True)
    args.from_version = successor.name
    with pytest.raises(ValueError, match="exact retained"):
        versions._profile_action(parser, args, owner, True)
    assert journal_path.read_bytes() == old_journal
    assert owner.state.read(binding_path) == binding

    args.from_version = bundle.name
    assert versions._profile_action(parser, args, owner, True)["state"] == "COMMITTED"
    assert versions.select_bundle(directory.parent, identity) == successor
    assert owner.state.read(directory / "recovery-v2.json") == coordination
    assert graph.read_bytes() == original_graph
    transaction = owner.state.read(journal_path)
    assert transaction["before"]["runtime_binding"] == binding
    assert (
        list((directory / "migration-history").glob("*.json"))[0].read_bytes()
        == old_journal
    )

    assert versions.rollback(owner, identity)["state"] == "ROLLED_BACK"
    with pytest.raises(PermissionError, match="disabled"):
        versions.select_bundle(directory.parent, identity)
    assert (
        versions._select_disabled_migration_bundle(owner, identity, bundle.name)
        == bundle
    )


def test_migration_rejects_an_external_bundle_before_loading_its_owner(
    transition_owner, bundle, tmp_path, monkeypatch
):
    import shutil

    owner, directory, graph = transition_owner
    foreign = tmp_path / "external" / bundle.name
    shutil.copytree(bundle, foreign)
    monkeypatch.setattr(
        versions, "bundle_owner", lambda *_: pytest.fail("foreign runtime loaded")
    )
    before = graph.read_bytes()
    with pytest.raises(ValueError, match="VERSIONS"):
        versions.migrate(owner, directory.name, foreign)
    assert graph.read_bytes() == before
    assert not (directory / "migration-v2.json").exists()


@pytest.mark.parametrize("phase", ["RESOLVED", "LAUNCHING"])
def test_pending_recovery_grant_prevents_migration_before_preparing(
    transition_owner, bundle, phase
):
    owner, directory, graph = transition_owner
    owner.state.write(
        directory / "recovery-v2.json", {"schema": 2, "history": [{"phase": phase}]}
    )
    before = {path: path.read_bytes() for path in directory.iterdir()}
    with pytest.raises(ValueError, match="grant awaits"):
        versions.migrate(owner, directory.name, bundle)
    assert {path: path.read_bytes() for path in directory.iterdir()} == before
    assert graph.read_bytes() == b'{"fixture":true}\n'


def test_rollback_refuses_a_transaction_replaced_while_waiting_for_the_registry(
    transition_owner, bundle, bundle_factory, monkeypatch
):
    from contextlib import contextmanager

    owner, directory, graph = transition_owner
    versions.migrate(owner, directory.name, bundle)
    successor = bundle_factory(b"VERSION = 'successor'\n")
    entered = []

    @contextmanager
    def lock(path):
        if path == directory.parent / "registry.lock" and not entered:
            entered.append(True)
            versions.migrate(owner, directory.name, successor, from_version=bundle.name)
        yield

    monkeypatch.setattr(owner.core, "LifetimeLock", lock)
    with pytest.raises(ValueError, match="Concurrent migration"):
        versions.rollback(owner, directory.name)
    assert versions.select_bundle(directory.parent, directory.name) == successor
    assert owner.state.read(directory / "migration-v2.json")["phase"] == "COMMITTED"
    assert graph.read_bytes() == b'{"fixture":true}\n'


def test_missing_predecessor_dependency_disables_rollback_like_changed_bytes(
    transition_owner, bundle
):
    owner, directory, graph = transition_owner
    dependency = directory / "legacy-dependency.py"
    dependency.write_bytes(b"qualified legacy dependency")
    owner.state.write(
        directory / "active.json",
        {"hashes": {str(dependency): versions.sha(dependency)}},
    )
    versions.migrate(owner, directory.name, bundle)
    dependency.unlink()
    result = versions.rollback(owner, directory.name)
    assert result["state"] == "BLOCKED_LEGACY_RUNTIME_DRIFT"
    assert owner.state.read(directory / "runtime-binding.json")["state"] == "disabled"
    with pytest.raises(PermissionError, match="disabled"):
        versions.select_bundle(directory.parent, directory.name)
    assert graph.read_bytes() == b'{"fixture":true}\n'


@pytest.mark.parametrize("transition_point", ["between_records", "during_verification"])
def test_dispatch_never_returns_a_bundle_from_incoherent_migration_records(
    transition_owner, bundle, bundle_factory, monkeypatch, transition_point
):
    owner, directory, _ = transition_owner
    versions.migrate(owner, directory.name, bundle)
    successor = bundle_factory(b"VERSION = 'pending'\n")
    original_verify = versions.verify
    original_read = versions._optional_bytes
    changed = []

    def change():
        changed.append(True)
        transaction = owner.state.read(directory / "migration-v2.json")
        transaction.update(
            id="c" * 32,
            phase="PREPARING",
            bundle=str(successor),
            version=successor.name,
        )
        owner.state.write(directory / "migration-v2.json", transaction)
        owner.state.write(
            directory / "runtime-binding.json",
            {
                "schema": 2,
                "state": "active",
                "bundle": str(successor),
                "version": successor.name,
            },
        )

    def read(path):
        if (
            transition_point == "between_records"
            and path.name == "runtime-binding.json"
            and not changed
        ):
            change()
        return original_read(path)

    def verify(path):
        result = original_verify(path)
        if transition_point == "during_verification" and not changed:
            change()
        return result

    monkeypatch.setattr(versions, "_optional_bytes", read)
    monkeypatch.setattr(versions, "verify", verify)
    with pytest.raises(PermissionError, match="committed transaction|changed during"):
        versions.select_bundle(directory.parent, directory.name)


def test_reconcile_reads_an_enumerated_owned_plan(tmp_path):
    from pathlib import Path
    from unittest.mock import Mock

    directory = tmp_path / "target"
    plans = directory / "reconcile-plans"
    plans.mkdir(parents=True)
    path = plans / "reviewed.json"
    path.write_text('{"reviewed": true}', encoding="utf-8")
    apply = Mock(
        return_value={
            "id": "resolution",
            "new_generation": "generation",
            "phase": "RESOLVED",
        }
    )
    selected = SimpleNamespace(
        specification=lambda *_: ({"state": str(directory)}, {}),
        runtime_owner=lambda: "fixture-owner",
        state=SimpleNamespace(
            scope=SimpleNamespace(physical=lambda value: value),
            read=lambda value, **_: json.loads(Path(value).read_bytes()),
        ),
        reconciler=SimpleNamespace(apply=apply),
    )
    args = SimpleNamespace(action="reconcile-apply", profile="target", plan=path)
    assert (
        versions._reconcile_profile(argparse.ArgumentParser(), args, selected, False)[
            "state"
        ]
        == "RESOLVED"
    )
    assert apply.call_args.args[-1] == {"reviewed": True}


def test_rollback_checks_the_entire_predecessor_bundle(
    transition_owner, bundle, bundle_factory
):
    owner, directory, graph = transition_owner
    versions.migrate(owner, directory.name, bundle)
    successor = bundle_factory(b"VERSION = 'next'\n")
    versions.migrate(owner, directory.name, successor, from_version=bundle.name)
    (bundle / "runtime/unlisted.py").write_bytes(b"unlisted predecessor dependency")
    result = versions.rollback(owner, directory.name)
    assert result["state"] == "BLOCKED_LEGACY_RUNTIME_DRIFT"
    assert owner.state.read(directory / "runtime-binding.json")["state"] == "disabled"
    assert graph.read_bytes() == b'{"fixture":true}\n'


def test_historical_audit_uses_the_same_unknown_identity_normalization():
    from scripts.ai.mcp import memory_reconciliation

    owner = SimpleNamespace(state=SimpleNamespace(identity=lambda *_: "ABSENT"))
    observed = {"status": {}, "owner-launch": {}}
    states = memory_reconciliation.process_identities(owner, observed)
    assert states["owner"] == states["launch"] == "UNKNOWN"
    assert "BLOCK_PROCESS_IDENTITY_UNKNOWN" in versions._audit_block_reasons(
        states, {"schema": 2}, True, True
    )


def test_duplicate_build_cleanup_never_accepts_a_foreign_directory(
    tmp_path, monkeypatch
):
    root = tmp_path / "versions"
    root.mkdir()
    foreign = tmp_path / "building-foreign"
    foreign.mkdir()
    sentinel = foreign / "preserved"
    sentinel.write_bytes(b"foreign data")
    monkeypatch.setattr(versions, "VERSIONS", root)
    with pytest.raises(ValueError, match="escaped"):
        versions._discard_duplicate_build(foreign)
    assert sentinel.read_bytes() == b"foreign data"


def test_verified_duplicate_bundle_releases_its_current_staging(bundle, monkeypatch):
    import shutil

    monkeypatch.setattr(versions, "VERSIONS", bundle.parent)
    staging = bundle.parent / "building-current"
    shutil.copytree(bundle, staging)
    assert versions._publish_bundle(staging, bundle) == bundle
    assert not staging.exists()
    versions.verify(bundle)


def test_unlisted_file_in_predecessor_bundle_blocks_rollback_before_commit(
    transition_owner, bundle, bundle_factory
):
    owner, directory, graph = transition_owner
    versions.migrate(owner, directory.name, bundle)
    successor = bundle_factory(b"VERSION = 'successor'\n")
    versions.migrate(owner, directory.name, successor, from_version=bundle.name)
    (bundle / "runtime/injected.py").write_bytes(b"unregistered executable")
    result = versions.rollback(owner, directory.name)
    assert result["state"] == "BLOCKED_LEGACY_RUNTIME_DRIFT"
    assert owner.state.read(directory / "migration-v2.json")["phase"] == "COMMITTED"
    assert owner.state.read(directory / "runtime-binding.json")["state"] == "disabled"
    assert graph.read_bytes() == b'{"fixture":true}\n'


@pytest.mark.parametrize("valid", [True, False, None])
@pytest.mark.parametrize("prepared", [False, True])
def test_interrupted_old_runtime_can_upgrade_only_with_a_zero_request_start_receipt(
    transition_owner, bundle, bundle_factory, valid, monkeypatch, prepared
):
    from scripts.ai.mcp import memory_reconciliation as recovery

    owner, directory, graph = transition_owner
    monkeypatch.setattr(
        owner.state,
        "identity",
        lambda record, role: "DEAD" if record and role + "_pid" in record else "ABSENT",
        raising=False,
    )
    versions.migrate(owner, directory.name, bundle)
    stamp = {"graph_sha256": versions.sha(graph)}
    generation = "a" * 32
    coord = {
        "schema": 2,
        "active_block": None,
        "history": [
            {
                "id": "b" * 32,
                "phase": "LAUNCHING",
                "new_generation": generation,
                "snapshot": {"profile": directory.name, "graph": stamp},
            }
        ],
    }
    if prepared:
        coord["history"][-1].update(
            launch_stage="PREPARED", owner_pid=77, owner_birth=1
        )
    owner.state.write(directory / "recovery-v2.json", coord)
    owner.state.write(
        directory / "status.json",
        (
            {"generation": generation}
            if valid is None
            else {"generation": generation, "owner_pid": 123456, "owner_birth": 1}
        ),
    )
    owner.state.write(
        directory / "work.json",
        {
            "schema": 2,
            "profile": directory.name,
            "generation": generation,
            "phase": "starting",
            "accepted_count": 1 if valid is False else 0,
            "request_id": None,
            "mutating": False,
            "graph": stamp,
        },
    )
    successor = bundle_factory(b"VERSION = 'new-reconciler'\n")
    if valid:
        assert (
            versions.migrate(
                owner, directory.name, successor, from_version=bundle.name
            )["state"]
            == "COMMITTED"
        )
        preserved = owner.state.read(directory / "recovery-v2.json")
        assert preserved == coord
        observed = recovery.records(owner, {"state": str(directory)})
        assert recovery.block_identity(observed, preserved).startswith("interrupted-")
        assert versions.select_bundle(directory.parent, directory.name) == successor
    else:
        with pytest.raises(ValueError, match="grant awaits"):
            versions.migrate(owner, directory.name, successor, from_version=bundle.name)
        assert owner.state.read(directory / "runtime-binding.json")["bundle"] == str(
            bundle
        )
    assert graph.read_bytes() == b'{"fixture":true}\n'


def test_active_runtime_without_committed_journal_is_refused(
    tmp_path, bundle, monkeypatch
):
    monkeypatch.setattr(versions, "VERSIONS", bundle.parent)
    directory = tmp_path / "active-profile"
    directory.mkdir()
    binding = directory / "runtime-binding.json"
    binding.write_text(
        json.dumps(
            {
                "schema": 2,
                "state": "active",
                "version": bundle.name,
                "bundle": str(bundle),
            }
        ),
        encoding="utf-8",
    )
    before = binding.read_bytes()
    with pytest.raises(PermissionError, match="no committed migration"):
        versions.select_bundle(tmp_path, directory.name)
    assert binding.read_bytes() == before
    assert not (directory / "migration-v2.json").exists()


@pytest.mark.parametrize("cleanup_fails", [False, True])
def test_failed_build_cleans_only_its_staging_and_preserves_original_error(
    tmp_path, monkeypatch, cleanup_fails
):
    host, root = tmp_path / "host", tmp_path / "versions"
    host.mkdir()
    for name in ("project-memory-scoped-client.py", "host-servers.json"):
        (host / name).write_text("synthetic fixture", encoding="utf-8")
    root.mkdir()
    published = root / ("a" * 64)
    published.mkdir()
    sentinel = published / "preserved"
    sentinel.write_bytes(b"published")
    monkeypatch.setattr(versions, "HOST", host)
    monkeypatch.setattr(versions, "VERSIONS", root)
    created = []

    def copy(_owner, _hashes, staging):
        created.append(staging)
        service = staging / "tools/shared-mcp"
        service.mkdir(parents=True)
        (service / "changed.py").write_text("fixture", encoding="utf-8")

    def fail(*_):
        raise ValueError("fixture source drift")

    monkeypatch.setattr(versions, "_copy_runtime_dependencies", copy)
    monkeypatch.setattr(versions, "_adapt_service_text", fail)
    if cleanup_fails:

        def refuse_cleanup(_):
            raise OSError("fixture cleanup failure")

        monkeypatch.setattr(versions, "_discard_duplicate_build", refuse_cleanup)
    owner = SimpleNamespace(candidate=lambda *_: {"hashes": {}})
    with pytest.raises(ValueError, match="fixture source drift"):
        versions.build(owner, {}, {})
    assert len(created) == 1 and created[0].exists() is cleanup_fails
    assert sentinel.read_bytes() == b"published"


def test_failed_bundle_assembly_cleans_its_staging_only(bundle, monkeypatch):
    owner = SimpleNamespace(candidate=lambda *_: {"hashes": {}})
    monkeypatch.setattr(versions, "VERSIONS", bundle.parent)
    monkeypatch.setattr(versions, "sha", lambda _: "fixture-digest")

    def copy_inputs(_owner, _hashes, staging):
        service = staging / "tools/shared-mcp"
        service.mkdir(parents=True)
        (service / "fixture.py").write_bytes(b"# candidate input\n")

    def reject(_file, _text):
        raise ValueError("reviewed source drift")

    monkeypatch.setattr(versions, "_copy_runtime_dependencies", copy_inputs)
    monkeypatch.setattr(versions, "_adapt_service_text", reject)
    with pytest.raises(ValueError, match="reviewed source drift"):
        versions.build(owner, {}, {})
    assert list(bundle.parent.iterdir()) == [bundle]


@pytest.mark.parametrize(
    "operation,completed", [("migrate", "COMMITTED"), ("rollback", "ROLLED_BACK")]
)
@pytest.mark.parametrize(
    "point",
    [
        "profile.json",
        "active.json",
        "profiles.json",
        "runtime-binding.json",
        "migration-v2.json",
    ],
)
def test_explicit_recovery_completes_the_same_interrupted_transition(
    transition_owner, bundle, monkeypatch, operation, completed, point
):
    owner, directory, graph = transition_owner
    identity = directory.name
    index_path = directory.parent / versions.PROFILE_INDEX
    index = owner.state.read(index_path)
    index["neighbor"] = {"preserved": True}
    owner.state.write(index_path, index)
    before_graph = graph.read_bytes()
    if operation == "rollback":
        legacy = directory / "legacy-runtime.py"
        legacy.write_bytes(b"# immutable legacy source fixture\n")
        owner.state.write(
            directory / versions.ACTIVE_INDEX,
            {"hashes": {str(legacy): versions.sha(legacy)}},
        )
        versions.migrate(owner, identity, bundle)
        graph.write_bytes(b'{"legitimate_change":"after migration"}\n')
        before_graph = graph.read_bytes()
    original_write = owner.state.write

    def fail(path, value):
        if path.name == point and (
            point != versions.MIGRATION_RECORD or value["phase"] == completed
        ):
            raise OSError("injected transition interruption")
        original_write(path, value)

    monkeypatch.setattr(owner.state, "write", fail)
    with pytest.raises(OSError, match="interruption"):
        if operation == "migrate":
            versions.migrate(owner, identity, bundle)
        else:
            versions.rollback(owner, identity)
    monkeypatch.setattr(owner.state, "write", original_write)
    transaction = owner.state.read(directory / versions.MIGRATION_RECORD)
    original_id = transaction["id"]
    assert (
        versions.recover_transition(owner, identity, original_id, fixture=True)["state"]
        == completed
    )
    assert owner.state.read(directory / versions.MIGRATION_RECORD)["id"] == original_id
    assert owner.state.read(index_path)["neighbor"] == {"preserved": True}
    assert graph.read_bytes() == before_graph
    assert versions.select_bundle(directory.parent, identity) == (
        bundle if operation == "migrate" else None
    )
    before = {
        path: path.read_bytes() for path in directory.rglob("*") if path.is_file()
    }
    assert versions.recover_transition(owner, identity, original_id, fixture=True)[
        "already_completed"
    ]
    assert {
        path: path.read_bytes() for path in directory.rglob("*") if path.is_file()
    } == before


@pytest.mark.parametrize(
    "change",
    [
        "transaction",
        "graph",
        "coordination",
        "profile",
        "active",
        "binding",
        "live_process",
        "index",
    ],
)
def test_transition_recovery_refuses_unreviewed_evidence_without_writes(
    transition_owner, bundle, monkeypatch, change
):
    owner, directory, graph = transition_owner
    write = owner.state.write

    def interrupt(path, value):
        if path.name == versions.RUNTIME_BINDING:
            raise OSError("injected binding interruption")
        write(path, value)

    monkeypatch.setattr(owner.state, "write", interrupt)
    with pytest.raises(OSError):
        versions.migrate(owner, directory.name, bundle)
    monkeypatch.setattr(owner.state, "write", write)
    transaction = owner.state.read(directory / versions.MIGRATION_RECORD)
    identity = transaction["id"]
    if change == "transaction":
        identity = "wrong-transaction"
    elif change == "graph":
        graph.write_bytes(b'{"changed":true}')
    elif change == "coordination":
        write(directory / versions.RECOVERY_RECORD, {"schema": 2, "changed": True})
    elif change in {"profile", "active", "binding"}:
        filename = {
            "profile": versions.PROFILE_DESCRIPTOR,
            "active": versions.ACTIVE_INDEX,
            "binding": versions.RUNTIME_BINDING,
        }[change]
        write(directory / filename, {"unapproved": True})
    elif change == "index":
        index = owner.state.read(directory.parent / versions.PROFILE_INDEX)
        index[directory.name]["unexpected_endpoint"] = 9999
        write(directory.parent / versions.PROFILE_INDEX, index)
    elif change == "live_process":

        def alive(*args):
            raise ValueError("Profile is not proven dormant")

        monkeypatch.setattr(versions, "dormant", alive)
    before = {
        path: path.read_bytes()
        for path in directory.parent.rglob("*")
        if path.is_file()
    }
    with pytest.raises(ValueError):
        versions.recover_transition(owner, directory.name, identity, fixture=True)
    assert {
        path: path.read_bytes()
        for path in directory.parent.rglob("*")
        if path.is_file()
    } == before


def test_recovery_itself_can_resume_after_a_second_interruption(
    transition_owner, bundle, monkeypatch
):
    owner, directory, graph = transition_owner
    write = owner.state.write

    def interrupted(path, value):
        if path.name == versions.RUNTIME_BINDING:
            raise OSError("temporary disk failure")
        write(path, value)

    monkeypatch.setattr(owner.state, "write", interrupted)
    with pytest.raises(OSError):
        versions.migrate(owner, directory.name, bundle)
    transaction = owner.state.read(directory / versions.MIGRATION_RECORD)
    with pytest.raises(OSError):
        versions.recover_transition(
            owner, directory.name, transaction["id"], fixture=True
        )
    assert (
        owner.state.read(directory / versions.MIGRATION_RECORD)["phase"] == "PREPARING"
    )
    monkeypatch.setattr(owner.state, "write", write)
    assert (
        versions.recover_transition(
            owner, directory.name, transaction["id"], fixture=True
        )["state"]
        == "COMMITTED"
    )
    assert graph.read_bytes() == b'{"fixture":true}\n'


def test_legacy_without_activation_has_a_defined_rollback_refusal(
    transition_owner, bundle
):
    owner, directory, graph = transition_owner
    (directory / versions.ACTIVE_INDEX).unlink()
    versions.migrate(owner, directory.name, bundle)
    assert (
        versions.rollback(owner, directory.name)["state"]
        == "BLOCKED_LEGACY_RUNTIME_DRIFT"
    )
    assert graph.read_bytes() == b'{"fixture":true}\n'


@pytest.mark.parametrize("raises", [False, True])
def test_loading_a_bundle_with_bytecode_enabled_preserves_its_exact_files(
    tmp_path, raises
):
    import os
    import subprocess
    import sys

    source = tmp_path / "candidate"
    service = source / "tools/shared-mcp"
    service.mkdir(parents=True)
    helper = service / "helper.py"
    helper.write_text("VALUE=1\n", encoding="utf-8")
    text = 'import importlib.util\nfrom pathlib import Path\np=Path(__file__).with_name("helper.py")\ns=importlib.util.spec_from_file_location("owned_helper",p)\nm=importlib.util.module_from_spec(s)\ns.loader.exec_module(m)\n'
    if raises:
        text += 'raise RuntimeError("injected owner load failure")\n'
    (service / "project-memory-owner.py").write_text(text, encoding="utf-8")
    manifest = {
        "schema": 2,
        "files": {
            p.relative_to(source).as_posix(): versions.sha(p)
            for p in source.rglob("*.py")
        },
    }
    raw = versions.canonical(manifest)
    (source / versions.BUNDLE_MANIFEST).write_bytes(raw)
    bundle = tmp_path / hashlib.sha256(raw).hexdigest()
    source.rename(bundle)
    module_path = Path(versions.__file__)
    program = """import sys
from pathlib import Path
namespace={"__file__":sys.argv[1],"__name__":"isolated_versions"}
exec(compile(Path(sys.argv[1]).read_text(encoding="utf-8"),sys.argv[1],"exec"),namespace)
sys.dont_write_bytecode=False
expected_failure = sys.argv[3] == "True"
try:
    namespace["bundle_owner"](Path(sys.argv[2]))
except RuntimeError as error:
    assert expected_failure
    assert str(error) == "injected owner load failure"
else:
    assert not expected_failure, "Expected owner load failure did not occur"
assert sys.dont_write_bytecode is False
namespace["verify"](Path(sys.argv[2]))
"""
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            "-B",
            "-c",
            program,
            str(module_path),
            str(bundle),
            str(raises),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
    )
    assert result.returncode == 0, result.stderr
    assert not list(bundle.rglob("__pycache__"))


def test_migration_guards_late_runtime_imports_and_restores_bytecode_mode(
    transition_owner, bundle, monkeypatch
):
    import sys

    owner, directory, _ = transition_owner
    original = owner.candidate

    def candidate(*args):
        assert sys.dont_write_bytecode is True
        return original(*args)

    monkeypatch.setattr(owner, "candidate", candidate)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = False
    try:
        assert versions.migrate(owner, directory.name, bundle)["state"] == "COMMITTED"
        assert sys.dont_write_bytecode is False
    finally:
        sys.dont_write_bytecode = previous


@pytest.mark.parametrize("guard", ["scope", "claim"])
def test_partial_transition_still_requires_current_scope_and_graph_claim(
    transition_owner, bundle, monkeypatch, guard
):
    owner, directory, graph = transition_owner
    descriptor = owner.state.read(directory / versions.PROFILE_DESCRIPTOR)
    descriptor["profile"]["id"] = directory.name
    owner.state.write(directory / versions.PROFILE_DESCRIPTOR, descriptor)
    original = owner.state.write

    def interrupt(path, value):
        if path.name == versions.RUNTIME_BINDING:
            raise OSError("injected interruption")
        original(path, value)

    monkeypatch.setattr(owner.state, "write", interrupt)
    with pytest.raises(OSError):
        versions.migrate(owner, directory.name, bundle)
    monkeypatch.setattr(owner.state, "write", original)
    transaction = owner.state.read(directory / versions.MIGRATION_RECORD)

    def revalidate(_profile):
        if guard == "scope":
            raise ValueError("Current account or branch changed")

    owner.state.scope.revalidate = revalidate
    owner.registry.claim = lambda _: "approved-graph"
    before = {
        path: path.read_bytes()
        for path in directory.parent.rglob("*")
        if path.is_file()
    }
    with pytest.raises(ValueError, match="account or branch|graph claim"):
        versions.recover_transition(owner, directory.name, transaction["id"])
    assert {
        path: path.read_bytes()
        for path in directory.parent.rglob("*")
        if path.is_file()
    } == before
    assert graph.read_bytes() == b'{"fixture":true}\n'


@pytest.mark.parametrize("identity_state", ["ALIVE", "UNKNOWN", "DEAD"])
def test_migration_cannot_overtake_a_prepared_owner_before_status_publication(
    transition_owner, bundle, bundle_factory, monkeypatch, identity_state
):
    import os
    from scripts.ai.mcp import memory_reconciliation as recovery

    owner, directory, graph = transition_owner
    versions.migrate(owner, directory.name, bundle)
    stamp = {"graph_sha256": versions.sha(graph)}
    owner.state.write(
        directory / "status.json",
        {"owner_pid": 77, "owner_birth": 1, "generation": "c" * 32},
    )
    owner.state.write(
        directory / "work.json",
        {
            "schema": 2,
            "profile": directory.name,
            "generation": "c" * 32,
            "phase": "idle",
            "accepted_count": 0,
            "mutating": False,
            "graph": stamp,
        },
    )
    observed = recovery.records(owner, {"state": str(directory)})
    owner.state.write(
        directory / versions.RECOVERY_RECORD,
        {
            "schema": 2,
            "active_block": None,
            "history": [
                {
                    "id": "b" * 32,
                    "phase": "LAUNCHING",
                    "launch_stage": "PREPARED",
                    "owner_pid": os.getpid(),
                    "owner_birth": 42,
                    "new_generation": "a" * 32,
                    "snapshot": {
                        "profile": directory.name,
                        "graph": stamp,
                        "records": {
                            name: recovery.digest(record)
                            for name, record in observed.items()
                        },
                    },
                }
            ],
        },
    )
    owner.state.identity = lambda record, role: (
        identity_state
        if record and record.get(role + "_pid") == os.getpid()
        else "DEAD"
        if record and role + "_pid" in record
        else "ABSENT"
    )
    successor = bundle_factory(b"VERSION='new'\n")
    before = {
        path: path.read_bytes() for path in directory.rglob("*") if path.is_file()
    }
    with pytest.raises(ValueError, match="grant awaits"):
        versions.migrate(owner, directory.name, successor, from_version=bundle.name)
    assert {
        path: path.read_bytes() for path in directory.rglob("*") if path.is_file()
    } == before


def test_interrupted_rollback_refuses_changes_since_its_own_graph_snapshot(
    transition_owner, bundle, monkeypatch
):
    owner, directory, graph = transition_owner
    legacy = directory / "legacy-runtime.py"
    legacy.write_bytes(b"# immutable legacy source fixture\n")
    owner.state.write(
        directory / versions.ACTIVE_INDEX,
        {"hashes": {str(legacy): versions.sha(legacy)}},
    )
    versions.migrate(owner, directory.name, bundle)
    graph.write_bytes(b'{"legitimate_change":"before rollback"}\n')
    original = owner.state.write

    def interrupted(path, value):
        if path.name == versions.PROFILE_DESCRIPTOR:
            raise OSError("injected rollback interruption")
        original(path, value)

    with monkeypatch.context() as patch:
        patch.setattr(owner.state, "write", interrupted)
        with pytest.raises(OSError, match="rollback interruption"):
            versions.rollback(owner, directory.name)
    transaction = owner.state.read(directory / versions.MIGRATION_RECORD)
    assert transaction["rollback_snapshot"]["graph"] == {
        "graph_sha256": versions.sha(graph)
    }
    graph.write_bytes(b'{"unexpected_change":"during rollback"}\n')
    before = {
        path: path.read_bytes()
        for path in directory.parent.rglob("*")
        if path.is_file()
    }
    with pytest.raises(ValueError, match="Graph changed"):
        versions.recover_transition(
            owner, directory.name, transaction["id"], fixture=True
        )
    assert {
        path: path.read_bytes()
        for path in directory.parent.rglob("*")
        if path.is_file()
    } == before


@pytest.mark.parametrize("changed_graph", [False, True])
def test_legacy_interrupted_rollback_requires_its_preserved_graph_snapshot(
    transition_owner, bundle, monkeypatch, changed_graph
):
    owner, directory, graph = transition_owner
    legacy = directory / "legacy-runtime.py"
    legacy.write_bytes(b"# immutable legacy source fixture\n")
    owner.state.write(
        directory / versions.ACTIVE_INDEX,
        {"hashes": {str(legacy): versions.sha(legacy)}},
    )
    versions.migrate(owner, directory.name, bundle)
    if changed_graph:
        graph.write_bytes(b'{"legitimate_change":"after migration"}\n')
    original = owner.state.write

    def interrupted(path, value):
        if path.name == versions.PROFILE_DESCRIPTOR:
            raise OSError("legacy rollback interruption")
        original(path, value)

    with monkeypatch.context() as patch:
        patch.setattr(owner.state, "write", interrupted)
        with pytest.raises(OSError, match="legacy rollback"):
            versions.rollback(owner, directory.name)
    transaction = owner.state.read(directory / versions.MIGRATION_RECORD)
    transaction.pop("rollback_snapshot")  # Earlier runtime journal format.
    original(directory / versions.MIGRATION_RECORD, transaction)
    before = {
        path: path.read_bytes()
        for path in directory.parent.rglob("*")
        if path.is_file()
    }
    if changed_graph:
        with pytest.raises(ValueError, match="Graph changed"):
            versions.recover_transition(
                owner, directory.name, transaction["id"], fixture=True
            )
        assert {
            path: path.read_bytes()
            for path in directory.parent.rglob("*")
            if path.is_file()
        } == before
    else:
        assert (
            versions.recover_transition(
                owner, directory.name, transaction["id"], fixture=True
            )["state"]
            == "ROLLED_BACK"
        )
