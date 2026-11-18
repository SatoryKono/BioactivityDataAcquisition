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
import uuid
from copy import deepcopy
from pathlib import Path

HOST = Path("D:/pc-agent/tools/shared-mcp")
VERSIONS = Path("D:/pc-agent/tools/memory-runtime-versions")
BASE_PYTHON = Path("C:/Users/Fedor/AppData/Local/Programs/Python/Python313")
VENV = Path("D:/github/BioactivityDataAcquisition/.venv-win")
SDK_ROOT = Path("D:/pc-agent/tools/mcp/markdownify/node_modules")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def physical(path):
    if not path.is_absolute() or ".." in path.parts or path.resolve(strict=True) != path:
        raise ValueError("Immutable runtime path is not physical")
    for item in (path, *path.parents):
        if item.is_symlink() or getattr(item, "is_junction", lambda: False)():
            raise ValueError("Immutable runtime traverses a reparse point")
    return path


def verify(bundle):
    bundle = physical(bundle)
    raw = (bundle / "bundle.json").read_bytes()
    manifest = json.loads(raw)
    if (manifest.get("schema") != 2 or bundle.name != hashlib.sha256(raw).hexdigest()
            or not isinstance(manifest.get("files"), dict)):
        raise ValueError("Immutable bundle identity mismatch")
    actual = set()
    for current, directories, files in os.walk(bundle, followlinks=False):
        for name in [*directories, *files]:
            path = Path(current) / name
            if getattr(path.lstat(), "st_file_attributes", 0) & 0x400:
                raise ValueError("Immutable bundle contains a reparse point")
        actual.update((Path(current) / name).relative_to(bundle).as_posix()
                      for name in files if Path(current) / name != bundle / "bundle.json")
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
    text = replace_once(text, "def recovery(entry, value, *, self_owner=False):", "def legacy_recovery(entry, value, *, self_owner=False):")
    anchor = "def environment():"
    additions = '''def runtime_owner():
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


'''
    text = replace_once(text, anchor, additions + anchor)
    text = text.replace('(directory / "blocked.json").exists()', 'reconciler.blocked(runtime_owner(), entry)')
    text = text.replace('("FRESH_START", "SAFE_IDLE_RESTART")', '("FRESH_START", "SAFE_IDLE_RESTART", "SAFE_RECONCILED_START")')
    text = replace_once(text, 'generation = uuid.uuid4().hex', 'generation = reconciler.launch_generation(runtime_owner(), entry, value)')
    text = replace_once(text, 'state.write(directory / "blocked.json", {"decision": decision})',
                        'reconciler.record_block(runtime_owner(), entry, decision)')
    text = replace_once(text, 'if info.get("ready"):\n                            deadline = None',
                        'if info.get("ready"):\n                            reconciler.observe(runtime_owner(), entry, value, generation)\n                            deadline = None')
    text = replace_once(text, 'if stopped:\n                return 0',
                        'if stopped:\n                reconciler.observe(runtime_owner(), entry, value, generation, idle=True)\n                return 0')
    text = replace_once(text, 'state.write(\n            directory / "blocked.json", {"decision": "RESTART_BUDGET_EXHAUSTED"}\n        )',
                        'reconciler.record_block(runtime_owner(), entry, "RESTART_BUDGET_EXHAUSTED")')
    text = replace_once(text, '"project-memory-owner.py",',
                        '"project-memory-owner.py",\n        "project-memory-reconciliation.py",\n        "project-memory-scoped-client.py",')
    return text


def adapt_gateway(text):
    text = replace_once(text, "function journal(phase, mutating = false) {",
                        "let acceptedCount = 0;\nlet requestId = null;\nfunction journal(phase, mutating = false) {\n    if (phase === 'busy') {acceptedCount++; requestId = randomUUID();}")
    return replace_once(text, '{generation: boot.generation, phase, mutating, graph: graphStamp()}',
                        '{schema: 2, profile: boot.id, generation: boot.generation, phase, mutating, accepted_count: acceptedCount, request_id: requestId, graph: graphStamp()}')


