"""Materialize an explicitly reviewed source delta; never infer runtime qualification.

The review pins both its input catalog and target source to immutable Git commits.
Unchanged definitions are reused. Changed files and expressions require explicit
decisions, and the original independent acquisition census remains authoritative.
"""

from __future__ import annotations

import argparse
import ast
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any, cast

from scripts.engineering.qa import external_resource_inventory as inventory
from scripts.engineering.ci.test_telemetry_provenance import require_published_ancestor


@dataclass
class Snapshot:
    """Actual Git objects, never a checkout alias or caller-provided hashes."""

    commit: str
    tree: str
    sources: dict[str, bytes]
    blobs: dict[str, inventory.SourceBlob]


def _git(root: Path, *args: str, data: bytes | None = None) -> bytes:
    return subprocess.check_output(["git", *args], cwd=root, input=data)


def _snapshot(root: Path, commit: str) -> Snapshot:
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise ValueError("Review requires full immutable commit IDs")
    require_published_ancestor(root, commit)
    entries = _git(root, "ls-tree", "-rz", commit, "--", "src/bioetl").split(b"\0")
    oids: dict[str, str] = {}
    for entry in filter(None, entries):
        meta, source_path = entry.split(b"\t", 1)
        if source_path.endswith(b".py"):
            oids[source_path.decode()] = meta.decode().split()[2]
    raw = _git(
        root,
        "cat-file",
        "--batch",
        data="".join(f"{v}\n" for v in oids.values()).encode(),
    )
    sources: dict[str, bytes] = {}
    blobs: dict[str, inventory.SourceBlob] = {}
    offset = 0
    for relative_path, oid in oids.items():
        end = raw.index(b"\n", offset)
        actual_oid, kind, size = raw[offset:end].decode().split()
        if actual_oid != oid or kind != "blob":
            raise ValueError("Invalid source object")
        offset = end + 1
        content = raw[offset : offset + int(size)]
        offset += int(size) + 1
        sources[relative_path] = content
        blobs[relative_path] = inventory.SourceBlob(
            oid, hashlib.sha256(content).hexdigest()
        )
    return Snapshot(
        commit,
        _git(root, "rev-parse", f"{commit}^{{tree}}").decode().strip(),
        sources,
        blobs,
    )


def _catalog(root: Path, commit: str) -> dict[str, Any]:
    _snapshot(
        root, commit
    )  # Reject symbolic/unreachable references before Git path reads.
    payload = cast(
        dict[str, Any],
        json.loads(_git(root, "show", f"{commit}:{inventory.CATALOG.as_posix()}")),
    )
    if "resource_parts" not in payload:
        return payload
    rows = []
    for part in payload.pop("resource_parts"):
        path = Path(part["file"])
        if path.parent != inventory.CATALOG.with_suffix(""):
            raise ValueError("Catalog part outside canonical directory")
        data = _git(root, "show", f"{commit}:{path.as_posix()}")
        if hashlib.sha256(data).hexdigest() != part["sha256"]:
            raise ValueError("Pinned catalog part digest mismatch")
        batch = json.loads(data)["resources"]
        if len(batch) != part["resource_count"]:
            raise ValueError("Pinned catalog part count mismatch")
        rows.extend(batch)
    payload["resources"] = rows
    return payload


def _scope(tree: ast.AST, line: int) -> str:
    scopes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and node.lineno <= line <= (node.end_lineno or node.lineno)
    ]
    return ".".join(n.name for n in sorted(scopes, key=lambda n: n.lineno))


def _locate(snapshot: Snapshot, selector: dict[str, Any]) -> dict[str, Any]:
    path = selector["file"]
    tree = ast.parse(snapshot.sources[path])
    provenance = {
        "source_commit": snapshot.commit,
        "source_blob": snapshot.blobs[path].oid,
        "content_sha256": snapshot.blobs[path].sha256,
    }
    if "segment" in selector:
        lines = [
            i
            for i, text in enumerate(snapshot.sources[path].decode().splitlines(), 1)
            if text.strip() == selector["segment"]
            and _scope(tree, i) == selector["scope"]
        ]
        if len(lines) != 1:
            raise ValueError(f"Ambiguous or missing reviewed binding: {selector}")
        return {
            **provenance,
            "file": path,
            "line": lines[0],
            "source_segment": selector["segment"],
        }
    nodes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and _scope(tree, node.lineno) == selector["scope"]
        and ast.unparse(node.func) == selector["call"]
    ]
    if "expression" in selector:
        nodes = [n for n in nodes if ast.unparse(n) == selector["expression"]]
    if len(nodes) != 1:
        raise ValueError(f"Ambiguous or missing reviewed acquisition: {selector}")
    node = nodes[0]
    return {
        **provenance,
        "file": path,
        "line": node.lineno,
        "expression": ast.unparse(node),
        "call": ast.unparse(node.func),
        "creator": selector["scope"],
        "creation_mode": "call",
        "context_manager": False,
    }


