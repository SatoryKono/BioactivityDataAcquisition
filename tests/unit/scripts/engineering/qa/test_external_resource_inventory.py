"""Isolated integrity controls for the COMP-004 source inventory (no runtime I/O)."""

from __future__ import annotations

import copy
import hashlib
from typing import Any

import pytest

from scripts.engineering.qa.external_resource_inventory import (
    SCENARIOS,
    SourceBlob,
    validate_inventory,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def inventory_case() -> tuple[dict[str, Any], dict[str, bytes], dict[str, SourceBlob]]:
    """One real source expression; no product imports or external endpoints."""
    source = b"def acquire():\n    with open('fixture') as stream:\n        return stream.read()\n"
    path = "src/bioetl/fixture.py"
    blob = "b" * 40
    reference = {
        "file": path,
        "line": 2,
        "source_commit": "a" * 40,
        "source_blob": blob,
        "content_sha256": hashlib.sha256(source).hexdigest(),
        "expression": "open('fixture')",
    }
    record = {
        "identity": "fixture.file",
        "type": "file",
        "creator": ["acquire"],
        "owner": "acquire operation",
        "closer": "file context exit",
        "shutdown_contract": "close on context exit",
        "production_entrypoint": "fixture.acquire",
        "call_path": ["acquire", "open"],
        "production_binding": [dict(reference)],
        "creation_sites": [reference],
        "qualification": "SOURCE_QUALIFIED_NOT_RUNTIME_VERIFIED",
        "scenarios": {
            name: {
                "applicability": "owner boundary",
                "expected": "close handle",
                "observation": "inspect handle after exit",
                "runtime_result": "NOT_RUN_12553",
            }
            for name in SCENARIOS
        },
    }
    payload = {
        "schema_version": 1,
        "source_commit": "a" * 40,
        "source_files": {path: blob},
        "resources": [record],
        "accepted_site_keys": [[path, 2, "open('fixture')"]],
        "prior_candidates_input": {"count": 1},
        "prior_candidate_dispositions": [
            {
                "candidate_id": "legacy-1",
                "object": "FixtureOwner",
                "file": path,
                "disposition": "accepted concrete fixture",
                "resource_definitions": ["fixture.file"],
            }
        ],
    }
    return (
        payload,
        {path: source},
        {path: SourceBlob(blob, hashlib.sha256(source).hexdigest())},
    )


def test_correct_inventory_is_accepted(inventory_case: tuple) -> None:
    assert validate_inventory(*inventory_case) == []


@pytest.mark.parametrize(
    "argv",
    [
        ["--check", "--source-commit", "e" * 40],
        ["--check", "--reviewed-source", "src/bioetl/pure.py=" + "f" * 64],
        ["--update", "--reviewed-source", "src/bioetl/pure.py=" + "f" * 64],
    ],
)
def test_source_maintenance_requires_explicit_update_and_commit(
    inventory_case: tuple,
    monkeypatch: pytest.MonkeyPatch,
    argv: list[str],
) -> None:
    from scripts.engineering.qa import external_resource_inventory as inventory

    monkeypatch.setattr(inventory, "load_catalog", lambda **kwargs: inventory_case[0])
    assert inventory.main(argv) == 1


def test_reviewed_resource_free_rebind_preserves_facts_and_history(
    inventory_case: tuple,
) -> None:
    from scripts.engineering.qa.external_resource_inventory import (
        rebind_resource_free_sources,
    )

    payload, sources, blobs = copy.deepcopy(inventory_case)
    path = "src/bioetl/pure.py"
    payload["source_files"][path] = "c" * 40
    sources[path] = b"def pure():\n    return 2\n"
    digest = hashlib.sha256(sources[path]).hexdigest()
    blobs[path] = SourceBlob("d" * 40, digest)
    old = copy.deepcopy(payload)
    updated = rebind_resource_free_sources(
        payload,
        sources,
        blobs,
        commit="e" * 40,
        tree="f" * 40,
        reviewed={path: digest},
    )
    assert payload == old
    assert updated["source_commit"] == "e" * 40
    assert updated["source_tree"] == "f" * 40
    assert updated["source_files"] == {
        **old["source_files"],
        path: "d" * 40,
    }
    assert validate_inventory(updated, sources, blobs) == []
    assert updated["source_rebindings"][0]["from_commit"] == old["source_commit"]
    assert (
        updated["resources"][0]["shutdown_contract"]
        == old["resources"][0]["shutdown_contract"]
    )
    assert (
        updated["prior_candidate_dispositions"] == old["prior_candidate_dispositions"]
    )


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("unreviewed", "Reviewed source set must exactly match"),
        ("wrong_digest", "Reviewed source digest differs"),
        ("resource_file", "Resource-bearing source changes"),
        ("added_resource", "unreconciled source acquisition"),
        ("new_file", "Source census additions/removals"),
    ],
)
def test_source_rebind_cannot_bypass_inventory_review(
    inventory_case: tuple, case: str, message: str
) -> None:
    from scripts.engineering.qa.external_resource_inventory import (
        rebind_resource_free_sources,
    )

    payload, sources, blobs = copy.deepcopy(inventory_case)
    path = "src/bioetl/pure.py"
    if case == "resource_file":
        path = "src/bioetl/fixture.py"
    if case not in {"resource_file", "new_file"}:
        payload["source_files"][path] = "c" * 40
    source = b"def pure():\n    return 2\n"
    if case == "added_resource":
        source = b"def pure():\n    return open('new resource')\n"
    sources[path] = source
    digest = hashlib.sha256(source).hexdigest()
    blobs[path] = SourceBlob("d" * 40, digest)
    reviewed = {path: digest if case != "wrong_digest" else "0" * 64}
    if case == "unreviewed":
        reviewed = {}
    with pytest.raises(ValueError, match=message):
        rebind_resource_free_sources(
            payload,
            sources,
            blobs,
            commit="e" * 40,
            tree="f" * 40,
            reviewed=reviewed,
        )