VERIFY_BOOTSTRAP = '''# Verify the complete closure before importing site dependencies or serving.
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
'''


def build(owner, entry, value):
    """Copy the reviewed legacy closure and deterministically adapt a new version."""
    hashes = owner.candidate(entry, value)["hashes"]
    hashes[str(HOST / "project-memory-scoped-client.py")] = sha(HOST / "project-memory-scoped-client.py")
    hashes[str(HOST / "host-servers.json")] = sha(HOST / "host-servers.json")
    VERSIONS.mkdir(parents=True, exist_ok=True)
    physical(VERSIONS)
    staging = VERSIONS / ("building-" + uuid.uuid4().hex)
    staging.mkdir()
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
        if source.is_relative_to(HOST):
            relative = Path("tools/shared-mcp") / source.relative_to(HOST)
        elif source.is_relative_to(SDK_ROOT):
            relative = Path("tools/mcp/markdownify/node_modules") / source.relative_to(SDK_ROOT)
        elif source.is_relative_to(BASE_PYTHON):
            relative = Path("runtime/python") / source.relative_to(BASE_PYTHON)
        elif source.is_relative_to(VENV / "Lib/site-packages"):
            relative = Path("runtime/site-packages") / source.relative_to(VENV / "Lib/site-packages")
        elif source.is_relative_to(VENV):
            relative = Path("runtime/venv") / source.relative_to(VENV)
        elif source == owner.core.NODE:
            relative = Path("runtime/node.exe")
        else:
            raise ValueError("Unclassified runtime dependency")
        target = staging / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        if sha(target) != expected:
            raise ValueError("Runtime dependency changed while copying")
    service = staging / "tools/shared-mcp"
    source = Path(__file__).with_name("memory_reconciliation.py")
    shutil.copyfile(source, service / "project-memory-reconciliation.py")
    for file in service.glob("*"):
        if file.suffix not in {".py", ".mjs"}:
            continue
        text = file.read_text(encoding="utf-8").replace("\r\n", "\n")
        if file.name == "project-memory-owner.py":
            text = adapt_owner(text)
        if file.name == "project-memory-client.py":
            text = replace_once(text, "owner.ensure(args.profile, fixture)", "owner.connect(args.profile, fixture)")
        if file.name == "project-memory-gateway.mjs":
            text = adapt_gateway(text)
        if file.suffix == ".py":
            text = text.replace('"C:/Users/Fedor/AppData/Local/Programs/Python/Python313/python.exe"',
                                '(HERE.parents[1] / "runtime/python/python.exe")')
            text = text.replace('"D:/github/BioactivityDataAcquisition/.venv-win/Lib/site-packages"',
                                'str(HERE.parents[1] / "runtime/site-packages")')
        else:
            text = text.replace("'C:/Users/Fedor/AppData/Local/Programs/Python/Python313/python.exe'",
                                "path.resolve(here, '../../runtime/python/python.exe')")
        if file.name == "supervisor.py":
            text = replace_once(text, "ROOT = Path('D:/pc-agent')", "ROOT = Path(__file__).resolve().parents[2]")
            text = replace_once(text, "NODE = Path('C:/Program Files/nodejs/node.exe')", 'NODE = ROOT / "runtime/node.exe"')
            text = replace_once(text, "PYTHON = Path('C:/Users/Fedor/AppData/Local/Programs/Python/Python313/python.exe')", 'PYTHON = ROOT / "runtime/python/python.exe"')
        if file.name == "project-memory-bootstrap.py":
            text = replace_once(text, 'HERE = Path(__file__).resolve().parent\n', 'HERE = Path(__file__).resolve().parent\n' + VERIFY_BOOTSTRAP)
        if file.name == "project-memory-runtime.py":
            text = replace_once(text, 'pathlib.Path("D:/pc-agent/tools/mcp/markdownify/node_modules/@modelcontextprotocol/sdk")',
                                'pathlib.Path(__file__).resolve().parents[1] / "mcp/markdownify/node_modules/@modelcontextprotocol/sdk"')
            start = text.index("def python_hashes()")
            end = text.index('\n\nif __name__ == "__main__":', start)
            text = text[:start] + '''def python_hashes():
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
''' + text[end:]
        file.write_text(text, encoding="utf-8", newline="\n")
    manifest = {"schema": 2, "recipe": {"builder_sha256": sha(Path(__file__)), "legacy_input": hashes,
                                       "reconciliation_sha256": sha(source)},
                "files": {p.relative_to(staging).as_posix(): sha(p)
                                           for p in sorted(staging.rglob("*")) if p.is_file()}}
    raw = canonical(manifest)
    identity = hashlib.sha256(raw).hexdigest()
    target = VERSIONS / identity
    (staging / "bundle.json").write_bytes(raw)
    if target.exists():
        verify(target)
        # Keep the duplicate build as evidence instead of recursive cleanup.
        return target
    staging.rename(target)
    verify(target)
    return target