def _relocate(
    ref: dict[str, Any],
    old: Snapshot,
    new: Snapshot,
    replacements: dict[str, str],
    segment_replacements: dict[str, str],
) -> None:
    path, line = ref["file"], ref["line"]
    old_tree, new_tree = ast.parse(old.sources[path]), ast.parse(new.sources[path])
    scope = _scope(old_tree, line)
    if "expression" in ref:
        candidates = _expression_candidates(ref, new_tree, scope, replacements)
    else:
        candidates = _segment_candidates(
            ref,
            old.sources[path],
            new.sources[path],
            new_tree,
            scope,
            segment_replacements,
        )
    if len(candidates) != 1:
        raise ValueError(
            f"Reference relocation needs an explicit unambiguous review: {path}:{line}"
        )
    ref["line"] = candidates[0]
    if "source_segment" in ref:
        ref["source_segment"] = (
            new.sources[path].decode().splitlines()[ref["line"] - 1].strip()
        )


def _expression_candidates(
    ref: dict[str, Any],
    tree: ast.AST,
    scope: str,
    replacements: dict[str, str],
) -> list[int]:
    expression = replacements.get(ref["expression"], ref["expression"])
    kinds = {
        "call": (ast.Call,),
        "callback-reference": (ast.Name, ast.Attribute),
        "callback": (ast.FunctionDef, ast.AsyncFunctionDef),
    }
    creation_mode = ref.get("creation_mode", "call")
    if creation_mode not in kinds:
        raise ValueError(f"Unsupported reference creation mode: {creation_mode}")
    candidates = []
    for node in ast.walk(tree):
        if (
            not isinstance(node, kinds[creation_mode])
            or ast.unparse(node) != expression
        ):
            continue
        node_line = getattr(node, "lineno", None)
        if isinstance(node_line, int) and _scope(tree, node_line) == scope:
            candidates.append(node_line)
    ref["expression"] = expression
    return candidates


def _segment_candidates(
    ref: dict[str, Any],
    old_source: bytes,
    new_source: bytes,
    new_tree: ast.AST,
    scope: str,
    replacements: dict[str, str],
) -> list[int]:
    line = ref["line"]
    segment = ref.get(
        "source_segment", old_source.decode().splitlines()[line - 1].strip()
    )
    segment = replacements.get(segment, segment)
    return [
        index
        for index, text in enumerate(new_source.decode().splitlines(), 1)
        if text.strip() == segment and _scope(new_tree, index) == scope
    ]


def _validate_review_schema(review: dict[str, Any]) -> None:
    allowed = {
        "schema_version",
        "catalog_ref",
        "source_ref",
        "source_reviews",
        "expression_updates",
        "segment_updates",
        "reference_moves",
        "resource_updates",
        "additional_bindings",
        "new_resources",
        "new_exclusions",
    }
    if review["schema_version"] != 1 or set(review) - allowed:
        raise ValueError("Unsupported review schema")


def _apply_reference_moves(
    payload: dict[str, Any], review: dict[str, Any], new: Snapshot
) -> None:
    """Apply exact, reviewed moves for resource references that changed files."""
    records = {row["identity"]: row for row in payload["resources"]}
    allowed_fields = {"creation_sites", "production_binding", "cleanup_sources"}
    for move in review.get("reference_moves", []):
        record, fields, source, target = _validated_reference_move(
            move, records, allowed_fields
        )
        matches = sum(
            _move_matching_references(record.get(field, []), source, target, new)
            for field in fields
        )
        if matches != len(fields):
            raise ValueError("Reviewed reference move was missing or ambiguous")


def _validated_reference_move(
    move: dict[str, Any],
    records: dict[str, dict[str, Any]],
    allowed_fields: set[str],
) -> tuple[dict[str, Any], list[str], dict[str, Any], dict[str, Any]]:
    if set(move) != {"identity", "fields", "from", "to"}:
        raise ValueError("Invalid reviewed reference move schema")
    fields = move["fields"]
    if move["identity"] not in records or not set(fields) <= allowed_fields:
        raise ValueError("Reference move must name an existing resource and fields")
    source = move["from"]
    if set(source) - {"file", "line", "expression", "source_segment"}:
        raise ValueError("Invalid reviewed reference move source selector")
    return records[move["identity"]], fields, source, move["to"]


def _move_matching_references(
    refs: list[dict[str, Any]],
    source: dict[str, Any],
    target: dict[str, Any],
    new: Snapshot,
) -> int:
    matches = 0
    for index, ref in enumerate(refs):
        if not all(ref.get(key) == value for key, value in source.items()):
            continue
        refs[index] = _locate(new, target)
        matches += 1
    return matches