@pytest.fixture
def resource_component(inventory_case: tuple) -> dict[str, Any]:
    return {
        "identity": "fixture.component",
        "type": "dependency stream",
        "creator": "dependency writer",
        "owner": "save operation",
        "lifetime": "one save",
        "closer": "dependency close",
        "shutdown_contract": "close after writing",
        "source": "dependency/writer.py",
        "version": "1.0",
        "source_sha256": hashlib.sha256(b"dependency").hexdigest(),
        "source_line": 1,
        "repo_source": dict(inventory_case[0]["resources"][0]["creation_sites"][0]),
    }


def test_correct_component_is_accepted_and_rendered(
    inventory_case: tuple, resource_component: dict[str, Any]
) -> None:
    from scripts.engineering.qa.external_resource_inventory import _render_components

    payload, sources, blobs = inventory_case
    payload["resources"][0]["resource_components"] = [resource_component]
    assert validate_inventory(payload, sources, blobs) == []
    assert "fixture.component" in "\n".join(_render_components(payload))


@pytest.mark.parametrize(
    "field",
    [
        "identity",
        "type",
        "creator",
        "owner",
        "lifetime",
        "closer",
        "shutdown_contract",
        "source",
        "version",
        "source_sha256",
        "source_line",
        "repo_source",
    ],
)
@pytest.mark.parametrize("replacement", [None, 3, ""])
def test_invalid_component_fields_are_rejected(
    inventory_case: tuple,
    resource_component: dict[str, Any],
    field: str,
    replacement: object,
) -> None:
    if field == "source_line" and replacement == 3:
        replacement = True
    resource_component[field] = replacement
    payload, sources, blobs = inventory_case
    payload["resources"][0]["resource_components"] = [resource_component]
    assert "invalid resource component schema" in validate_inventory(
        payload, sources, blobs
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [("source_line", 0), ("source_line", -1), ("source_sha256", "not-a-digest")],
)
def test_component_source_coordinates_are_valid(
    inventory_case: tuple, resource_component: dict[str, Any], field: str, value: object
) -> None:
    payload, sources, blobs = inventory_case
    resource_component[field] = value
    payload["resources"][0]["resource_components"] = [resource_component]
    assert "invalid resource component schema" in validate_inventory(
        payload, sources, blobs
    )


def test_component_requires_repository_source_provenance(
    inventory_case: tuple, resource_component: dict[str, Any]
) -> None:
    payload, sources, blobs = inventory_case
    resource_component["repo_source"].pop("source_blob")
    payload["resources"][0]["resource_components"] = [resource_component]
    assert "invalid resource component schema" in validate_inventory(
        payload, sources, blobs
    )