def bundle_owner(bundle, fixture_registry=None):
    verify(bundle)
    # Management imports use the current interpreter; service launch uses the copied one.
    owner = load("versioned_memory_owner", bundle / "tools/shared-mcp/project-memory-owner.py")
    if fixture_registry:
        owner.fixture_registry(str(fixture_registry))
    return owner


def dormant(owner, entry, value):
    record = owner.state.read(Path(entry["state"]) / "status.json")
    launch = owner.state.read(Path(entry["state"]) / "owner-launch.json")
    for source, roles in ((record, ("owner", "gateway", "backend")), (launch, ("owner",))):
        if any(owner.state.identity(source, role) not in {"DEAD", "ABSENT"} for role in roles):
            raise ValueError("Profile is not proven dormant")
    return owner.state.graph_stamp(value)


def migrate(owner, identity, bundle, *, fixture=False):
    new_owner = bundle_owner(bundle, owner.registry.ROOT if fixture else None)
    entry, value = owner.specification(identity, fixture)
    directory = Path(entry["state"])
    with owner.core.LifetimeLock(owner.registry.ROOT / "registry.lock"):
        with owner.core.LifetimeLock(directory / "transition.lock"):
            with owner.core.LifetimeLock(Path(value["profile"]["graph"]).with_name(".memory.service-owner.lock")):
                stamp = dormant(owner, entry, value)
                if (directory / "runtime-binding.json").exists():
                    raise ValueError("Existing runtime binding requires explicit migration review")
                index_path = owner.registry.ROOT / "profiles.json"
                index = owner.state.read(index_path)
                if index.get(identity) != entry:
                    raise ValueError("Concurrent profile registration change")
                before = {"entry": entry, "descriptor": value, "active": owner.state.read(directory / "active.json", max_bytes=32 * 1024 * 1024),
                          "graph": stamp, "coordination": owner.state.read(directory / "recovery-v2.json")}
                updated = deepcopy(value)
                updated["service_pins"] = new_owner.registry.provider.hashes()
                descriptor_raw = new_owner.state.scope.canonical(updated) + b"\n"
                new_entry = {**entry, "descriptor_sha256": hashlib.sha256(descriptor_raw).hexdigest()}
                active = new_owner.candidate(new_entry, updated)
                transaction = {"id": uuid.uuid4().hex, "phase": "PREPARING", "before": before,
                               "after_entry": new_entry, "bundle": str(bundle), "version": bundle.name}
                path = directory / "migration-v2.json"
                if path.exists():
                    raise ValueError("Prior migration journal retained; no automatic replacement")
                owner.state.write(path, transaction)
                owner.state.write(directory / "profile.json", updated)
                owner.state.write(directory / "active.json", active)
                index[identity] = new_entry
                owner.state.write(index_path, index)
                owner.state.write(directory / "runtime-binding.json", {"schema": 2, "state": "active", "bundle": str(bundle), "version": bundle.name})
                if dormant(new_owner, new_entry, updated) != stamp:
                    raise ValueError("Graph changed during migration; route remains closed")
                transaction["phase"] = "COMMITTED"
                owner.state.write(path, transaction)
                return {"profile": identity, "version": bundle.name, "graph_preserved": True, "state": "COMMITTED"}


