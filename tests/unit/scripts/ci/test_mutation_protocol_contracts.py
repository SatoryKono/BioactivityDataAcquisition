"""Real mutmut instrumentation controls; no product/runtime protocol changes."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest
from mutmut.mutation.file_mutation import mutate_file_contents
from mutmut.mutation.trampoline import set_mutant_under_test
from mutmut.configuration import reset_config

from scripts.engineering.ci import mutation_protocol_contracts as harness

pytestmark = pytest.mark.unit

SOURCE = """from typing import Protocol, runtime_checkable
@runtime_checkable
class P(Protocol):
    def accept(self, value: int = 0) -> bool:
        return value > 0
"""


class Good:
    def accept(self, value: int = 0) -> bool:
        return value > 0


class Missing:
    pass


@pytest.fixture(autouse=True)
def isolated_mutmut_configuration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Exercise the locked instrumenter without inheriting repository settings."""
    (tmp_path / "pyproject.toml").write_text(
        '[tool.mutmut]\nsource_paths = ["src"]\n', encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    reset_config()
    yield
    reset_config()


@pytest.fixture
def instrumented(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MUTANT_UNDER_TEST", "")
    set_mutant_under_test(None)
    original = ModuleType("mutation_contract_fixture")
    exec(SOURCE, original.__dict__)
    pristine = original.P
    transformed = mutate_file_contents("fixture.py", SOURCE)
    module = ModuleType("mutation_contract_fixture")
    monkeypatch.setitem(sys.modules, module.__name__, module)
    exec(transformed.code, module.__dict__)
    contract = harness.Contract(
        module.__name__,
        "P",
        "src/fixture.py",
        hashlib.sha256(SOURCE.encode()).hexdigest(),
        frozenset(pristine.__protocol_attrs__),
        None
        if not hasattr(pristine, "__non_callable_proto_members__")
        else frozenset(pristine.__non_callable_proto_members__),
    )
    yield module, contract, transformed.mutant_names
    set_mutant_under_test(None)


def test_real_instrumentation_restores_membership_without_removing_mutants(
    instrumented,
):
    module, contract, mutants = instrumented
    protocol = module.P
    before = {name: value for name, value in vars(protocol).items() if callable(value)}
    dictionaries = {
        name: dict(value)
        for name, value in vars(module).items()
        if name.startswith("mutants_")
    }
    assert mutants and not isinstance(Good(), protocol)
    harness.normalize_protocol(protocol, contract)
    assert isinstance(Good(), protocol)
    assert not isinstance(Missing(), protocol)
    assert protocol.__protocol_attrs__ == set(contract.members)
    assert before == {
        name: value for name, value in vars(protocol).items() if callable(value)
    }
    assert dictionaries == {
        name: dict(value)
        for name, value in vars(module).items()
        if name.startswith("mutants_")
    }


@pytest.mark.parametrize("invalid_id", ["1٢", "1２", "1²", "01"])
def test_protocol_helper_ids_require_canonical_ascii_digits(instrumented, invalid_id):
    module, contract, _ = instrumented
    valid = [name for name in vars(module.P) if harness.HELPER.fullmatch(name)]
    assert valid
    for name in valid:
        harness._verify_helper(module.P, contract, name)
    with pytest.raises(ValueError, match="Unexpected structural Protocol member"):
        harness._verify_helper(module.P, contract, "xǁPǁaccept__mutmut_" + invalid_id)


def test_active_body_mutants_remain_observable(instrumented):
    module, contract, mutants = instrumented
    harness.normalize_protocol(module.P, contract)
    expected = [False, False, True]
    differences = []
    for mutant in mutants:
        set_mutant_under_test(module.__name__ + "." + mutant)
        actual = [module.P.accept(None, value) for value in (-1, 0, 1)]
        if actual != expected:
            differences.append(mutant)
    assert len(differences) >= 2
    assert not isinstance(Missing(), module.P)


@pytest.mark.parametrize(
    "defect", ["missing_real", "unknown_extra", "unbound_helper", "non_callable"]
)
def test_protocol_metadata_correction_fails_closed(instrumented, defect: str):
    module, contract, _ = instrumented
    protocol = module.P
    if defect == "missing_real":
        protocol.__protocol_attrs__ -= {"accept"}
    elif defect == "unknown_extra":
        protocol.__protocol_attrs__.add("unexpected")
    elif defect == "unbound_helper":
        protocol.__protocol_attrs__.add("xǁPǁaccept__mutmut_9999")
        protocol.xǁPǁaccept__mutmut_9999 = lambda self: None
    else:
        protocol.__non_callable_proto_members__ = {"accept"}
    observed = set(protocol.__protocol_attrs__)
    with pytest.raises(ValueError):
        harness.normalize_protocol(protocol, contract)
    assert protocol.__protocol_attrs__ == observed


@pytest.fixture
def sandbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "repository"
    source = root / "src" / "mutation_manifest_fixture.py"
    source.parent.mkdir(parents=True)
    source.write_text(SOURCE, encoding="utf-8", newline="\n")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(
        ["git", "-C", str(root), "config", "core.autocrlf", "false"], check=True
    )
    subprocess.run(["git", "-C", str(root), "add", "src"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    monkeypatch.delitem(sys.modules, "mutation_manifest_fixture", raising=False)
    output = root / "reports" / "protocols.json"
    harness.capture(root, Path("src/mutation_manifest_fixture.py"), output)
    target = root / "mutants" / "src" / source.name
    target.parent.mkdir(parents=True)
    target.write_text(mutate_file_contents(source.name, SOURCE).code, encoding="utf-8")
    monkeypatch.delitem(sys.modules, "mutation_manifest_fixture", raising=False)
    monkeypatch.syspath_prepend(str(target.parent))
    monkeypatch.setenv(harness.MANIFEST_ENV, str(output))
    monkeypatch.setenv(harness.ROOT_ENV, str(root))
    monkeypatch.chdir(root / "mutants")
    monkeypatch.setenv("MUTANT_UNDER_TEST", "")
    set_mutant_under_test(None)
    yield root, output, source
    set_mutant_under_test(None)
    monkeypatch.delitem(sys.modules, "mutation_manifest_fixture", raising=False)


def test_native_capture_and_sandbox_plugin_preserve_contract(sandbox):
    root, output, source = sandbox
    data = json.loads(output.read_text())
    assert (
        data["source_commit"]
        == subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
        ).strip()
    )
    assert (
        data["contracts"][0]["sha256"]
        == hashlib.sha256(source.read_bytes()).hexdigest()
    )
    harness.pytest_configure(None)
    harness.pytest_configure(None)
    protocol = sys.modules["mutation_manifest_fixture"].P
    assert isinstance(Good(), protocol)
    assert not isinstance(Missing(), protocol)


@pytest.mark.parametrize(
    "defect",
    [
        "missing_identity",
        "duplicate_identity",
        "source_digest",
        "source_and_digest",
        "wrong_root",
        "missing_manifest",
    ],
)
def test_sandbox_plugin_rejects_inconsistent_provenance(
    sandbox, defect: str, monkeypatch: pytest.MonkeyPatch
):
    root, output, source = sandbox
    data = json.loads(output.read_text())
    if defect == "missing_identity":
        data["contracts"] = []
    elif defect == "duplicate_identity":
        data["contracts"].append(data["contracts"][0])
    elif defect == "source_digest":
        source.write_text(SOURCE + "\n# drift\n", encoding="utf-8")
    elif defect == "source_and_digest":
        harness.pytest_configure(None)
        source.write_bytes(source.read_bytes() + b"\n# forged digest\n")
        data["contracts"][0]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    elif defect == "wrong_root":
        monkeypatch.chdir(root)
    else:
        monkeypatch.delenv(harness.MANIFEST_ENV)
    output.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        harness.pytest_configure(None)


def test_capture_rejects_dirty_pristine_source(sandbox):
    root, _, source = sandbox
    source.write_text(SOURCE + "\n# uncommitted\n", encoding="utf-8")
    with pytest.raises(ValueError, match="differs from the checked-out commit"):
        harness.capture(
            root,
            Path("src/mutation_manifest_fixture.py"),
            root / "reports" / "rejected.json",
        )


def test_cached_commit_blob_still_rejects_working_drift_and_tracks_new_commit(sandbox):
    root, _, source = sandbox
    commit = harness._git(root, "HEAD")
    original = harness._committed_source(root, source, commit)
    hits = harness._committed_blob.cache_info().hits
    assert harness._committed_source(root, source, commit) == original
    assert harness._committed_blob.cache_info().hits == hits + 1
    metadata = source.stat()
    source.write_bytes(original.replace(b"value > 0", b"value < 0"))
    os.utime(source, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
    assert source.stat().st_size == len(original)
    with pytest.raises(ValueError, match="differs from the checked-out commit"):
        harness._committed_source(root, source, commit)
    source.write_bytes(original + b"\n# new committed revision\n")
    with pytest.raises(ValueError, match="differs from the checked-out commit"):
        harness._committed_source(root, source, commit)
    subprocess.run(["git", "-C", str(root), "add", "src"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "next",
        ],
        check=True,
    )
    next_commit = harness._git(root, "HEAD")
    assert next_commit != commit
    assert harness._committed_source(root, source, next_commit) == source.read_bytes()
    with pytest.raises(ValueError, match="differs from the checked-out commit"):
        harness._committed_source(root, source, commit)


def test_runtime_name_cache_is_content_bound_and_census_reads_current_files(sandbox):
    root, _, source = sandbox
    raw = source.read_bytes()
    assert harness._runtime_names(raw) == ("P",)
    hits = harness._runtime_names.cache_info().hits
    assert harness._runtime_names(raw) == ("P",)
    assert harness._runtime_names.cache_info().hits == hits + 1
    changed = raw.replace(b"class P(", b"class Renamed(")
    source.write_bytes(changed)
    assert harness._source_census(root, Path("src")) == [
        ["mutation_manifest_fixture", "Renamed"]
    ]
    extra = source.with_name("additional.py")
    extra.write_bytes(raw)
    assert harness._source_census(root, Path("src")) == [
        ["additional", "P"],
        ["mutation_manifest_fixture", "Renamed"],
    ]
    extra.unlink()
    assert harness._source_census(root, Path("src")) == [
        ["mutation_manifest_fixture", "Renamed"]
    ]


@pytest.mark.parametrize(
    "defect, expected_exit", [("none", 0), ("missing_method", 1), ("stale_source", 3)]
)
def test_real_pytest_plugin_path_fails_closed(sandbox, defect: str, expected_exit: int):
    """Use a fresh pytest process, not a direct invocation of the hook."""
    root, output, source = sandbox
    test = root / "mutants" / "test_contract_fixture.py"
    method = (
        "def accept(self, value=0): return value > 0"
        if defect != "missing_method"
        else "pass"
    )
    test.write_text(
        "from mutation_manifest_fixture import P\nclass Adapter:\n    "
        + method
        + "\ndef test_contract():\n    assert isinstance(Adapter(), P)\n",
        encoding="utf-8",
    )
    if defect == "stale_source":
        source.write_bytes(source.read_bytes() + b"\n# stale\n")
    env = dict(os.environ)
    # Retain the current locked instrumenter path and the plugin's repository.
    env["PYTHONPATH"] = os.pathsep.join([str(root / "mutants" / "src"), *sys.path])
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(test),
            "-q",
            "-p",
            "scripts.engineering.ci.mutation_protocol_contracts",
        ],
        cwd=root / "mutants",
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == expected_exit, result.stdout + result.stderr
    if defect == "none":
        assert "1 passed" in result.stdout
    elif defect == "missing_method":
        assert "AssertionError" in result.stdout
    else:
        assert (
            "Pristine Protocol source differs from the checked-out commit"
            in result.stderr
        )


def test_inherited_protocol_preserves_data_members_and_worker_idempotence(monkeypatch):
    source = (
        SOURCE + "\n@runtime_checkable\nclass Child(P, Protocol):\n    label: str\n"
    )
    pristine = ModuleType("inherited_mutation_fixture")
    exec(source, pristine.__dict__)
    mutated = ModuleType(pristine.__name__)
    monkeypatch.setitem(sys.modules, mutated.__name__, mutated)
    exec(mutate_file_contents("inherited.py", source).code, mutated.__dict__)
    child = pristine.Child
    contract = harness.Contract(
        mutated.__name__,
        "Child",
        "src/inherited.py",
        "fixture",
        frozenset(child.__protocol_attrs__),
        frozenset(child.__non_callable_proto_members__),
    )

    class Complete(Good):
        label = "synthetic"

    class MissingData(Good):
        pass

    assert not isinstance(Complete(), mutated.Child)
    harness.normalize_protocol(mutated.Child, contract)
    harness.normalize_protocol(mutated.Child, contract)
    assert isinstance(Complete(), mutated.Child)
    assert not isinstance(MissingData(), mutated.Child)
    assert mutated.Child.__non_callable_proto_members__ == {"label"}
