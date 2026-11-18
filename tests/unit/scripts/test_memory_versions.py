"""Immutable dependency identity and fail-closed profile dispatch controls."""

import argparse
import hashlib
import json
from contextlib import nullcontext
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


@pytest.mark.parametrize("valid", [True, False])
def test_interrupted_old_runtime_can_upgrade_only_with_a_zero_request_start_receipt(
    transition_owner, bundle, bundle_factory, valid
):
    from scripts.ai.mcp import memory_reconciliation as recovery

    owner, directory, graph = transition_owner
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
    owner.state.write(directory / "recovery-v2.json", coord)
    owner.state.write(directory / "status.json", {"generation": generation})
    owner.state.write(
        directory / "work.json",
        {
            "schema": 2,
            "profile": directory.name,
            "generation": generation,
            "phase": "starting",
            "accepted_count": 0 if valid else 1,
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
