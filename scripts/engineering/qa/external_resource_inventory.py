"""Check source-qualified COMP-004 data and render its readable projection."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
from collections.abc import Mapping
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
    blobs: Mapping[str, str],
    commit: str,
) -> list[str]:
    path = ref.get("file")
    if not isinstance(path, str) or path not in sources:
        return [f"source path missing or outside inventory: {path}"]
    errors: list[str] = []
    data = sources[path].replace(b"\r\n", b"\n")
    if ref.get("source_commit") != commit or ref.get("source_blob") != blobs.get(path):
        errors.append(f"inconsistent source provenance: {path}")
    if ref.get("content_sha256") != hashlib.sha256(data).hexdigest():
        errors.append(f"source content changed: {path}")
    line = ref.get("line")
    if type(line) is not int or not 1 <= line <= len(data.splitlines()):
        errors.append(f"invalid source line: {path}:{line}")
    elif (
        "source_segment" in ref
        and ref["source_segment"] != data.decode().splitlines()[line - 1].strip()
    ):
        errors.append(f"source segment differs: {path}:{line}")
    if "expression" in ref:
        mode = ref.get("creation_mode", "call")
        if mode not in {"call", "callback", "callback-reference"}:
            errors.append(f"unsupported creation mode: {mode}")
        kinds = (
            (ast.Call,)
            if mode == "call"
            else (ast.Attribute, ast.Name)
            if mode == "callback-reference"
            else (ast.AsyncFunctionDef, ast.FunctionDef)
        )
        calls = {
            ast.unparse(node)
            for node in ast.walk(ast.parse(data))
            if isinstance(node, kinds) and node.lineno == line
        }
        if ref["expression"] not in calls:
            errors.append(f"source expression differs: {path}:{line}")
    return errors


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
    for field in ("creation_sites", "production_binding", "cleanup_sources"):
        references = record.get(field, [])
        if not isinstance(references, list) or any(
            not isinstance(ref, dict) or not _REFERENCE_FIELDS.issubset(ref)
            for ref in references
        ):
            errors.append(f"{identity}: invalid {field} provenance schema")
    if record.get("qualification") != "SOURCE_QUALIFIED_NOT_RUNTIME_VERIFIED":
        errors.append(f"{identity}: unsupported runtime claim")
    scenarios = record.get("scenarios", {})
    if set(scenarios) != SCENARIOS or any(
        not value.get("applicability")
        or not value.get("expected")
        or not value.get("observation")
        or value.get("runtime_result") != "NOT_RUN_12553"
        for value in scenarios.values()
    ):
        errors.append(f"{identity}: incomplete scenarios or unsupported runtime result")
    for site in record.get("creation_sites", []):
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


def validate_inventory(
    payload: dict[str, Any],  # Any: JSON inventory boundary, checked below.
    sources: Mapping[str, bytes],
    blobs: Mapping[str, str],
) -> list[str]:
    """Check catalog integrity without importing product code or opening endpoints."""
    errors: list[str] = []
    commit = payload.get("source_commit", "")
    if payload.get("schema_version") != 1 or not _OID.fullmatch(str(commit)):
        errors.append("invalid schema/source commit")
    recorded = payload.get("source_files")
    if not isinstance(recorded, dict) or recorded != dict(blobs):
        errors.append("source census missing, added, removed, or rebound files")
    if set(sources) != set(blobs):
        errors.append("missing source content or unexpected source file")
    for path, content in sources.items():
        canonical = content.replace(b"\r\n", b"\n")
        header = b"blob " + str(len(canonical)).encode() + b"\0"
        if hashlib.sha1(header + canonical).hexdigest() != blobs.get(path):
            errors.append(f"working source blob differs: {path}")
    records = payload.get("resources")
    if not isinstance(records, list) or not records:
        return errors + ["missing resources"]
    seen: set[str] = set()
    sites: set[tuple[str, int, str]] = set()
    for record in records:
        errors.extend(_check_record(record, seen, sites))
    for ref in _references(payload):
        errors.extend(_check_reference(ref, sources, blobs, str(commit)))
    expected_sites = payload.get("accepted_site_keys")
    if (
        not isinstance(expected_sites, list)
        or sorted(map(list, sites)) != expected_sites
    ):
        errors.append(
            "resource missing or acquisition coverage differs from reviewed census"
        )
    history = payload.get("prior_candidate_dispositions", [])
    expected_count = payload.get("prior_candidates_input", {}).get("count")
    if (
        not isinstance(expected_count, int)
        or expected_count < 1
        or (
            len(history) != expected_count
            or len({row.get("candidate_id") for row in history}) != len(history)
            or any(
                not row.get("object")
                or not row.get("file")
                or not set(row.get("resource_definitions", [])).issubset(seen)
                for row in history
            )
        )
    ):
        errors.append("historical candidate coverage/identity linkage is inconsistent")
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


def load_catalog(root: Path = ROOT) -> dict[str, Any]:  # Any: validated JSON envelope.
    """Load hash-bound parts while keeping every source file below size policy."""
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
        if hashlib.sha256(data).hexdigest() != part["sha256"]:
            raise ValueError(f"Catalog part digest differs: {relative}")
        rows = json.loads(data)
        if (
            rows.get("schema_version") != 1
            or len(rows["resources"]) != part["resource_count"]
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
    """Check source provenance and check/update only the readable projection."""
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--update", action="store_true")
    args = parser.parse_args(argv)
    payload = load_catalog()
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
    blobs = {}
    for entry in entries:
        if entry:
            meta, name = entry.split(b"\t", 1)
            if name.endswith(b".py"):
                blobs[name.decode()] = meta.decode().split()[2]
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
