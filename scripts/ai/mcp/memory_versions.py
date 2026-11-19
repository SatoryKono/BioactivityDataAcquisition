"""Build and select immutable Memory runtime closures without editing legacy files.

Each bundle contains Python, Node, the checked engine, service sources and the
resolved MCP SDK dependency closure. Profile migration changes only one entry
under the existing registry lock; graph contents and credentials are retained.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import threading
from contextlib import contextmanager
import uuid
from copy import deepcopy
from pathlib import Path

HOST = Path("D:/pc-agent/tools/shared-mcp")
VERSIONS = Path("D:/pc-agent/tools/memory-runtime-versions")
BASE_PYTHON = Path("C:/Users/Fedor/AppData/Local/Programs/Python/Python313")
VENV = Path("D:/github/BioactivityDataAcquisition/.venv-win")
SDK_ROOT = Path("D:/pc-agent/tools/mcp/markdownify/node_modules")


BUNDLE_MANIFEST = "bundle.json"
RUNTIME_BINDING = "runtime-binding.json"
MIGRATION_RECORD = "migration-v2.json"
SITE_PACKAGES = "Lib/site-packages"
PROFILE_INDEX = "profiles.json"
ACTIVE_INDEX = "active.json"
PROFILE_DESCRIPTOR = "profile.json"
RECOVERY_RECORD = "recovery-v2.json"
RECONCILIATION_SOURCE = "memory_reconciliation.py"
REGISTRY_LOCK = "registry.lock"
PROFILE_LOCK = "transition.lock"
GRAPH_OWNER_LOCK = ".memory.service-owner.lock"


_BYTECODE_LOCK = threading.RLock()


@contextmanager
def _bytecode_guard():
    with _BYTECODE_LOCK:
        previous = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            yield
        finally:
            sys.dont_write_bytecode = previous


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@_bytecode_guard()
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def physical(path):
    if (
        not path.is_absolute()
        or ".." in path.parts
        or path.resolve(strict=True) != path
    ):
        raise ValueError("Immutable runtime path is not physical")
    for item in (path, *path.parents):
        if item.is_symlink() or getattr(item, "is_junction", lambda: False)():
            raise ValueError("Immutable runtime traverses a reparse point")
    return path


def verify(bundle):
    bundle = physical(bundle)
    raw = (bundle / BUNDLE_MANIFEST).read_bytes()
    manifest = json.loads(raw)
    if (
        manifest.get("schema") != 2
        or bundle.name != hashlib.sha256(raw).hexdigest()
        or not isinstance(manifest.get("files"), dict)
    ):
        raise ValueError("Immutable bundle identity mismatch")
    actual = set()
    for current, directories, files in os.walk(bundle, followlinks=False):
        for name in [*directories, *files]:
            path = Path(current) / name
            if getattr(path.lstat(), "st_file_attributes", 0) & 0x400:
                raise ValueError("Immutable bundle contains a reparse point")
        actual.update(
            (Path(current) / name).relative_to(bundle).as_posix()
            for name in files
            if Path(current) / name != bundle / BUNDLE_MANIFEST
        )
    if actual != set(manifest["files"]):
        raise ValueError("Immutable bundle file set changed")
    for relative, expected in manifest["files"].items():
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or sha(bundle / path) != expected:
            raise ValueError("Immutable bundle source/dependency drift")
    return manifest


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError("Legacy runtime contract changed; adaptation refused")
    return text.replace(before, after, 1)


def adapt_owner(text):
    text = replace_once(
        text,
        "def recovery(entry, value, *, self_owner=False):",
        "def legacy_recovery(entry, value, *, self_owner=False):",
    )
    anchor = "def environment():"
    additions = """def runtime_owner():
    from types import SimpleNamespace
    return SimpleNamespace(HERE=HERE, state=state, core=core, legacy_recovery=legacy_recovery)


reconciler = module("project-memory-reconciliation")


def recovery(entry, value, *, self_owner=False):
    return reconciler.decision(runtime_owner(), entry, value, self_owner=self_owner)


def connect(identity, fixture=False):
    entry, _ = specification(identity, fixture)
    if reconciler.blocked(runtime_owner(), entry):
        raise ValueError("Memory profile is blocked")
    token = core.credential()
    observed = health(entry, token)
    if not observed or not observed.get("ready") or observed.get("draining") or observed.get("uncertain"):
        raise ValueError("Memory owner is not ready; explicit administrator ensure is required")
    return entry, token, observed