@pytest.mark.parametrize("components", [None, "invalid", {}, [None], [{}]])
def test_malformed_component_collections_are_rejected(
    inventory_case: tuple, components: object
) -> None:
    payload, sources, blobs = inventory_case
    payload["resources"][0]["resource_components"] = components
    assert any(
        "component" in error for error in validate_inventory(payload, sources, blobs)
    )


@pytest.mark.parametrize("identity", ["fixture.component", "fixture.file"])
def test_component_identities_are_unique(
    inventory_case: tuple, resource_component: dict[str, Any], identity: str
) -> None:
    payload, sources, blobs = inventory_case
    payload["resources"][0]["resource_components"] = [
        resource_component,
        dict(resource_component, identity=identity),
    ]
    assert any(
        "duplicate component identity" in error
        for error in validate_inventory(payload, sources, blobs)
    )


def test_duplicate_identity_is_rejected(inventory_case: tuple) -> None:
    payload, sources, blobs = inventory_case
    payload["resources"].append(copy.deepcopy(payload["resources"][0]))
    assert any(
        "duplicate identity" in item
        for item in validate_inventory(payload, sources, blobs)
    )


@pytest.mark.parametrize("identity", [None, "", " "])
def test_missing_identity_is_rejected(inventory_case: tuple, identity: object) -> None:
    payload, sources, blobs = inventory_case
    payload["resources"][0]["identity"] = identity
    assert "missing identity" in validate_inventory(payload, sources, blobs)


def test_missing_resource_is_rejected(inventory_case: tuple) -> None:
    payload, sources, blobs = inventory_case
    payload["resources"] = []
    assert "missing resources" in validate_inventory(payload, sources, blobs)


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_commit", "b" * 40),
        ("source_blob", "c" * 40),
        ("content_sha256", "0" * 64),
        ("line", 20),
        ("expression", "open('different')"),
    ],
)
def test_inconsistent_source_provenance_is_rejected(
    inventory_case: tuple,
    field: str,
    value: object,
) -> None:
    payload, sources, blobs = inventory_case
    payload["resources"][0]["creation_sites"][0][field] = value
    assert validate_inventory(payload, sources, blobs)


def test_changed_source_census_is_rejected(inventory_case: tuple) -> None:
    payload, sources, blobs = inventory_case
    blobs["src/bioetl/new.py"] = SourceBlob(
        "d" * 40, hashlib.sha256(b"pass\n").hexdigest()
    )
    sources["src/bioetl/new.py"] = b"pass\n"
    assert any("census" in item for item in validate_inventory(payload, sources, blobs))


def test_missing_acquisition_is_rejected(inventory_case: tuple) -> None:
    payload, sources, blobs = inventory_case
    payload["accepted_site_keys"].append(["src/bioetl/fixture.py", 3, "other()"])
    assert any(
        "coverage differs" in item
        for item in validate_inventory(payload, sources, blobs)
    )


def test_runtime_pass_cannot_be_invented(inventory_case: tuple) -> None:
    payload, sources, blobs = inventory_case
    payload["resources"][0]["scenarios"]["normal"]["runtime_result"] = "PASS"
    assert any(
        "runtime result" in item for item in validate_inventory(payload, sources, blobs)
    )


def test_made_up_binding_provenance_is_rejected(inventory_case: tuple) -> None:
    payload, sources, blobs = inventory_case
    payload["resources"][0]["production_binding"] = [{"made_up_binding": True}]
    assert any(
        "provenance schema" in e for e in validate_inventory(payload, sources, blobs)
    )


def test_callback_location_and_expression_are_checked(inventory_case: tuple) -> None:
    payload, sources, blobs = inventory_case
    site = payload["resources"][0]["creation_sites"][0]
    site.update(creation_mode="callback", line=1, expression="not a source expression")
    payload["accepted_site_keys"] = [[site["file"], 1, site["expression"]]]
    assert any(
        "source expression differs" in e
        for e in validate_inventory(payload, sources, blobs)
    )


def test_missing_history_is_rejected(inventory_case: tuple) -> None:
    payload, sources, blobs = inventory_case
    payload["prior_candidate_dispositions"] = []
    assert any(
        "historical candidate" in e for e in validate_inventory(payload, sources, blobs)
    )


