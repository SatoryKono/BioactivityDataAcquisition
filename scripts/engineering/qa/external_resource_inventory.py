"""Check source-qualified COMP-004 data and render its readable projection."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
CATALOG = Path("configs/quality/external_resource_inventory.json")
REPORT = Path("reports/quality/external-resource-inventory.md")
SCENARIOS = frozenset({"normal", "error", "cancellation", "timeout", "retry"})
_OID = re.compile(r"[0-9a-f]{40}")
_REFERENCE_FIELDS = frozenset(
    {"file", "line", "source_commit", "source_blob", "content_sha256"}
)
_ACQUISITION_NAMES = frozenset(
    "AsyncClient ThreadPoolExecutor ProcessPoolExecutor Thread create_task "
    "ensure_future start_server Popen popen_factory DeltaTable _DeltaTable "
    "write_deltalake _write_deltalake open fdopen mkstemp NamedTemporaryFile "
    "TemporaryFile TemporaryDirectory FileHandler TracerProvider BatchSpanProcessor "
    "ConsoleSpanExporter exporter_class read_text read_bytes write_text write_bytes "
    "scandir iterdir glob rglob walk listdir stream_reader stream_writer new_file "
    "new_stream open_file to_thread run_in_executor read_csv write_csv read_parquet "
    "write_parquet scan_parquet scan_csv read_table to_excel copyfile copytree copy2 "
    "move rmtree push_gateway delete_gateway start_http_server_fn flock locking "
    "Workbook save".split()
)


@dataclass(frozen=True)
class SourceBlob:
    """Git-provided object identity and SHA256 of its actual blob bytes."""

    oid: str
    sha256: str


def _load_source_blobs(oids: Mapping[str, str]) -> dict[str, SourceBlob]:
    raw = subprocess.check_output(
        ["git", "cat-file", "--batch"],
        input="".join(f"{oid}\n" for oid in oids.values()).encode(),
        cwd=ROOT,
    )
    stream = BytesIO(raw)
    result = {}
    for path, oid in oids.items():
        actual, kind, size = stream.readline().decode().split()
        if actual != oid or kind != "blob":
            raise ValueError(f"invalid pinned Git blob: {path}")
        content = stream.read(int(size))
        if len(content) != int(size) or stream.read(1) != b"\n":
            raise ValueError(f"truncated pinned Git blob: {path}")
        result[path] = SourceBlob(oid, hashlib.sha256(content).hexdigest())
    return result


def _reference_schema(value: object, label: str) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(ref, dict) or not _REFERENCE_FIELDS.issubset(ref)
        for ref in value
    ):
        return [f"{label}: invalid provenance schema"]
    return []


def _check_acquisition_census(
    payload: dict[str, Any],
    sources: Mapping[str, bytes],
    sites: set[tuple[str, int, str]],
) -> list[str]:
    """Enumerate source calls independently of the authored acceptance ledger."""
    covered = sites | {
        (ref.get("file"), ref.get("line"), ref.get("expression"))
        for ref in payload.get("operation_aliases", [])
    }
    excluded = {
        (ref.get("file"), ref.get("line"), ref.get("call"))
        for ref in payload.get("delegations_and_exclusions", [])
    }
    errors = []
    for path, content in sources.items():
        for node in ast.walk(ast.parse(content)):
            if not isinstance(node, ast.Call):
                continue
            call = ast.unparse(node.func)
            if (
                call.rsplit(".", 1)[-1] not in _ACQUISITION_NAMES
                and call != "subprocess.run"
            ):
                continue
            key = (path, node.lineno, ast.unparse(node))
            if key not in covered and (path, node.lineno, call) not in excluded:
                errors.append(
                    f"unreconciled source acquisition: {path}:{node.lineno}: {call}"
                )
    return errors


def _references(value: object) -> list[dict[str, Any]]:  # Any: recursive JSON envelope.
    if isinstance(value, dict):
        found = [value] if "source_blob" in value else []
        return found + [ref for child in value.values() for ref in _references(child)]
    if isinstance(value, list):
        return [ref for child in value for ref in _references(child)]
    return []


def _check_reference(
    ref: dict[str, Any],  # Any: JSON source reference validated here.
    sources: Mapping[str, bytes],
    blobs: Mapping[str, SourceBlob],
    commit: str,
) -> list[str]:
    path = ref.get("file")
    if not isinstance(path, str) or path not in sources:
        return [f"source path missing or outside inventory: {path}"]
    errors: list[str] = []
    data = sources[path].replace(b"\r\n", b"\n")
    blob = blobs.get(path)
    if (
        ref.get("source_commit") != commit
        or blob is None
        or ref.get("source_blob") != blob.oid
    ):
        errors.append(f"inconsistent source provenance: {path}")
    if ref.get("content_sha256") != hashlib.sha256(data).hexdigest():
        errors.append(f"source content changed: {path}")
    errors.extend(_check_location(ref, data, path))
    errors.extend(_check_expression(ref, data, path))
    return errors


def _check_location(ref: dict[str, Any], data: bytes, path: str) -> list[str]:
    line = ref.get("line")
    if type(line) is not int or not 1 <= line <= len(data.splitlines()):
        return [f"invalid source line: {path}:{line}"]
    if (
        "source_segment" in ref
        and ref["source_segment"] != data.decode().splitlines()[line - 1].strip()
    ):
        return [f"source segment differs: {path}:{line}"]
    return []


def _check_expression(ref: dict[str, Any], data: bytes, path: str) -> list[str]:
    if "expression" not in ref:
        return []
    mode = ref.get("creation_mode", "call")
    modes: dict[str, tuple[type[ast.AST], ...]] = {
        "call": (ast.Call,),
        "callback-reference": (ast.Attribute, ast.Name),
        "callback": (ast.AsyncFunctionDef, ast.FunctionDef),
    }
    if mode not in modes:
        return [f"unsupported creation mode: {mode}"]
    line = ref.get("line")
    calls = {
        ast.unparse(node)
        for node in ast.walk(ast.parse(data))
        if isinstance(node, modes[mode]) and getattr(node, "lineno", None) == line
    }
    if ref["expression"] not in calls:
        return [f"source expression differs: {path}:{line}"]
    return []


def _check_record(
    record: dict[str, Any],  # Any: JSON resource record.
    seen: set[str],
    sites: set[tuple[str, int, str]],
) -> list[str]:
    errors: list[str] = []
    identity = record.get("identity")
    if not isinstance(identity, str) or not identity.strip():
        errors.append("missing identity")
    elif identity in seen:
        errors.append(f"duplicate identity: {identity}")
    else:
        seen.add(identity)
    for field in (
        "type",
        "creator",
        "owner",
        "closer",
        "shutdown_contract",
        "production_entrypoint",
        "production_binding",
        "call_path",
        "creation_sites",
    ):
        if not record.get(field):
            errors.append(f"{identity}: missing {field}")
    for field in (
        "creation_sites",
        "production_binding",
        "cleanup_sources",
        "configuration_predicates",
        "operation_aliases",
    ):
        errors.extend(_reference_schema(record.get(field, []), f"{identity}: {field}"))
    if record.get("qualification") != "SOURCE_QUALIFIED_NOT_RUNTIME_VERIFIED":
        errors.append(f"{identity}: unsupported runtime claim")
    errors.extend(_check_scenarios(record))
    errors.extend(_check_sites(record, sites))
    return errors


def _check_scenarios(record: dict[str, Any]) -> list[str]:
    scenarios = record.get("scenarios", {})
    if not isinstance(scenarios, dict) or set(scenarios) != SCENARIOS:
        return [
            f"{record.get('identity')}: incomplete scenarios or unsupported runtime result"
        ]
    if any(
        not isinstance(value, dict)
        or not value.get("applicability")
        or not value.get("expected")
        or not value.get("observation")
        or value.get("runtime_result") != "NOT_RUN_12553"
        for value in scenarios.values()
    ):
        return [
            f"{record.get('identity')}: incomplete scenarios or unsupported runtime result"
        ]
    return []


def _check_sites(record: dict[str, Any], sites: set[tuple[str, int, str]]) -> list[str]:
    errors = []
    identity = record.get("identity")
    references = record.get("creation_sites", [])
    if _reference_schema(references, "creation_sites"):
        return [f"{identity}: incomplete creation provenance"]
    for site in references:
        if not all(
            key in site for key in ("file", "line", "expression", "source_blob")
        ):
            errors.append(f"{identity}: incomplete creation provenance")
            continue
        key = (site["file"], site["line"], site["expression"])
        if key in sites:
            errors.append(f"{identity}: duplicate acquisition site")
        sites.add(key)
    return errors


def _check_source_census(
    payload: dict[str, Any],
    sources: Mapping[str, bytes],
    blobs: Mapping[str, SourceBlob],
) -> list[str]:
    errors = []
    if payload.get("source_files") != {path: blob.oid for path, blob in blobs.items()}:
        errors.append("source census missing, added, removed, or rebound files")
    if set(sources) != set(blobs):
        errors.append("missing source content or unexpected source file")
    for path, content in sources.items():
        canonical = content.replace(b"\r\n", b"\n")
        blob = blobs.get(path)
        if blob is None or hashlib.sha256(canonical).hexdigest() != blob.sha256:
            errors.append(f"working source blob differs: {path}")
    return errors


def _valid_disposition(row: object, identities: set[str]) -> bool:
    if not isinstance(row, dict):
        return False
    for field in ("candidate_id", "object", "file", "disposition"):
        value = row.get(field)
        if not isinstance(value, str) or not value.strip():
            return False
    definitions = row.get("resource_definitions", [])
    if not isinstance(definitions, list) or not all(
        isinstance(value, str) for value in definitions
    ):
        return False
    return set(definitions).issubset(identities)


def _check_history(payload: dict[str, Any], identities: set[str]) -> list[str]:
    history = payload.get("prior_candidate_dispositions", [])
    meta = payload.get("prior_candidates_input")
    expected = meta.get("count") if isinstance(meta, dict) else None
    if not isinstance(history, list) or not all(
        _valid_disposition(row, identities) for row in history
    ):
        return ["historical candidate coverage/identity linkage is inconsistent"]
    if (
        type(expected) is not int
        or expected < 1
        or len(history) != expected
        or len({row.get("candidate_id") for row in history}) != len(history)
    ):
        return ["historical candidate coverage/identity linkage is inconsistent"]
    return []


def _check_alias_links(payload: dict[str, Any], identities: set[str]) -> list[str]:
    for alias in payload.get("operation_aliases", []):
        identity = alias.get("resource_identity")
        if not isinstance(identity, str) or identity not in identities:
            return ["operation alias links a missing resource identity"]
    return []


def validate_inventory(
    payload: dict[str, Any],  # Any: JSON inventory boundary, checked below.
    sources: Mapping[str, bytes],
    blobs: Mapping[str, SourceBlob],
) -> list[str]:
    """Check catalog integrity without importing product code or opening endpoints."""
    errors: list[str] = []
    commit = payload.get("source_commit", "")
    if payload.get("schema_version") != 1 or not _OID.fullmatch(str(commit)):
        errors.append("invalid schema/source commit")
    errors.extend(_check_source_census(payload, sources, blobs))
    records = payload.get("resources")
    if not isinstance(records, list) or not records:
        return errors + ["missing resources"]
    if not all(isinstance(record, dict) for record in records):
        return errors + ["invalid resource record schema"]
    seen: set[str] = set()
    sites: set[tuple[str, int, str]] = set()
    for record in records:
        errors.extend(_check_record(record, seen, sites))
    schema_errors = [
        error
        for field in (
            "dynamic_wiring",
            "delegations_and_exclusions",
            "operation_aliases",
        )
        for error in _reference_schema(payload.get(field, []), field)
    ]
    if schema_errors:
        return errors + schema_errors
    for ref in _references(payload):
        errors.extend(_check_reference(ref, sources, blobs, str(commit)))
    errors.extend(_check_acquisition_census(payload, sources, sites))
    errors.extend(_check_alias_links(payload, seen))
    expected_sites = payload.get("accepted_site_keys")
    if (
        not isinstance(expected_sites, list)
        or sorted(map(list, sites)) != expected_sites
    ):
        errors.append(
            "resource missing or acquisition coverage differs from reviewed census"
        )
    errors.extend(_check_history(payload, seen))
    return errors


def render(payload: dict[str, Any]) -> str:  # Any: validated JSON catalog.
    """Render every resource and source link without inventing runtime results."""
    commit = payload["source_commit"]
    out = [
        "# External Resource Inventory",
        "",
        "Status: active",
        "Owner: BioETL Team",
        "Scope: #12552 / #12478 (COMP-004)",
        "",
        f"Source commit: {commit}; source tree: {payload['source_tree']}.",
        "",
        payload["scope_statement"],
        "",
        payload["completeness_method"],
        "",
        "Static inventory only. Runtime results are NOT_RUN_12553. No production "
        "endpoint, data operation, lifecycle trace or leak test is run here.",
        "",
        f"Definitions: {len(payload['resources'])}; historical candidates: "
        f"{len(payload['prior_candidate_dispositions'])}.",
        "",
        "## Resource definitions",
        "",
        "| Identity / type | Production binding / scope | Creator / owner / closer | Shutdown contract | Source |",
        "| --- | --- | --- | --- | --- |",
    ]
    for record in payload["resources"]:
        links = []
        for site in record["creation_sites"]:
            url = (
                "https://github.com/SatoryKono/BioactivityDataAcquisition/blob/"
                f"{commit}/{site['file']}#L{site['line']}"
            )
            links.append(f"[{site['file']}:{site['line']}]({url})")
        fields = [
            f"{record['identity']} / {record['type']}",
            record["production_entrypoint"] + " / " + record["lifetime"],
            "; ".join(record["creator"])
            + " / "
            + record["owner"]
            + " / "
            + record["closer"],
            record["shutdown_contract"],
            "<br>".join(dict.fromkeys(links)),
        ]
        out.append(
            "| "
            + " | ".join(str(x).replace("|", r"\|").replace("\n", " ") for x in fields)
            + " |"
        )
    out += _render_components(payload)
    out += [
        "",
        "## Coverage and history",
        "",
        payload["history_statement"],
        "",
        payload["reuse_statement"],
        "",
        "The JSON records accepted acquisitions, delegated/excluded sites, dynamic wiring "
        "and dispositions of all 377 historical candidates. Alias links do not create "
        "duplicate resources.",
        "",
        "## Validation and downstream use",
        "",
        "python -m scripts.engineering.qa.external_resource_inventory --check validates "
        "identities, source-file census, source blobs/content/lines, scenario and acquisition "
        "coverage. --update renders this Markdown from the canonical JSON.",
        "",
        "Integrity fixtures cover positive, duplicate identity, missing identity, missing "
        "resource and inconsistent provenance controls. They do not execute product code.",
        "",
        "For #12553 use every resource's scenario expectations and observation barriers; "
        "capture opened/closed/remaining identities and physical workers. Cancellation of "
        "a future does not prove stopped native work. Retry does not imply append idempotency. "
        "#12478 and #12553 retain their independent acceptance criteria.",
        "",
    ]
    return "\n".join(out)


def _render_components(payload: dict[str, Any]) -> list[str]:
    components = [
        component
        for row in payload["resources"]
        for component in row.get("resource_components", [])
    ]
    if not components:
        return []
    lines = [
        "",
        "## Delegated resource components",
        "",
        "| Identity / type | Creator / owner / lifetime | Closer / shutdown | Dependency source |",
        "| --- | --- | --- | --- |",
    ]
    for component in components:
        fields = [
            component["identity"] + " / " + component["type"],
            component["creator"]
            + " / "
            + component["owner"]
            + " / "
            + component["lifetime"],
            component["closer"] + "; " + component["shutdown_contract"],
            f"{component['source']}:{component['source_line']}; version {component['version']}; SHA256 {component['source_sha256']}",
        ]
        lines.append(
            "| "
            + " | ".join(
                field.replace("|", r"\|").replace("\n", " ") for field in fields
            )
            + " |"
        )
    return lines


def load_catalog(
    root: Path = ROOT,
    *,
    verify_manifest: bool = True,
) -> dict[str, Any]:  # Any: validated JSON envelope.
    """Load safe parts; strict checks verify derived digests/counts by default."""
    payload = json.loads((root / CATALOG).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Catalog index must be an object")
    if "resource_parts" not in payload:
        return payload
    resources = []
    seen = set()
    for part in payload["resource_parts"]:
        relative = Path(part["file"])
        path = (root / relative).resolve()
        if (
            not path.is_relative_to((root / CATALOG.with_suffix("")).resolve())
            or path in seen
        ):
            raise ValueError("Catalog part is outside its root or duplicated")
        seen.add(path)
        data = path.read_bytes()
        if verify_manifest and hashlib.sha256(data).hexdigest() != part["sha256"]:
            raise ValueError(f"Catalog part digest differs: {relative}")
        rows = json.loads(data)
        if (
            not isinstance(rows, dict)
            or rows.get("schema_version") != 1
            or not isinstance(rows.get("resources"), list)
            or (verify_manifest and len(rows["resources"]) != part["resource_count"])
        ):
            raise ValueError(f"Catalog part schema/count differs: {relative}")
        resources.extend(rows["resources"])
    payload["resources"] = resources
    return payload


def write_catalog(
    payload: dict[str, Any], root: Path = ROOT
) -> None:  # Any: source catalog.
    """Write deterministic size-bounded parts and their actual content hashes."""
    directory = root / CATALOG.with_suffix("")
    directory.mkdir(parents=True, exist_ok=True)
    batches: list[list[dict[str, Any]]] = [[]]  # Any: resource rows in validated JSON.
    for record in payload["resources"]:
        proposed = json.dumps(
            {"schema_version": 1, "resources": batches[-1] + [record]},
            indent=2,
            ensure_ascii=False,
        ).encode()
        if len(proposed) > 700_000 and batches[-1]:
            batches.append([])
        batches[-1].append(record)
    manifest = []
    for index, batch in enumerate(batches, 1):
        data = (
            json.dumps(
                {"schema_version": 1, "resources": batch}, indent=2, ensure_ascii=False
            )
            + "\n"
        ).encode()
        part = directory / f"part-{index:02}.json"
        part.write_bytes(data)
        manifest.append(
            {
                "file": part.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(data).hexdigest(),
                "resource_count": len(batch),
            }
        )
    header = {
        key: value
        for key, value in payload.items()
        if key not in {"resources", "resource_parts"}
    }
    header["resource_parts"] = manifest
    (root / CATALOG).write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main(argv: list[str] | None = None) -> int:
    """Check provenance; update canonical partitions, index digests and Markdown."""
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--update", action="store_true")
    args = parser.parse_args(argv)
    try:
        return _run(args)
    except subprocess.CalledProcessError as error:
        print(_git_failure_message(error))
        return 1
    except (OSError, ValueError) as error:
        print(f"Inventory input unavailable or invalid: {error}")
        return 1


def _git_failure_message(error: subprocess.CalledProcessError) -> str:
    args = error.cmd
    if isinstance(args, str):
        return f"CHECK FAILED: command exited {error.returncode}: {args}"
    command = " ".join(map(str, args))
    if (
        len(args) > 1
        and args[0] == "git"
        and args[1] in {"ls-tree", "cat-file", "rev-parse"}
    ):
        return (
            f"MISSING EVIDENCE: pinned Git command exited {error.returncode}: {command}; "
            "fetch full repository history if the pinned commit is absent"
        )
    return f"CHECK FAILED: command exited {error.returncode}: {command}"


def _run(args: argparse.Namespace) -> int:
    payload = load_catalog(verify_manifest=not args.update)
    commit = payload.get("source_commit", "")
    if not _OID.fullmatch(str(commit)):
        print("Invalid source commit")
        return 1
    tracked = (
        subprocess.check_output(["git", "ls-files", "-z", "--", "src/bioetl"], cwd=ROOT)
        .decode()
        .split("\0")
    )
    sources = {
        name: (ROOT / name).read_bytes() for name in tracked if name.endswith(".py")
    }
    entries = subprocess.check_output(
        ["git", "ls-tree", "-rz", commit, "--", "src/bioetl"], cwd=ROOT
    ).split(b"\0")
    oids = {}
    for entry in entries:
        if entry:
            meta, name = entry.split(b"\t", 1)
            if name.endswith(b".py"):
                oids[name.decode()] = meta.decode().split()[2]
    blobs = _load_source_blobs(oids)
    errors = validate_inventory(payload, sources, blobs)
    tree = (
        subprocess.check_output(["git", "rev-parse", f"{commit}^{{tree}}"], cwd=ROOT)
        .decode()
        .strip()
    )
    if payload.get("source_tree") != tree:
        errors.append("inconsistent source tree")
    if set(sources) != set(blobs):
        errors.append("working source census differs from pinned source")
    if errors:
        print("\n".join(errors))
        return 1
    expected = render(payload)
    if args.update:
        write_catalog(payload)
        (ROOT / REPORT).write_text(expected, encoding="utf-8", newline="\n")
    elif (ROOT / REPORT).read_text(encoding="utf-8") != expected:
        print("Readable inventory is stale; run --update")
        return 1
    print(
        f"PASS: {len(payload['resources'])} source-qualified definitions; runtime NOT_RUN_12553"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