def rollback(owner, identity):
    entry, value = owner.specification(identity)
    directory = Path(entry["state"])
    with owner.core.LifetimeLock(owner.registry.ROOT / "registry.lock"):
        with owner.core.LifetimeLock(directory / "transition.lock"):
            with owner.core.LifetimeLock(Path(value["profile"]["graph"]).with_name(".memory.service-owner.lock")):
                dormant(owner, entry, value)
                path = directory / "migration-v2.json"
                transaction = owner.state.read(path)
                if transaction is None or transaction["phase"] != "COMMITTED":
                    raise ValueError("Migration is not committed; preserve journal")
                current = owner.state.read(directory / "recovery-v2.json")
                if current != transaction["before"]["coordination"]:
                    owner.state.write(directory / "runtime-binding.json", {"schema": 2, "state": "disabled", "version": transaction["version"]})
                    return {"state": "BLOCKED_INCOMPATIBLE_COORDINATION", "graph_preserved": True}
                index_path = owner.registry.ROOT / "profiles.json"
                index = owner.state.read(index_path)
                if index.get(identity) != transaction["after_entry"]:
                    raise ValueError("Concurrent profile registration change")
                before = transaction["before"]
                if any(sha(Path(path)) != expected for path, expected in before["active"]["hashes"].items()):
                    owner.state.write(directory / "runtime-binding.json", {"schema": 2, "state": "disabled", "version": transaction["version"]})
                    return {"state": "BLOCKED_LEGACY_RUNTIME_DRIFT", "graph_preserved": True}
                transaction["phase"] = "ROLLING_BACK"
                owner.state.write(path, transaction)
                owner.state.write(directory / "profile.json", before["descriptor"])
                owner.state.write(directory / "active.json", before["active"])
                index[identity] = before["entry"]
                owner.state.write(index_path, index)
                owner.state.write(directory / "runtime-binding.json", {"schema": 2, "state": "legacy"})
                transaction["phase"] = "ROLLED_BACK"
                owner.state.write(path, transaction)
                return {"profile": identity, "state": "ROLLED_BACK", "graph_preserved": True}


def select_bundle(registry_root, identity):
    directory = registry_root / identity
    physical(directory)
    migration = directory / "migration-v2.json"
    if migration.exists() and json.loads(migration.read_bytes())["phase"] not in {"COMMITTED", "ROLLED_BACK"}:
        raise PermissionError("Profile migration has not committed")
    path = directory / "runtime-binding.json"
    if not path.exists():
        return None
    binding = json.loads(path.read_bytes())
    if binding.get("schema") != 2 or binding.get("state") not in {"active", "legacy"}:
        raise PermissionError("Profile runtime binding is disabled or unsupported")
    if binding["state"] == "legacy":
        return None
    bundle = Path(binding["bundle"])
    if bundle.parent != VERSIONS or bundle.name != binding["version"]:
        raise PermissionError("Profile runtime version mismatch")
    verify(bundle)
    return bundle