def test_duplicate_history_identity_is_rejected(inventory_case: tuple) -> None:
    payload, sources, blobs = inventory_case
    payload["prior_candidates_input"]["count"] = 2
    payload["prior_candidate_dispositions"] *= 2
    assert any(
        "historical candidate" in e for e in validate_inventory(payload, sources, blobs)
    )


def test_missing_unreferenced_source_is_rejected(inventory_case: tuple) -> None:
    payload, sources, blobs = inventory_case
    name = "src/bioetl/unreferenced.py"
    blobs[name] = SourceBlob("d" * 40, hashlib.sha256(b"pass\n").hexdigest())
    payload["source_files"] = {path: blob.oid for path, blob in blobs.items()}
    assert any(
        "missing source content" in e
        for e in validate_inventory(payload, sources, blobs)
    )


def test_partitioned_catalog_roundtrip(inventory_case: tuple, tmp_path: Any) -> None:
    from scripts.engineering.qa.external_resource_inventory import (
        load_catalog,
        write_catalog,
    )

    payload, _, _ = inventory_case
    write_catalog(payload, tmp_path)
    loaded = load_catalog(tmp_path)
    assert loaded["resources"] == payload["resources"]
    assert loaded["source_files"] == payload["source_files"]


def test_partition_digest_rejects_changed_content(
    inventory_case: tuple, tmp_path: Any
) -> None:
    from scripts.engineering.qa.external_resource_inventory import (
        load_catalog,
        write_catalog,
    )

    payload, _, _ = inventory_case
    write_catalog(payload, tmp_path)
    part = tmp_path / "configs/quality/external_resource_inventory/part-01.json"
    part.write_bytes(part.read_bytes() + b" ")
    with pytest.raises(ValueError, match="digest"):
        load_catalog(tmp_path)


def test_partition_path_escape_is_rejected(
    inventory_case: tuple, tmp_path: Any
) -> None:
    import json
    from scripts.engineering.qa.external_resource_inventory import (
        CATALOG,
        load_catalog,
        write_catalog,
    )

    payload, _, _ = inventory_case
    write_catalog(payload, tmp_path)
    index = tmp_path / CATALOG
    data = json.loads(index.read_text())
    data["resource_parts"][0]["file"] = "outside.json"
    index.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="outside"):
        load_catalog(tmp_path)


def test_duplicate_partition_is_rejected(inventory_case: tuple, tmp_path: Any) -> None:
    import json
    from scripts.engineering.qa.external_resource_inventory import (
        CATALOG,
        load_catalog,
        write_catalog,
    )

    payload, _, _ = inventory_case
    write_catalog(payload, tmp_path)
    index = tmp_path / CATALOG
    data = json.loads(index.read_text())
    data["resource_parts"] *= 2
    index.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="duplicated"):
        load_catalog(tmp_path)


def test_changed_working_source_is_rejected(inventory_case: tuple) -> None:
    payload, sources, blobs = inventory_case
    sources["src/bioetl/fixture.py"] = sources["src/bioetl/fixture.py"].replace(
        b"return", b"yield"
    )
    assert any(
        "content changed" in item
        for item in validate_inventory(payload, sources, blobs)
    )


def test_synchronized_site_and_ledger_removal_is_rejected(
    inventory_case: tuple,
) -> None:
    payload, sources, blobs = inventory_case
    path = "src/bioetl/fixture.py"
    sources[path] += b"\nopen('omitted')\n"
    digest = hashlib.sha256(sources[path]).hexdigest()
    blobs[path] = SourceBlob(blobs[path].oid, digest)
    for field in ("production_binding", "creation_sites"):
        payload["resources"][0][field][0]["content_sha256"] = digest
    # Both catalog and ledger omit the second allocation; the source census must catch it.
    assert any(
        "unreconciled source acquisition" in e
        for e in validate_inventory(payload, sources, blobs)
    )


@pytest.mark.parametrize(
    "section", ["dynamic_wiring", "delegations_and_exclusions", "operation_aliases"]
)
def test_missing_reference_marker_cannot_bypass_provenance(
    inventory_case: tuple, section: str
) -> None:
    payload, sources, blobs = inventory_case
    ref = dict(payload["resources"][0]["creation_sites"][0])
    del ref["source_blob"]
    payload[section] = [ref]
    assert any(
        "provenance schema" in e for e in validate_inventory(payload, sources, blobs)
    )