"""
    text = replace_once(text, anchor, additions + anchor)
    text = text.replace(
        '(directory / "blocked.json").exists()',
        "reconciler.blocked(runtime_owner(), entry)",
    )
    text = text.replace(
        '("FRESH_START", "SAFE_IDLE_RESTART")',
        '("FRESH_START", "SAFE_IDLE_RESTART", "SAFE_RECONCILED_START")',
    )
    text = replace_once(
        text,
        "generation = uuid.uuid4().hex",
        "generation = reconciler.launch_generation(runtime_owner(), entry, value)",
    )
    text = replace_once(
        text,
        'state.write(directory / "blocked.json", {"decision": decision})',
        "reconciler.record_block(runtime_owner(), entry, decision)",
    )
    text = replace_once(
        text,
        'child.stdin.write((nonce + "\\n").encode())',
        'reconciler.authorize_gateway(runtime_owner(), entry, value, generation, record)\n                child.stdin.write((nonce + "\\n").encode())',
    )
    text = replace_once(
        text,
        'if info.get("ready"):\n                            deadline = None',
        'if info.get("ready"):\n                            reconciler.observe(runtime_owner(), entry, value, generation)\n                            deadline = None',
    )
    text = replace_once(
        text,
        "if stopped:\n                return 0",
        "if stopped:\n                reconciler.observe(runtime_owner(), entry, value, generation, idle=True)\n                return 0",
    )
    text = replace_once(
        text,
        'state.write(\n            directory / "blocked.json", {"decision": "RESTART_BUDGET_EXHAUSTED"}\n        )',
        'reconciler.record_block(runtime_owner(), entry, "RESTART_BUDGET_EXHAUSTED")',
    )
    text = replace_once(
        text,
        '"project-memory-owner.py",',
        '"project-memory-owner.py",\n        "project-memory-reconciliation.py",\n        "project-memory-scoped-client.py",',
    )
    text = replace_once(
        text, "deadline = time.monotonic() + 45", "deadline = time.monotonic() + 300"
    )
    text = replace_once(
        text,
        "deadline = time.monotonic() + 30\n            try:",
        "deadline = time.monotonic() + 180\n            try:",
    )
    return text


def adapt_gateway(text):
    text = replace_once(
        text,
        "function journal(phase, mutating = false) {",
        "let acceptedCount = 0;\nlet requestId = null;\nfunction journal(phase, mutating = false) {\n    if (phase === 'busy') {acceptedCount++; requestId = randomUUID();}",
    )
    return replace_once(
        text,
        "{generation: boot.generation, phase, mutating, graph: graphStamp()}",
        "{schema: 2, profile: boot.id, generation: boot.generation, phase, mutating, accepted_count: acceptedCount, request_id: requestId, graph: graphStamp()}",
    )


VERIFY_BOOTSTRAP = """# Verify the complete closure before importing site dependencies or serving.
import hashlib
import json
import os
bundle = HERE.parents[1]
manifest_raw = (bundle / "bundle.json").read_bytes()
if hashlib.sha256(manifest_raw).hexdigest() != bundle.name:
    raise SystemExit("Immutable runtime manifest mismatch")
manifest = json.loads(manifest_raw)
actual = set()
for current, directories, files in os.walk(bundle, followlinks=False):
    for name in [*directories, *files]:
        file = Path(current) / name
        if getattr(file.lstat(), "st_file_attributes", 0) & 0x400:
            raise SystemExit("Immutable runtime reparse point")
    actual.update((Path(current) / name).relative_to(bundle).as_posix()
                  for name in files if Path(current) / name != bundle / "bundle.json")
if actual != set(manifest["files"]):
    raise SystemExit("Immutable runtime file set changed")
for relative, expected in manifest["files"].items():
    file = bundle / relative
    if Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise SystemExit("Immutable runtime path changed")
    if hashlib.sha256(file.read_bytes()).hexdigest() != expected:
        raise SystemExit("Immutable runtime source drift")