def _apply_resource_reviews(
    payload: dict[str, Any], review: dict[str, Any], new: Snapshot
) -> None:
    records = {row["identity"]: row for row in payload["resources"]}
    for identity, update in review.get("resource_updates", {}).items():
        if set(update) - {
            "creator",
            "owner",
            "closer",
            "shutdown_contract",
            "call_path",
            "production_entrypoint",
            "scenarios",
        }:
            raise ValueError(
                "Existing resource identity, acquisition and qualification cannot be replaced"
            )
        records[identity].update(update)
    for identity, selectors in review.get("additional_bindings", {}).items():
        records[identity]["production_binding"].extend(
            _locate(new, s) for s in selectors
        )
    for record in deepcopy(review.get("new_resources", [])):
        record["creation_sites"] = [
            _locate(new, s) for s in record.pop("site_selectors")
        ]
        bindings = record.pop("binding_selectors", [])
        record["production_binding"] = (
            [_locate(new, s) for s in bindings]
            if bindings
            else deepcopy(record["creation_sites"])
        )
        record["cleanup_sources"] = [
            _locate(new, s) for s in record.pop("cleanup_selectors", [])
        ]
        if record["identity"] in records:
            raise ValueError("New resource duplicates an existing identity")
        records[record["identity"]] = record
        payload["resources"].append(record)
    for selector in review.get("new_exclusions", []):
        ref = _locate(new, selector)
        ref["scope"], ref["reason"] = selector["scope"], selector["reason"]
        payload["delegations_and_exclusions"].append(ref)


def build_requalification(root: Path, review: dict[str, Any]) -> dict[str, Any]:
    """Construct a candidate only after proving the old and new source closures."""
    _validate_review_schema(review)
    original = _catalog(root, review["catalog_ref"])
    old = _snapshot(root, original["source_commit"])
    new = _snapshot(root, review["source_ref"])
    errors = inventory.validate_inventory(original, old.sources, old.blobs)
    if errors:
        raise ValueError("Invalid original catalog: " + "; ".join(errors))
    changed = {
        p
        for p in old.sources.keys() | new.sources.keys()
        if old.sources.get(p) != new.sources.get(p)
    }
    decisions = review["source_reviews"]
    if set(decisions) != changed or any(
        not isinstance(v, str) or not v.strip() for v in decisions.values()
    ):
        raise ValueError(
            "Every changed source requires an explicit review; no extra or missing decisions"
        )
    payload = deepcopy(original)
    _apply_reference_moves(payload, review, new)
    for ref in inventory._references(payload):
        if ref["file"] in changed and ref.get("source_commit") != new.commit:
            _relocate(
                ref,
                old,
                new,
                review.get("expression_updates", {}).get(ref["file"], {}),
                review.get("segment_updates", {}).get(ref["file"], {}),
            )
    _apply_resource_reviews(payload, review, new)
    for ref in inventory._references(payload):
        path = ref["file"]
        ref.update(
            source_commit=new.commit,
            source_blob=new.blobs[path].oid,
            content_sha256=new.blobs[path].sha256,
        )
    payload.update(
        source_commit=new.commit,
        source_tree=new.tree,
        source_files={p: b.oid for p, b in new.blobs.items()},
    )
    payload["source_requalification"] = {
        "catalog_ref": review["catalog_ref"],
        "source_ref": new.commit,
        "baseline_source_ref": old.commit,
        "review_sha256": hashlib.sha256(
            json.dumps(review, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "production_file_count": len(new.sources),
        "definition_count": len(payload["resources"]),
        "creation_site_count": sum(
            len(row["creation_sites"]) for row in payload["resources"]
        ),
        "runtime_result": "NOT_RUN_12553",
    }
    payload["accepted_site_keys"] = sorted(
        [s["file"], s["line"], s["expression"]]
        for row in payload["resources"]
        for s in row["creation_sites"]
    )
    if (
        payload["prior_candidate_dispositions"]
        != original["prior_candidate_dispositions"]
    ):
        raise ValueError("Historical dispositions must remain unchanged")
    tracked = _git(root, "ls-files", "-z", "--", "src/bioetl").decode().split("\0")
    working = {p: (root / p).read_bytes() for p in tracked if p.endswith(".py")}
    errors = inventory.validate_inventory(payload, working, new.blobs)
    if errors:
        raise ValueError("Unqualified target source: " + "; ".join(errors))
    return payload


def main(argv: list[str] | None = None) -> int:
    """Check/update only the active inventory through its original canonical writer."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--update", action="store_true")
    args = parser.parse_args(argv)
    root = inventory.ROOT
    try:
        path = (root / args.review).resolve(strict=True)
        if not path.is_relative_to((root / "configs/quality").resolve()):
            raise ValueError("Review must be a repository quality input")
        expected = build_requalification(
            root, json.loads(path.read_text(encoding="utf-8"))
        )
        projection = inventory.render(expected)
        if args.update:
            inventory.write_catalog(expected, root=root)
            (root / inventory.REPORT).write_text(
                projection, encoding="utf-8", newline="\n"
            )
        actual = inventory.load_catalog(root)
        actual.pop("resource_parts", None)
        if (
            actual != expected
            or (root / inventory.REPORT).read_text(encoding="utf-8") != projection
        ):
            print("Reviewed source requalification is stale; run --update")
            return 1
        print(
            "PASS: reviewed source delta; runtime qualification remains NOT_RUN_12553"
        )
        return 0
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        print(f"Source requalification refused: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