@pytest.mark.parametrize("disposition", [None, "", " "])
def test_empty_historical_disposition_is_rejected(
    inventory_case: tuple, disposition: object
) -> None:
    payload, sources, blobs = inventory_case
    payload["prior_candidate_dispositions"][0]["disposition"] = disposition
    assert any(
        "historical candidate" in e for e in validate_inventory(payload, sources, blobs)
    )


def test_git_batch_snapshot_uses_actual_blob_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts.engineering.qa import external_resource_inventory as inventory

    oid = "e" * 40
    content = b"pass\n"
    response = f"{oid} blob {len(content)}\n".encode() + content + b"\n"
    calls = []

    def batch(command: list[str], *, input: bytes, cwd: Any) -> bytes:
        calls.append((command, input, cwd))
        return response

    monkeypatch.setattr(inventory.subprocess, "check_output", batch)
    assert inventory._load_source_blobs({"fixture.py": oid}) == {
        "fixture.py": SourceBlob(oid, hashlib.sha256(content).hexdigest())
    }
    assert calls == [
        (["git", "cat-file", "--batch"], f"{oid}\n".encode(), inventory.ROOT)
    ]


@pytest.mark.parametrize(
    "response",
    [
        b"wrong blob 5\npass\n\n",
        b"eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee tree 5\npass\n\n",
        b"eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee blob 8\npass\n",
    ],
)
def test_invalid_git_batch_snapshot_is_rejected(
    monkeypatch: pytest.MonkeyPatch, response: bytes
) -> None:
    from scripts.engineering.qa import external_resource_inventory as inventory

    monkeypatch.setattr(
        inventory.subprocess, "check_output", lambda *args, **kwargs: response
    )
    with pytest.raises(ValueError, match="pinned Git blob"):
        inventory._load_source_blobs({"fixture.py": "e" * 40})


@pytest.mark.parametrize(
    "field,value",
    [
        ("scenarios", None),
        ("scenarios", {"normal": None}),
        ("creation_sites", [None]),
        ("creation_sites", None),
    ],
)
def test_malformed_record_returns_diagnostic(
    inventory_case: tuple, field: str, value: object
) -> None:
    payload, sources, blobs = inventory_case
    payload["resources"][0][field] = value
    assert validate_inventory(payload, sources, blobs)


def test_unavailable_pinned_history_is_explicit(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import subprocess
    from scripts.engineering.qa import external_resource_inventory as inventory

    def unavailable(args: Any) -> int:
        raise subprocess.CalledProcessError(128, ["git", "ls-tree"])

    monkeypatch.setattr(inventory, "_run", unavailable)
    assert inventory.main(["--check"]) == 1
    assert "MISSING EVIDENCE" in capsys.readouterr().out


@pytest.mark.parametrize(
    "field,value",
    [
        ("prior_candidates_input", None),
        ("prior_candidates_input", []),
        ("prior_candidate_dispositions", None),
        ("prior_candidate_dispositions", [None]),
        ("prior_candidate_dispositions", ["not a record"]),
    ],
)
def test_malformed_history_returns_diagnostic(
    inventory_case: tuple, field: str, value: object
) -> None:
    payload, sources, blobs = inventory_case
    payload[field] = value
    assert any(
        "historical candidate" in error
        for error in validate_inventory(payload, sources, blobs)
    )


@pytest.mark.parametrize("definitions", [None, "fixture.file", [{}]])
def test_malformed_history_links_return_diagnostic(
    inventory_case: tuple, definitions: object
) -> None:
    payload, sources, blobs = inventory_case
    payload["prior_candidate_dispositions"][0]["resource_definitions"] = definitions
    assert any(
        "historical candidate" in error
        for error in validate_inventory(payload, sources, blobs)
    )


@pytest.mark.parametrize("command", [["git", "ls-files"], "git ls-files"])
def test_working_checkout_failure_is_not_missing_evidence(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], command: object
) -> None:
    import subprocess
    from scripts.engineering.qa import external_resource_inventory as inventory

    def failed(args: Any) -> int:
        raise subprocess.CalledProcessError(128, command)

    monkeypatch.setattr(inventory, "_run", failed)
    assert inventory.main(["--check"]) == 1
    output = capsys.readouterr().out
    assert "CHECK FAILED" in output
    assert "MISSING EVIDENCE" not in output
    assert "git ls-files" in output and "128" in output