"""


def _bundle_relative_path(source, node):
    if source.is_relative_to(HOST):
        return Path("tools/shared-mcp") / source.relative_to(HOST)
    elif source.is_relative_to(SDK_ROOT):
        return Path("tools/mcp/markdownify/node_modules") / source.relative_to(SDK_ROOT)
    elif source.is_relative_to(BASE_PYTHON):
        return Path("runtime/python") / source.relative_to(BASE_PYTHON)
    elif source.is_relative_to(VENV / SITE_PACKAGES):
        return Path("runtime/site-packages") / source.relative_to(VENV / SITE_PACKAGES)
    elif source.is_relative_to(VENV):
        return Path("runtime/venv") / source.relative_to(VENV)
    elif source == node:
        return Path("runtime/node.exe")
    else:
        raise ValueError("Unclassified runtime dependency")


def _copy_runtime_dependencies(owner, hashes, staging):
    checked_parents = set()
    for raw_path, expected in hashes.items():
        source = Path(raw_path)
        for parent in reversed(source.parents):
            if parent not in checked_parents:
                physical(parent)
                checked_parents.add(parent)
        if getattr(source.lstat(), "st_file_attributes", 0) & 0x400:
            raise ValueError("Runtime source is a reparse point")
        if sha(source) != expected:
            raise ValueError("Legacy closure changed during build")
        relative = _bundle_relative_path(source, owner.core.NODE)
        target = staging / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        if sha(target) != expected:
            raise ValueError("Runtime dependency changed while copying")


def _adapt_service_text(file, text):
    if file.name == "project-memory-owner.py":
        text = adapt_owner(text)
    if file.name == "project-memory-client.py":
        text = replace_once(
            text,
            "owner.ensure(args.profile, fixture)",
            "owner.connect(args.profile, fixture)",
        )
    if file.name == "project-memory-gateway.mjs":
        text = adapt_gateway(text)
    if file.name == "project-memory-connection.mjs":
        # Each health bridge verifies the entire closure before network IO.
        # A cold verification can exceed the legacy five-second GET budget.
        text = replace_once(
            text, "AbortSignal.timeout(5000)", "AbortSignal.timeout(120_000)"
        )
    if file.name == "github-grok-broker.mjs":
        text = replace_once(
            text,
            "this.client.connect(this.transport,{timeout:60000})",
            "this.client.connect(this.transport,{timeout:180000})",
        )
    if file.suffix == ".py":
        text = text.replace(
            '"C:/Users/Fedor/AppData/Local/Programs/Python/Python313/python.exe"',
            '(HERE.parents[1] / "runtime/python/python.exe")',
        )
        text = text.replace(
            '"D:/github/BioactivityDataAcquisition/.venv-win/Lib/site-packages"',
            'str(HERE.parents[1] / "runtime/site-packages")',
        )
    else:
        text = text.replace(
            "'C:/Users/Fedor/AppData/Local/Programs/Python/Python313/python.exe'",
            "path.resolve(here, '../../runtime/python/python.exe')",
        )
    if file.name == "supervisor.py":
        text = replace_once(
            text,
            "ROOT = Path('D:/pc-agent')",
            "ROOT = Path(__file__).resolve().parents[2]",
        )
        text = replace_once(
            text,
            "NODE = Path('C:/Program Files/nodejs/node.exe')",
            'NODE = ROOT / "runtime/node.exe"',
        )
        text = replace_once(
            text,
            "PYTHON = Path('C:/Users/Fedor/AppData/Local/Programs/Python/Python313/python.exe')",
            'PYTHON = ROOT / "runtime/python/python.exe"',
        )
    if file.name == "project-memory-bootstrap.py":
        text = replace_once(
            text,
            "HERE = Path(__file__).resolve().parent\n",
            "HERE = Path(__file__).resolve().parent\n" + VERIFY_BOOTSTRAP,
        )
    if file.name == "project-memory-runtime.py":
        text = replace_once(
            text,
            'pathlib.Path("D:/pc-agent/tools/mcp/markdownify/node_modules/@modelcontextprotocol/sdk")',
            'pathlib.Path(__file__).resolve().parents[1] / "mcp/markdownify/node_modules/@modelcontextprotocol/sdk"',
        )
        start = text.index("def python_hashes()")
        end = text.index('\n\nif __name__ == "__main__":', start)
        text = (
            text[:start]
            + """def python_hashes():
    root = pathlib.Path(__file__).resolve().parents[2]
    manifest = json.loads((root / "bundle.json").read_bytes())
    result = {}
    for relative in manifest["files"]:
        if relative.startswith("runtime/"):
            path = root / relative
            if path.resolve(strict=True) != path:
                raise ValueError("Runtime dependency path changed")
            result[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result
"""
            + text[end:]
        )
    return text


@_bytecode_guard()
def build(owner, entry, value):
    """Copy the reviewed legacy closure and deterministically adapt a new version."""
    hashes = owner.candidate(entry, value)["hashes"]
    hashes[str(HOST / "project-memory-scoped-client.py")] = sha(
        HOST / "project-memory-scoped-client.py"
    )
    hashes[str(HOST / "host-servers.json")] = sha(HOST / "host-servers.json")
    VERSIONS.mkdir(parents=True, exist_ok=True)
    physical(VERSIONS)
    staging = VERSIONS / ("building-" + uuid.uuid4().hex)
    staging.mkdir()
    try:
        return _build_version(owner, hashes, staging)
    except BaseException:
        if staging.exists():
            try:
                _discard_duplicate_build(staging)
            except Exception:
                pass  # Preserve the build error when safe cleanup cannot complete.
        raise


def _build_version(owner, hashes, staging):
    _copy_runtime_dependencies(owner, hashes, staging)
    service = staging / "tools/shared-mcp"
    source = Path(__file__).with_name(RECONCILIATION_SOURCE)
    shutil.copyfile(source, service / "project-memory-reconciliation.py")
    for file in service.glob("*"):
        if file.suffix not in {".py", ".mjs"}:
            continue
        text = file.read_text(encoding="utf-8").replace("\r\n", "\n")
        text = _adapt_service_text(file, text)
        file.write_text(text, encoding="utf-8", newline="\n")
    manifest = {
        "schema": 2,
        "recipe": {
            "builder_sha256": sha(Path(__file__)),
            "legacy_input": hashes,
            "reconciliation_sha256": sha(source),
        },
        "files": {
            p.relative_to(staging).as_posix(): sha(p)
            for p in sorted(staging.rglob("*"))
            if p.is_file()
        },
    }
    raw = canonical(manifest)
    identity = hashlib.sha256(raw).hexdigest()
    target = VERSIONS / identity
    (staging / BUNDLE_MANIFEST).write_bytes(raw)
    return _publish_bundle(staging, target)


def _discard_duplicate_build(staging):
    if staging.parent != VERSIONS or not staging.name.startswith("building-"):
        raise ValueError("Duplicate cleanup escaped the owned versions directory")
    physical(staging)
    for current, directories, files in os.walk(staging, followlinks=False):
        for name in [*directories, *files]:
            path = Path(current) / name
            if (
                getattr(path.lstat(), "st_file_attributes", 0) & 0x400
                or path.is_symlink()
            ):
                raise ValueError("Duplicate cleanup contains a reparse point")
    shutil.rmtree(staging)


def _publish_bundle(staging, target):
    if not target.exists():
        try:
            staging.rename(target)
        except OSError:
            if not target.is_dir():
                raise
    verify(target)
    if staging.exists():
        _discard_duplicate_build(staging)
    return target


@_bytecode_guard()
def bundle_owner(bundle, fixture_registry=None):
    verify(bundle)
    # The copied owner may import additional pinned dependencies lazily.
    owner = load(
        "versioned_memory_owner", bundle / "tools/shared-mcp/project-memory-owner.py"
    )
    if fixture_registry:
        owner.fixture_registry(str(fixture_registry))
    return owner


def dormant(owner, entry, value):
    record = owner.state.read(Path(entry["state"]) / "status.json")
    launch = owner.state.read(Path(entry["state"]) / "owner-launch.json")
    for source, roles in (
        (record, ("owner", "gateway", "backend")),
        (launch, ("owner",)),
    ):
        if any(
            owner.state.identity(source, role) not in {"DEAD", "ABSENT"}
            for role in roles
        ):
            raise ValueError("Profile is not proven dormant")
    return owner.state.graph_stamp(value)


def _retained_disabled_bundle(binding, prior, expected_version):
    version = binding.get("version")
    if (
        binding.get("schema") != 2
        or binding.get("state") != "disabled"
        or not isinstance(version, str)
        or len(version) != 64
        or any(char not in "0123456789abcdef" for char in version)
        or expected_version != version
    ):
        raise ValueError("Disabled recovery requires the exact retained --from-version")
    bundle = VERSIONS / version
    if binding.get("bundle", str(bundle)) != str(bundle):
        raise ValueError("Disabled recovery bundle does not match the binding")
    if prior.get("phase") == "COMMITTED":
        if prior.get("version") == version and prior.get("bundle") == str(bundle):
            return bundle
    if prior.get("phase") == "ROLLED_BACK":
        if prior.get("before", {}).get("runtime_binding") == binding:
            return bundle
    raise ValueError("Disabled recovery requires a matching completed migration record")


def _select_disabled_migration_bundle(owner, identity, from_version):
    if from_version is None:
        return None
    if Path(identity).name != identity or identity in {"", ".", ".."}:
        raise ValueError("Invalid recovery profile identity")
    directory = physical(owner.registry.ROOT / identity)
    binding = owner.state.read(directory / RUNTIME_BINDING)
    if not binding or binding.get("state") != "disabled":
        return None
    prior = owner.state.read(directory / MIGRATION_RECORD, max_bytes=32 * 1024 * 1024)
    return _retained_disabled_bundle(binding, prior or {}, from_version)


def _predecessor_consistent(binding, prior, entry, current):
    if prior.get("phase") == "COMMITTED":
        return prior.get("after_entry") == entry and prior.get("version") == current
    if prior.get("phase") == "ROLLED_BACK":
        before = prior.get("before", {})
        return before.get("entry") == entry and binding == before.get(
            "runtime_binding", {"schema": 2, "state": "legacy"}
        )
    return False


def _upgradeable_interrupted_launch(owner, directory, recovery_state, graph):
    current = load(
        "migration_reconciliation", Path(__file__).with_name(RECONCILIATION_SOURCE)
    )
    last = recovery_state["history"][-1]
    if (
        graph is None
        or recovery_state.get("active_block")
        or last.get("snapshot", {}).get("graph") != graph
    ):
        return False
    observed = current.records(owner, {"state": str(directory)})
    if (
        last.get("launch_stage") == "PREPARED"
        and owner.state.identity(last, "owner") != "DEAD"
    ):
        return False
    incident = current._interrupted_launch_block(observed, recovery_state)
    # PREPARED-only proof hashes profile/active records that migration rewrites.
    # Only a separate successor zero-request receipt survives that transition.
    return (
        current.process_verdict(owner, observed) is None
        and incident is not None
        and incident.startswith("interrupted-")
    )


def _check_pending_recovery(owner, directory, graph=None):
    recovery_state = owner.state.read(directory / RECOVERY_RECORD) or {}
    history = recovery_state.get("history", [])
    if history and history[-1].get("phase") == "LAUNCHING":
        if _upgradeable_interrupted_launch(owner, directory, recovery_state, graph):
            return
    if history and history[-1].get("phase") in {"RESOLVED", "LAUNCHING"}:
        raise ValueError("Recovery grant awaits its reviewed launch; migration refused")


def previous_migration(
    owner, directory, entry, expected_version, *, recover_disabled=False
):
    """Require an explicit, consistent predecessor before replacing its journal."""
    binding = owner.state.read(directory / RUNTIME_BINDING)
    prior = owner.state.read(directory / MIGRATION_RECORD, max_bytes=32 * 1024 * 1024)
    states = {"disabled"} if recover_disabled else {"active", "legacy"}
    if binding is None and prior is None:
        if expected_version is not None:
            raise ValueError("Unexpected predecessor version")
        return None, None
    if (
        not binding
        or not prior
        or binding.get("schema") != 2
        or binding.get("state") not in states
    ):
        raise ValueError("Incomplete predecessor migration; preserve its records")
    if recover_disabled:
        _retained_disabled_bundle(binding, prior, expected_version)
    current = "legacy" if binding["state"] == "legacy" else binding["version"]
    if expected_version != current:
        raise ValueError("Existing runtime requires its explicit --from-version")
    consistent = _predecessor_consistent(binding, prior, entry, current)
    identity = prior.get("id", "")
    if (
        not consistent
        or len(identity) != 32
        or any(c not in "0123456789abcdef" for c in identity)
    ):
        raise ValueError("Predecessor migration does not match current profile")
    return binding, prior


@_bytecode_guard()
def migrate(
    owner, identity, bundle, *, fixture=False, from_version=None, recover_disabled=False
):
    if bundle.parent != VERSIONS:
        raise ValueError(
            "Migration bundle must be in the registered VERSIONS directory"
        )
    new_owner = bundle_owner(bundle, owner.registry.ROOT if fixture else None)
    entry, value = owner.specification(identity, fixture)
    directory = Path(entry["state"])
    with owner.core.LifetimeLock(owner.registry.ROOT / REGISTRY_LOCK):
        with owner.core.LifetimeLock(directory / PROFILE_LOCK):
            with owner.core.LifetimeLock(
                Path(value["profile"]["graph"]).with_name(GRAPH_OWNER_LOCK)
            ):
                stamp = dormant(owner, entry, value)
                _check_pending_recovery(owner, directory, stamp)
                binding, prior = previous_migration(
                    owner,
                    directory,
                    entry,
                    from_version,
                    recover_disabled=recover_disabled,
                )
                if binding and binding.get("version") == bundle.name:
                    raise ValueError("Migration requires a different runtime version")
                index_path = owner.registry.ROOT / PROFILE_INDEX
                index = owner.state.read(index_path)
                if index.get(identity) != entry:
                    raise ValueError("Concurrent profile registration change")
                before = {
                    "entry": entry,
                    "descriptor": value,
                    "active": owner.state.read(
                        directory / ACTIVE_INDEX, max_bytes=32 * 1024 * 1024
                    ),
                    "graph": stamp,
                    "coordination": owner.state.read(directory / RECOVERY_RECORD),
                    "runtime_binding": binding or {"schema": 2, "state": "legacy"},
                }
                updated = deepcopy(value)
                updated["service_pins"] = new_owner.registry.provider.hashes()
                descriptor_raw = new_owner.state.scope.canonical(updated) + b"\n"
                new_entry = {
                    **entry,
                    "descriptor_sha256": hashlib.sha256(descriptor_raw).hexdigest(),
                }
                active = new_owner.candidate(new_entry, updated)
                transaction = {
                    "id": uuid.uuid4().hex,
                    "phase": "PREPARING",
                    "before": before,
                    "after_entry": new_entry,
                    "bundle": str(bundle),
                    "version": bundle.name,
                }
                transaction["after"] = {
                    "entry": new_entry,
                    "descriptor": updated,
                    "active": active,
                    "runtime_binding": {
                        "schema": 2,
                        "state": "active",
                        "bundle": str(bundle),
                        "version": bundle.name,
                        "transaction": transaction["id"],
                    },
                }
                path = directory / MIGRATION_RECORD
                if prior is not None:
                    history = directory / "migration-history"
                    owner.state.scope.physical(history, exists=False)
                    history.mkdir(exist_ok=True)
                    archive = history / (prior["id"] + ".json")
                    if archive.exists():
                        if (
                            owner.state.read(archive, max_bytes=32 * 1024 * 1024)
                            != prior
                        ):
                            raise ValueError(
                                "Archived migration differs; preserve current state"
                            )
                    else:
                        owner.state.write(archive, prior)
                    transaction["previous_migration"] = {
                        "path": str(archive),
                        "sha256": sha(archive),
                    }
                owner.state.write(path, transaction)
                owner.state.write(directory / PROFILE_DESCRIPTOR, updated)
                owner.state.write(directory / ACTIVE_INDEX, active)
                index[identity] = new_entry
                owner.state.write(index_path, index)
                owner.state.write(
                    directory / RUNTIME_BINDING,
                    {
                        "schema": 2,
                        "state": "active",
                        "bundle": str(bundle),
                        "version": bundle.name,
                        "transaction": transaction["id"],
                    },
                )
                if dormant(new_owner, new_entry, updated) != stamp:
                    raise ValueError(
                        "Graph changed during migration; route remains closed"
                    )
                transaction["phase"] = "COMMITTED"
                owner.state.write(path, transaction)
                return {
                    "profile": identity,
                    "version": bundle.name,
                    "graph_preserved": True,
                    "state": "COMMITTED",
                }


def _approved_migration_after(owner, transaction, fixture):
    bundle = Path(transaction["bundle"])
    if bundle.parent != VERSIONS or bundle.name != transaction["version"]:
        raise ValueError("Pending migration bundle identity changed")
    selected = bundle_owner(bundle, owner.registry.ROOT if fixture else None)
    descriptor = deepcopy(transaction["before"]["descriptor"])
    descriptor["service_pins"] = selected.registry.provider.hashes()
    entry = transaction["after_entry"]
    expected_hash = hashlib.sha256(
        selected.state.scope.canonical(descriptor) + b"\n"
    ).hexdigest()
    expected_entry = {
        **transaction["before"]["entry"],
        "descriptor_sha256": expected_hash,
    }
    if entry != expected_entry:
        raise ValueError("Pending migration descriptor or profile identity changed")
    after = {
        "entry": entry,
        "descriptor": descriptor,
        "active": selected.candidate(entry, descriptor),
        "runtime_binding": {
            "schema": 2,
            "state": "active",
            "bundle": str(bundle),
            "version": bundle.name,
            "transaction": transaction["id"],
        },
    }
    if "after" in transaction and transaction["after"] != after:
        raise ValueError("Pending migration runtime inputs changed")
    return selected, after


def _transition_records(owner, directory, index, identity):
    return {
        "entry": index.get(identity),
        "descriptor": owner.state.read(directory / PROFILE_DESCRIPTOR),
        "active": owner.state.read(
            directory / ACTIVE_INDEX, max_bytes=32 * 1024 * 1024
        ),
        "runtime_binding": owner.state.read(directory / RUNTIME_BINDING),
    }


def _check_transition_records(current, before, after, *, completed_target=None):
    for name, value in current.items():
        if completed_target is not None:
            if value != completed_target[name]:
                raise ValueError("Completed migration records changed")
            continue
        if value == before.get(name) or value == after[name]:
            continue
        if (
            name == "runtime_binding"
            and value is None
            and before.get(name, {}).get("state") == "legacy"
        ):
            continue
        raise ValueError("Pending migration contains an unapproved record")


def _complete_transition(owner, directory, identity, transaction, selected, after):
    phase = transaction["phase"]
    rollback_direction = phase in {"ROLLING_BACK", "ROLLED_BACK"}
    before = transaction["before"]
    target = before if rollback_direction else after
    bound = (
        transaction.get("rollback_snapshot", before) if rollback_direction else before
    )
    if not isinstance(bound, dict) or not {"graph", "coordination"}.issubset(bound):
        raise ValueError("Interrupted transition has no qualified snapshot")
    if rollback_direction and not _predecessor_runtime_matches(before):
        raise ValueError("Rollback predecessor runtime is not qualified")
    index_path = owner.registry.ROOT / PROFILE_INDEX
    index = owner.state.read(index_path)
    current = _transition_records(owner, directory, index, identity)
    completed = phase in {"COMMITTED", "ROLLED_BACK"}
    _check_transition_records(
        current, before, after, completed_target=target if completed else None
    )
    if current["entry"] is None or Path(current["entry"]["state"]) != directory:
        raise ValueError("Pending migration profile scope changed")
    if dormant(selected, current["entry"], current["descriptor"]) != bound["graph"]:
        raise ValueError("Graph changed during interrupted migration")
    if owner.state.read(directory / RECOVERY_RECORD) != bound["coordination"]:
        raise ValueError("Coordination changed during interrupted migration")
    if completed:
        return {
            "profile": identity,
            "state": phase,
            "graph_preserved": True,
            "already_completed": True,
        }
    owner.state.write(directory / PROFILE_DESCRIPTOR, target["descriptor"])
    owner.state.write(directory / ACTIVE_INDEX, target["active"])
    index[identity] = target["entry"]
    owner.state.write(index_path, index)
    owner.state.write(directory / RUNTIME_BINDING, target["runtime_binding"])
    if dormant(selected, target["entry"], target["descriptor"]) != bound["graph"]:
        raise ValueError("Graph changed while completing interrupted migration")
    if owner.state.read(directory / RECOVERY_RECORD) != bound["coordination"]:
        raise ValueError("Coordination changed while completing interrupted migration")
    transaction["phase"] = "ROLLED_BACK" if rollback_direction else "COMMITTED"
    transaction["completed_by_recovery"] = True
    owner.state.write(directory / MIGRATION_RECORD, transaction)
    return {
        "profile": identity,
        "state": transaction["phase"],
        "graph_preserved": True,
        "recovered": True,
    }


def _validate_recovery_scope(owner, identity, descriptor):
    profile = descriptor["profile"]
    if profile.get("id") != identity:
        raise ValueError("Recovery profile identity changed")
    owner.state.scope.revalidate(profile)
    claims = owner.state.read(owner.registry.ROOT / "graphs.json") or {}
    if claims.get(owner.registry.claim(descriptor)) != identity:
        raise ValueError("Recovery graph claim changed")


@_bytecode_guard()
def recover_transition(owner, identity, transaction_id, *, fixture=False):
    """Complete only the exact, already approved profile-local transition."""
    if not identity or Path(identity).name != identity or identity in {".", ".."}:
        raise ValueError("Invalid recovery profile identity")
    directory = owner.registry.ROOT / identity
    physical(directory)
    path = directory / MIGRATION_RECORD
    expected = owner.state.read(path, max_bytes=32 * 1024 * 1024)
    if (
        not expected
        or expected.get("id") != transaction_id
        or expected.get("phase")
        not in {"PREPARING", "ROLLING_BACK", "COMMITTED", "ROLLED_BACK"}
    ):
        raise ValueError("Explicit current migration transaction required")
    selected, after = _approved_migration_after(owner, expected, fixture)
    if not fixture:
        _validate_recovery_scope(selected, identity, expected["before"]["descriptor"])
    graph = Path(expected["before"]["descriptor"]["profile"]["graph"])
    with owner.core.LifetimeLock(owner.registry.ROOT / REGISTRY_LOCK):
        with owner.core.LifetimeLock(directory / PROFILE_LOCK):
            with owner.core.LifetimeLock(graph.with_name(GRAPH_OWNER_LOCK)):
                transaction = owner.state.read(path, max_bytes=32 * 1024 * 1024)
                if transaction != expected:
                    raise ValueError("Pending migration changed during recovery")
                if not fixture:
                    _validate_recovery_scope(
                        selected, identity, expected["before"]["descriptor"]
                    )
                return _complete_transition(
                    owner, directory, identity, transaction, selected, after
                )


def _runtime_hashes_match(hashes):
    try:
        return all(sha(Path(path)) == expected for path, expected in hashes.items())
    except OSError:
        return False


def _predecessor_runtime_matches(before):
    binding = before.get("runtime_binding", {"schema": 2, "state": "legacy"})
    if binding.get("state") == "active":
        try:
            bundle = Path(binding["bundle"])
            if bundle.parent != VERSIONS or bundle.name != binding["version"]:
                return False
            verify(bundle)
        except (OSError, ValueError, KeyError):
            return False
    active = before.get("active")
    return (
        isinstance(active, dict)
        and isinstance(active.get("hashes"), dict)
        and _runtime_hashes_match(active["hashes"])
    )


@_bytecode_guard()
def rollback(owner, identity):
    entry, value = owner.specification(identity)
    directory = Path(entry["state"])
    expected = owner.state.read(
        directory / MIGRATION_RECORD, max_bytes=32 * 1024 * 1024
    )
    with owner.core.LifetimeLock(owner.registry.ROOT / REGISTRY_LOCK):
        with owner.core.LifetimeLock(directory / PROFILE_LOCK):
            with owner.core.LifetimeLock(
                Path(value["profile"]["graph"]).with_name(GRAPH_OWNER_LOCK)
            ):
                path = directory / MIGRATION_RECORD
                transaction = owner.state.read(path, max_bytes=32 * 1024 * 1024)
                if transaction is None or transaction["phase"] != "COMMITTED":
                    raise ValueError("Migration is not committed; preserve journal")
                index_path = owner.registry.ROOT / PROFILE_INDEX
                index = owner.state.read(index_path)
                if (
                    expected is None
                    or transaction["id"] != expected["id"]
                    or index.get(identity) != entry
                    or entry != transaction["after_entry"]
                ):
                    raise ValueError(
                        "Concurrent migration or profile change; rollback refused"
                    )
                stamp = dormant(owner, entry, value)
                current = owner.state.read(directory / RECOVERY_RECORD)
                if current != transaction["before"]["coordination"]:
                    owner.state.write(
                        directory / RUNTIME_BINDING,
                        {
                            "schema": 2,
                            "state": "disabled",
                            "bundle": transaction["bundle"],
                            "version": transaction["version"],
                        },
                    )
                    return {
                        "state": "BLOCKED_INCOMPATIBLE_COORDINATION",
                        "graph_preserved": True,
                    }
                before = transaction["before"]
                if not _predecessor_runtime_matches(before):
                    owner.state.write(
                        directory / RUNTIME_BINDING,
                        {
                            "schema": 2,
                            "state": "disabled",
                            "bundle": transaction["bundle"],
                            "version": transaction["version"],
                        },
                    )
                    return {
                        "state": "BLOCKED_LEGACY_RUNTIME_DRIFT",
                        "graph_preserved": True,
                    }
                transaction["rollback_snapshot"] = {
                    "graph": stamp,
                    "coordination": current,
                }
                transaction["phase"] = "ROLLING_BACK"
                owner.state.write(path, transaction)
                owner.state.write(directory / PROFILE_DESCRIPTOR, before["descriptor"])
                owner.state.write(directory / ACTIVE_INDEX, before["active"])
                index[identity] = before["entry"]
                owner.state.write(index_path, index)
                owner.state.write(
                    directory / RUNTIME_BINDING,
                    before.get("runtime_binding", {"schema": 2, "state": "legacy"}),
                )
                if dormant(owner, before["entry"], before["descriptor"]) != stamp:
                    raise ValueError(
                        "Graph changed during rollback; route remains closed"
                    )
                if owner.state.read(directory / RECOVERY_RECORD) != current:
                    raise ValueError("Coordination changed during rollback")
                transaction["phase"] = "ROLLED_BACK"
                owner.state.write(path, transaction)
                return {
                    "profile": identity,
                    "state": "ROLLED_BACK",
                    "graph_preserved": True,
                }


def _optional_bytes(path):
    return path.read_bytes() if path.exists() else None


def _binding_matches_transaction(binding, transaction):
    phase = transaction["phase"]
    if phase == "COMMITTED":
        return (
            all(binding.get(key) == transaction[key] for key in ("bundle", "version"))
            and binding.get("transaction", transaction["id"]) == transaction["id"]
        )
    if phase == "ROLLED_BACK":
        return binding == transaction["before"].get(
            "runtime_binding", {"schema": 2, "state": "legacy"}
        )
    return False


def _selected_binding(bundle_binding, transaction):
    if bundle_binding.get("schema") != 2 or bundle_binding.get("state") not in {
        "active",
        "legacy",
    }:
        raise PermissionError("Profile runtime binding is disabled or unsupported")
    if bundle_binding["state"] == "active" and transaction is None:
        raise PermissionError("Active runtime has no committed migration transaction")
    if transaction is not None and not _binding_matches_transaction(
        bundle_binding, transaction
    ):
        raise PermissionError(
            "Runtime binding does not match the committed transaction"
        )
    if bundle_binding["state"] == "legacy":
        return None
    bundle = Path(bundle_binding["bundle"])
    if bundle.parent != VERSIONS or bundle.name != bundle_binding["version"]:
        raise PermissionError("Profile runtime version mismatch")
    verify(bundle)
    return bundle


def select_bundle(registry_root, identity):
    directory = registry_root / identity
    physical(directory)
    migration, binding_path = directory / MIGRATION_RECORD, directory / RUNTIME_BINDING
    observed = (_optional_bytes(migration), _optional_bytes(binding_path))
    transaction = json.loads(observed[0]) if observed[0] is not None else None
    if transaction is not None and transaction["phase"] not in {
        "COMMITTED",
        "ROLLED_BACK",
    }:
        raise PermissionError("Profile migration has not committed")
    binding = (
        json.loads(observed[1])
        if observed[1] is not None
        else {"schema": 2, "state": "legacy"}
    )
    selected = _selected_binding(binding, transaction)
    # Both records must still represent the same publication after closure verification.
    # A read never creates a control-plane lock or starts a migration.
    if observed != (_optional_bytes(migration), _optional_bytes(binding_path)):
        raise PermissionError("Profile migration changed during runtime selection")
    return selected


def _audit_block_reasons(process_states, work, branch_matches, account_matches):
    reasons = []
    if "UNKNOWN" in process_states.values():
        reasons.append("BLOCK_PROCESS_IDENTITY_UNKNOWN")
    if "ALIVE" in process_states.values():
        reasons.append("BLOCK_SURVIVING_PROCESS")
    if work.get("schema") != 2:
        reasons.append("BLOCK_INSUFFICIENT_LEGACY_EVIDENCE")
    if not branch_matches or not account_matches:
        reasons.append("BLOCK_CONTEXT_MISMATCH")
    if not reasons:
        reasons.append("REQUIRES_VERSIONED_PLAN_IN_MATCHING_SCOPE")
    return reasons


@_bytecode_guard()
def audit_profile(owner, identity):
    """Inspect historical state without pretending its branch is checked out."""
    if len(identity) != 64 or any(ch not in "0123456789abcdef" for ch in identity):
        raise ValueError("Invalid historical profile identity")
    index = owner.state.read(owner.registry.ROOT / PROFILE_INDEX) or {}
    entry = index[identity]
    directory = Path(entry["state"])
    if directory != owner.registry.ROOT / identity:
        raise ValueError("Historical profile registry mismatch")
    descriptor = owner.state.read(directory / PROFILE_DESCRIPTOR)
    if sha(directory / PROFILE_DESCRIPTOR) != entry["descriptor_sha256"]:
        raise ValueError("Historical descriptor drift")
    if (owner.state.read(owner.registry.ROOT / "graphs.json") or {}).get(
        owner.registry.claim(descriptor)
    ) != identity:
        raise ValueError("Historical graph claim absent")
    stamp = owner.state.graph_stamp(descriptor)
    work = owner.state.read(directory / "work.json") or {}
    status = owner.state.read(directory / "status.json")
    launch = owner.state.read(directory / "owner-launch.json")
    scope = descriptor["profile"]["scope"]
    account_matches = scope["account"] == owner.state.scope.account_sid()
    context = (
        owner.state.scope.git_context(Path(scope["root"]))
        if not scope["directory"]
        else None
    )
    branch_matches = bool(scope["directory"] or context["branch"] == scope["branch"])
    reconciler = load(
        "audit_reconciliation", Path(__file__).with_name(RECONCILIATION_SOURCE)
    )
    process_states = reconciler.process_identities(
        owner, {"status": status, "owner-launch": launch}
    )
    process_states["launch_owner"] = process_states.pop("launch")
    reasons = _audit_block_reasons(
        process_states, work, branch_matches, account_matches
    )
    return {
        "profile": identity,
        "historical_branch": scope["branch"],
        "branch_matches": branch_matches,
        "account_matches": account_matches,
        "provider_pins_match": descriptor["service_pins"]
        == owner.registry.provider.hashes(),
        "graph_verified": True,
        "graph_sequence": stamp["sequence"],
        "work_phase": work.get("phase"),
        "accepted_count_present": "accepted_count" in work,
        "process_states": process_states,
        "verdict": "BLOCKED",
        "reason": reasons[0],
        "reasons": reasons,
        "operational_scope": "MATCH"
        if branch_matches and account_matches
        else "MISMATCH",
        "files_changed": False,
        "request_replayed": False,
    }


def _profile_action(parser, args, owner, fixture):
    if args.action == "audit-profile":
        return audit_profile(owner, args.profile)
    if args.action == "recover-transition":
        if not args.transaction:
            parser.error("recover-transition requires --transaction")
        return recover_transition(
            owner, args.profile, args.transaction, fixture=fixture
        )
    if args.action == "build":
        entry, value = owner.specification(args.profile, fixture)
        bundle = build(owner, entry, value)
        return {"bundle": str(bundle), "version": bundle.name}
    if args.action == "migrate":
        if not args.bundle:
            parser.error("migrate requires --bundle")
        recovery_bundle = _select_disabled_migration_bundle(
            owner, args.profile, args.from_version
        )
        prior_bundle = recovery_bundle or select_bundle(
            owner.registry.ROOT, args.profile
        )
        if prior_bundle is not None:
            owner = bundle_owner(prior_bundle, args.fixture_registry)
        return migrate(
            owner,
            args.profile,
            args.bundle,
            fixture=fixture,
            from_version=args.from_version,
            recover_disabled=recovery_bundle is not None,
        )
    bundle = select_bundle(owner.registry.ROOT, args.profile)
    if bundle is None:
        parser.error("profile has no selected v2 runtime")
    selected = bundle_owner(bundle, args.fixture_registry)
    if args.action == "rollback":
        return rollback(selected, args.profile)
    return _reconcile_profile(parser, args, selected, fixture)


def _reconcile_profile(parser, args, selected, fixture):
    entry, value = selected.specification(args.profile, fixture)
    if args.action == "reconcile-plan":
        # Full plan is private operator output, never a public acceptance report.
        return selected.reconciler.plan(selected.runtime_owner(), entry, value)
    if args.action == "reconcile-incident":
        current = load(
            "incident_reconciliation",
            Path(__file__).with_name(RECONCILIATION_SOURCE),
        )
        incident = current.identify_interrupted_launch(
            selected.runtime_owner(), entry, value
        )
        return {
            "incident": incident["id"],
            "state": "BLOCKED",
            "next": "reconcile-plan",
        }
    plan_path = args.plan
    if plan_path is None:
        return parser.error("reconcile-apply requires --plan")
    plans = Path(entry["state"]) / "reconcile-plans"
    if ".." in plan_path.parts or not plan_path.is_relative_to(plans):
        return parser.error(
            "apply plan must be in this profile's private reconcile-plans directory"
        )
    selected.state.scope.physical(plans)
    owned_plan = next((path for path in plans.iterdir() if path == plan_path), None)
    if owned_plan is None or owned_plan.suffix != ".json":
        return parser.error("apply plan must be an existing private JSON plan")
    physical(owned_plan)
    grant = selected.reconciler.apply(
        selected.runtime_owner(),
        entry,
        value,
        selected.state.read(owned_plan, max_bytes=32 * 1024 * 1024),
    )
    return {
        "resolution": grant["id"],
        "generation": grant["new_generation"],
        "state": grant["phase"],
    }


@_bytecode_guard()
def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "build",
            "verify",
            "migrate",
            "rollback",
            "recover-transition",
            "reconcile-incident",
            "reconcile-plan",
            "reconcile-apply",
            "audit-profile",
        ),
    )
    parser.add_argument("--profile")
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument(
        "--transaction",
        help="Exact preserved migration transaction ID for explicit completion",
    )
    parser.add_argument("--fixture-registry", type=Path)
    parser.add_argument(
        "--from-version",
        help="Exact active or retained disabled version, or legacy after a compatible rollback",
    )
    args = parser.parse_args(argv)
    if args.action == "verify":
        manifest = verify(args.bundle)
        result = {
            "verified": True,
            "files": len(manifest["files"]),
            "version": args.bundle.name,
        }
    else:
        if not args.profile:
            parser.error("--profile is required")
        sys.path.append(str(VENV / SITE_PACKAGES))
        owner = load("legacy_memory_owner", HOST / "project-memory-owner.py")
        fixture = owner.fixture_registry(
            str(args.fixture_registry) if args.fixture_registry else None
        )
        result = _profile_action(parser, args, owner, fixture)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