def audit_profile(owner, identity):
    """Inspect historical state without pretending its branch is checked out."""
    if len(identity) != 64 or any(ch not in "0123456789abcdef" for ch in identity):
        raise ValueError("Invalid historical profile identity")
    index = owner.state.read(owner.registry.ROOT / "profiles.json") or {}
    entry = index[identity]
    directory = Path(entry["state"])
    if directory != owner.registry.ROOT / identity:
        raise ValueError("Historical profile registry mismatch")
    descriptor = owner.state.read(directory / "profile.json")
    if sha(directory / "profile.json") != entry["descriptor_sha256"]:
        raise ValueError("Historical descriptor drift")
    if (owner.state.read(owner.registry.ROOT / "graphs.json") or {}).get(owner.registry.claim(descriptor)) != identity:
        raise ValueError("Historical graph claim absent")
    stamp = owner.state.graph_stamp(descriptor)
    work = owner.state.read(directory / "work.json") or {}
    status = owner.state.read(directory / "status.json")
    launch = owner.state.read(directory / "owner-launch.json")
    scope = descriptor["profile"]["scope"]
    account_matches = scope["account"] == owner.state.scope.account_sid()
    context = owner.state.scope.git_context(Path(scope["root"])) if not scope["directory"] else None
    branch_matches = bool(scope["directory"] or context["branch"] == scope["branch"])
    process_states = {role: owner.state.identity(status, role) for role in ("owner", "gateway", "backend")}
    process_states["launch_owner"] = owner.state.identity(launch, "owner")
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
    return {"profile": identity, "historical_branch": scope["branch"], "branch_matches": branch_matches,
            "account_matches": account_matches, "provider_pins_match": descriptor["service_pins"] == owner.registry.provider.hashes(),
            "graph_verified": True, "graph_sequence": stamp["sequence"],
            "work_phase": work.get("phase"), "accepted_count_present": "accepted_count" in work,
            "process_states": process_states, "verdict": "BLOCKED", "reason": reasons[0], "reasons": reasons,
            "operational_scope": "MATCH" if branch_matches and account_matches else "MISMATCH",
            "files_changed": False, "request_replayed": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "verify", "migrate", "rollback", "reconcile-plan", "reconcile-apply", "audit-profile"))
    parser.add_argument("--profile")
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--fixture-registry", type=Path)
    args = parser.parse_args(argv)
    if args.action == "verify":
        manifest = verify(args.bundle)
        print(json.dumps({"verified": True, "files": len(manifest["files"]), "version": args.bundle.name}))
    else:
        if not args.profile:
            parser.error("--profile is required")
        sys.path.append(str(VENV / "Lib/site-packages"))
        owner = load("legacy_memory_owner", HOST / "project-memory-owner.py")
        fixture = owner.fixture_registry(str(args.fixture_registry) if args.fixture_registry else None)
        if args.action == "audit-profile":
            print(json.dumps(audit_profile(owner, args.profile)))
            return
        if args.action == "build":
            entry, value = owner.specification(args.profile, fixture)
            bundle = build(owner, entry, value)
            print(json.dumps({"bundle": str(bundle), "version": bundle.name}))
            return
        if args.action == "migrate":
            if not args.bundle:
                parser.error("migrate requires --bundle")
            print(json.dumps(migrate(owner, args.profile, args.bundle, fixture=fixture)))
            return
        bundle = select_bundle(owner.registry.ROOT, args.profile)
        if bundle is None:
            parser.error("profile has no selected v2 runtime")
        selected = bundle_owner(bundle, args.fixture_registry)
        if args.action == "rollback":
            print(json.dumps(rollback(selected, args.profile)))
        else:
            entry, value = selected.specification(args.profile, fixture)
            if args.action == "reconcile-plan":
                # Full plan is private operator output, never a public acceptance report.
                print(json.dumps(selected.reconciler.plan(selected.runtime_owner(), entry, value)))
            else:
                if args.plan is None:
                    parser.error("reconcile-apply requires --plan")
                physical(args.plan)
                if not args.plan.is_relative_to(Path(entry["state"]) / "reconcile-plans"):
                    parser.error("apply plan must be in this profile's private reconcile-plans directory")
                grant = selected.reconciler.apply(selected.runtime_owner(), entry, value, json.loads(args.plan.read_bytes()))
                print(json.dumps({"resolution": grant["id"], "generation": grant["new_generation"], "state": grant["phase"]}))


if __name__ == "__main__":
    main()