@pytest.mark.parametrize(
    "expression",
    ["locking(1, 2, 1)", "flock(1, 2)", "Workbook()", "workbook.save('artifact.xlsx')"],
)
def test_omitted_delegated_resource_primitive_is_rejected(
    inventory_case: tuple, expression: str
) -> None:
    payload, sources, blobs = inventory_case
    path = "src/bioetl/fixture.py"
    sources[path] += ("\n" + expression + "\n").encode()
    digest = hashlib.sha256(sources[path]).hexdigest()
    blobs[path] = SourceBlob(blobs[path].oid, digest)
    for field in ("production_binding", "creation_sites"):
        payload["resources"][0][field][0]["content_sha256"] = digest
    assert any(
        "unreconciled source acquisition" in error
        for error in validate_inventory(payload, sources, blobs)
    )


@pytest.mark.parametrize("field", ["expression", "creation_mode"])
@pytest.mark.parametrize("value", [[], {}])
def test_component_reference_expression_types_are_diagnostics(
    inventory_case: tuple, resource_component: dict[str, Any], field: str, value: object
) -> None:
    payload, sources, blobs = inventory_case
    resource_component["repo_source"][field] = value
    payload["resources"][0]["resource_components"] = [resource_component]
    errors = validate_inventory(payload, sources, blobs)
    assert any("expression" in error or "creation mode" in error for error in errors)


@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize("identity", [None, "missing.resource", "fixture.file"])
def test_operation_alias_requires_existing_resource(
    inventory_case: tuple, nested: bool, identity: str | None
) -> None:
    payload, sources, blobs = inventory_case
    alias = dict(
        payload["resources"][0]["creation_sites"][0],
        resource_identity=identity,
    )
    section = payload["resources"][0] if nested else payload
    section["operation_aliases"] = [alias]
    errors = validate_inventory(payload, sources, blobs)
    if identity == "fixture.file":
        assert errors == []
    else:
        assert "operation alias links a missing resource identity" in errors


@pytest.mark.parametrize("aliases", [None, "invalid", [None], [{}]])
def test_malformed_nested_aliases_are_diagnostics(
    inventory_case: tuple, aliases: object
) -> None:
    payload, sources, blobs = inventory_case
    payload["resources"][0]["operation_aliases"] = aliases
    errors = validate_inventory(payload, sources, blobs)
    assert any("invalid provenance schema" in error for error in errors)


@pytest.mark.parametrize("change", ["owner", "resource_count"])
def test_update_rebuilds_edited_part_manifest(
    inventory_case: tuple, tmp_path: Any, change: str
) -> None:
    import json
    from scripts.engineering.qa.external_resource_inventory import (
        CATALOG,
        load_catalog,
        write_catalog,
    )

    payload, sources, blobs = inventory_case
    write_catalog(payload, tmp_path)
    index = tmp_path / CATALOG
    manifest = json.loads(index.read_text())
    part = tmp_path / manifest["resource_parts"][0]["file"]
    if change == "owner":
        data = json.loads(part.read_text())
        data["resources"][0]["owner"] = "reviewed changed owner"
        part.write_text(json.dumps(data))
    else:
        manifest["resource_parts"][0]["resource_count"] = 999
        index.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="digest|schema/count"):
        load_catalog(tmp_path)
    edited = load_catalog(tmp_path, verify_manifest=False)
    assert validate_inventory(edited, sources, blobs) == []
    write_catalog(edited, tmp_path)
    assert load_catalog(tmp_path)["resources"] == edited["resources"]


def test_update_never_relaxes_partition_path_boundary(
    inventory_case: tuple, tmp_path: Any
) -> None:
    import json
    from scripts.engineering.qa.external_resource_inventory import (
        CATALOG,
        load_catalog,
        write_catalog,
    )

    payload, _, _ = inventory_case
    write_catalog(payload, tmp_path)
    index = tmp_path / CATALOG
    data = json.loads(index.read_text())
    data["resource_parts"][0]["file"] = "outside.json"
    index.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="outside"):
        load_catalog(tmp_path, verify_manifest=False)
