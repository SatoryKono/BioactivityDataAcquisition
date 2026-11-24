"""Hash and preserve the typed local dependency closure of target deployment."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Mapping
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import url2pathname

import yaml

from bioetl.infrastructure.adapters.iuphar import decode_json, load_profile
from bioetl.infrastructure.adapters.iuphar.snapshot_loader import OUTPUT_NAMES


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _digest(value: object) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[a-f0-9]{64}", value) is None:
        raise ValueError("target dependency needs a lowercase SHA256")
    return value


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ValueError("target dependency needs an object")
    return value


def _text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("target dependency needs a nonempty file reference")
    return value


def _safe_path(workspace: Path, path: Path) -> Path:
    candidate = (path if path.is_absolute() else workspace / path).absolute()
    if ".." in candidate.parts:
        raise ValueError("target dependency refuses parent traversal")
    _reject_links(candidate)
    _reject_environment(candidate)
    resolved = candidate.resolve()
    if resolved == workspace or not resolved.is_relative_to(workspace):
        raise ValueError("target dependency escapes the approved workspace")
    return resolved


def _workspace(path: Path) -> Path:
    _reject_links(path.absolute())
    return path.resolve(strict=True)


def _reject_links(path: Path) -> None:
    for part in (path, *path.parents):
        if part.is_symlink() or part.is_junction():
            raise ValueError("target dependency refuses symlink/junction paths")


def _reject_environment(path: Path) -> None:
    if any(
        part.lower().endswith(".env") or part.lower().startswith(".env.")
        for part in path.parts
    ):
        raise ValueError("environment files cannot enter target dependencies")


def _local_path(workspace: Path, value: str, *, base: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        parsed = urlsplit(value)
        if parsed.scheme:
            if parsed.scheme != "file" or parsed.netloc not in {"", "localhost"}:
                raise ValueError(
                    "target dependency requires a resolvable local file URI"
                )
            if parsed.query or parsed.fragment or not parsed.path:
                raise ValueError("target dependency has an invalid file URI")
            path = Path(url2pathname(parsed.path))
        else:
            path = base / path
    return _safe_path(workspace, path)


def _dependency_document(raw: bytes) -> Mapping[str, object]:
    try:
        return _mapping(decode_json(raw))
    except ValueError as exc:
        if str(exc) == "duplicate JSON key":
            raise ValueError("duplicate target dependency JSON key") from exc
        raise


class _DependencyCollector:
    def __init__(
        self,
        workspace: Path,
        *,
        include_acceptance_proofs: bool = True,
        on_file: Callable[[str, bytes], None] | None = None,
    ) -> None:
        self.workspace = workspace
        self.include_acceptance_proofs = include_acceptance_proofs
        self.on_file = on_file
        self.dependencies: dict[str, str] = {}
        self.visited: set[tuple[Path, str]] = set()
        # Matches snapshot_evidence._review: evidence paths are relative to the
        # coverage directory, not the nested review file directory.
        self._scope_evidence_root: Path | None = None

    def add(self, path: Path, expected: str | None = None) -> bytes:
        path = _safe_path(self.workspace, path)
        raw = path.read_bytes()
        digest = _sha256(raw)
        if expected is not None and digest != _digest(expected):
            raise ValueError("target dependency digest mismatch")
        key = path.relative_to(self.workspace).as_posix()
        previous = self.dependencies.get(key)
        if previous is not None and previous != digest:
            raise ValueError("target dependency changed during collection")
        self.dependencies[key] = digest
        if previous is None and self.on_file is not None:
            self.on_file(key, raw)
        return raw

    def document(self, path: Path, kind: str, expected: str | None = None) -> None:
        raw = self.add(path, expected)
        identity = (path, kind)
        if identity in self.visited:
            return
        self.visited.add(identity)
        document = _dependency_document(raw)
        handlers = {
            "profile": self.profile,
            "snapshot": self.snapshot,
            "acquisition": self.acquisition,
            "coverage": self.coverage,
            "scope_review": self.scope_review,
            "acceptance": self.acceptance,
            "expected_labels": self.expected_labels,
            "pipeline_proof": self.proof,
            "stage0_manifest": self.stage0,
            "row_manifest": self.row,
            "fk_restoration": self.fk_restoration,
        }
        handlers[kind](path, document)

    def reference(self, root: Path, value: object, kind: str | None = None) -> None:
        reference = _mapping(value)
        relative = _text(reference.get("path"))
        if Path(relative).is_absolute() or urlsplit(relative).scheme:
            raise ValueError("typed target references require relative file paths")
        path = _local_path(self.workspace, relative, base=root)
        digest = _digest(reference.get("sha256"))
        if kind is None:
            self.add(path, digest)
        else:
            self.document(path, kind, digest)

    def profile(self, path: Path, document: Mapping[str, object]) -> None:
        _header(document, "bioetl_iuphar_profile", (1, 2))
        self.reference(path.parent, document.get("snapshot"), "snapshot")
        if document.get("acceptance") is not None:
            self.reference(path.parent, document["acceptance"], "acceptance")

    def snapshot(self, path: Path, document: Mapping[str, object]) -> None:
        _header(document, "bioetl_iuphar_snapshot", (1, 2))
        self.reference(path.parent, document.get("targets"))
        if document["schema_version"] == 2:
            self.reference(path.parent, document.get("projection_audit"))
            self.reference(path.parent, document.get("acquisition"), "acquisition")
            self.reference(path.parent, document.get("coverage"), "coverage")

    def acquisition(self, path: Path, document: Mapping[str, object]) -> None:
        _header(document, "bioetl_iuphar_acquisition", (1,))
        references = _mapping(document.get("raw_artifacts"))
        if not references:
            raise ValueError("target acquisition has no raw artifacts")
        for reference in references.values():
            self.reference(path.parent, reference)

    def coverage(self, path: Path, document: Mapping[str, object]) -> None:
        _header(document, "bioetl_iuphar_coverage", (1,))
        previous = self._scope_evidence_root
        self._scope_evidence_root = path.parent
        try:
            self.reference(path.parent, document.get("review"), "scope_review")
        finally:
            self._scope_evidence_root = previous

    def scope_review(self, path: Path, document: Mapping[str, object]) -> None:
        _header(document, "bioetl_iuphar_scope_review", (1,))
        references = document.get("evidence_references", [])
        if not isinstance(references, list):
            raise ValueError("scope review evidence references must be a typed list")
        evidence_root = self._scope_evidence_root or path.parent
        for reference in references:
            self.reference(evidence_root, reference)

    def acceptance(self, path: Path, document: Mapping[str, object]) -> None:
        _header(document, "bioetl_iuphar_acceptance", (1, 2))
        # Historical shadow receipts bind hashes without a typed file closure.
        # Preserve their pinned bytes; load_profile still validates the receipt
        # and requires schema 2 whenever the configuration activates enrich.
        if document["schema_version"] == 1 or not self.include_acceptance_proofs:
            return
        references = document.get("artifact_references")
        if not isinstance(references, list) or not references:
            raise ValueError("target acceptance needs resolvable artifact references")
        for value in references:
            reference = _mapping(value)
            target = _local_path(
                self.workspace, _text(reference.get("immutable_uri")), base=path.parent
            )
            digest = _digest(reference.get("sha256"))
            kind = _acceptance_kind(reference.get("kind"))
            if kind in {"pipeline_proof", "stage0_manifest", "expected_labels"}:
                self.document(target, str(kind), digest)
            else:
                self.add(target, digest)

    def expected_labels(self, path: Path, document: Mapping[str, object]) -> None:
        _header(document, "bioetl_iuphar_reference_cases", (1, 2))
        cases = document.get("cases")
        if not isinstance(cases, list) or not cases:
            raise ValueError("expected labels need typed reviewed case proofs")
        for case in cases:
            self.review_proofs(path.parent, _mapping(case).get("source_references"))
        matrix = _mapping(document.get("reference_matrix", {}))
        for category in matrix.values():
            self.review_proofs(path.parent, _mapping(category).get("source_references"))

    def review_proofs(self, root: Path, references: object) -> None:
        if not isinstance(references, list) or not references:
            raise ValueError("reference review needs declared source proof files")
        for reference in references:
            self.reference(root, reference)

    def proof(self, path: Path, document: Mapping[str, object]) -> None:
        _header(document, "bioetl_iuphar_pipeline_evidence", (1,))
        self.artifacts(path.parent, document.get("artifact_sha256"), rows=True)
        if document.get("pipeline_report") is not None:
            self.reference(path.parent, document["pipeline_report"])

    def stage0(self, path: Path, document: Mapping[str, object]) -> None:
        _header(document, "stage0_manifest", (1, 2))
        self.artifacts(path.parent, document.get("artifact_sha256"))

    def row(self, path: Path, document: Mapping[str, object]) -> None:
        if set(_mapping(document.get("artifact_sha256"))) != OUTPUT_NAMES:
            raise ValueError("target pipeline row needs all six artifact files")
        self.artifacts(path.parent, document.get("artifact_sha256"))

    def fk_restoration(self, path: Path, document: Mapping[str, object]) -> None:
        _header(document, "bioetl_target_fk_restoration", (1,))
        if document.get("status") != "validated_candidate":
            raise ValueError(
                "blocked target FK restoration cannot enter migration input"
            )
        sources = document.get("sources")
        files = document.get("candidate_files")
        if not isinstance(sources, list) or not sources:
            raise ValueError("target FK restoration needs source proofs")
        if not isinstance(files, list) or not files:
            raise ValueError("target FK restoration needs candidate bytes")
        for item in (*sources, *files):
            self.reference(self.workspace, item)

    def artifacts(self, root: Path, value: object, *, rows: bool = False) -> None:
        artifacts = _mapping(value)
        if not artifacts:
            raise ValueError("target proof has no artifact byte references")
        for name, digest in artifacts.items():
            kind = (
                "row_manifest"
                if rows and Path(name).name == "row-manifest.json"
                else None
            )
            self.reference(root, {"path": name, "sha256": digest}, kind)


def _header(
    document: Mapping[str, object], artifact: str, versions: tuple[int, ...]
) -> None:
    if (
        document.get("artifact") != artifact
        or type(document.get("schema_version")) is not int
    ):
        raise ValueError("unsupported typed target dependency")
    if document["schema_version"] not in versions:
        raise ValueError("unsupported target dependency version")


def _acceptance_kind(value: object) -> str:
    kind = _text(value)
    known = {
        "stage0_manifest",
        "expected_labels",
        "cohort_manifest",
        "conversion_ledger",
        "pipeline_proof",
        "pipeline_report",
        "stage0_cohort",
        "stage0_evidence",
    }
    if kind not in known | OUTPUT_NAMES and not kind.startswith("stage0_proof:"):
        raise ValueError("unsupported acceptance artifact reference kind")
    return kind


def collect_target_dependencies(
    *,
    workspace: Path,
    configs: tuple[Path, ...],
    restoration_manifest: Path | None = None,
) -> dict[str, str]:
    """Bind config bytes and their typed IUPHAR closure, including old profiles."""
    collector = _DependencyCollector(_workspace(workspace))
    if restoration_manifest is not None:
        collector.document(restoration_manifest, "fk_restoration")
    profiles: list[tuple[Path, str, bool]] = []
    for config in configs:
        config_path = _safe_path(collector.workspace, config)
        document = _mapping(yaml.safe_load(collector.add(config_path)))
        pipeline = _mapping(document.get("pipeline", document))
        classification = _mapping(pipeline.get("target_classification", {}))
        mode = classification.get("mode", "off")
        if mode == "off":
            continue
        if mode not in {"shadow", "enrich"}:
            raise ValueError("unsupported target classification deployment mode")
        path = _local_path(
            collector.workspace,
            _text(classification.get("snapshot_manifest")),
            base=collector.workspace,
        )
        digest = _digest(classification.get("snapshot_manifest_sha256"))
        collector.document(path, "profile", digest)
        profiles.append((path, digest, mode == "enrich"))
    for path, digest, required in profiles:
        load_profile(path, digest, require_acceptance=required)
    return dict(sorted(collector.dependencies.items()))


def collect_target_profile_runtime_files(
    path: Path, digest: str, *, on_file: Callable[[str, bytes], None] | None = None
) -> dict[str, str]:
    """Return the pinned files consumed by the classifier, relative to its profile."""
    path = path.resolve(strict=True)
    collector = _DependencyCollector(
        path.parent, include_acceptance_proofs=False, on_file=on_file
    )
    collector.document(path, "profile", digest)
    return dict(sorted(collector.dependencies.items()))


def verify_target_dependencies(workspace: Path, dependencies: dict[str, str]) -> None:
    """Refuse missing, external, redirected or changed dependency bytes."""
    root = _workspace(workspace)
    collector = _DependencyCollector(root)
    for reference, digest in dependencies.items():
        path = _local_path(root, reference, base=root)
        collector.add(path, _digest(digest))


def backup_target_dependencies(
    *, workspace: Path, dependencies: dict[str, str], destination: Path
) -> dict[str, str]:
    """Copy exact verified files under their original workspace-relative paths."""
    root = _workspace(workspace)
    target = _safe_path(root, destination)
    verify_target_dependencies(root, dependencies)
    sources = [
        (_local_path(root, name, base=root), _digest(digest))
        for name, digest in dependencies.items()
    ]
    if any(path.is_relative_to(target) for path, _ in sources):
        raise ValueError("target dependency backup overlaps its original inputs")
    backups: dict[str, str] = {}
    for source, digest in sources:
        copied = _safe_path(root, target / source.relative_to(root))
        _copy_verified(source, copied, root, digest)
        backups[copied.relative_to(root).as_posix()] = digest
    verify_target_dependencies(root, backups)
    verify_target_dependencies(root, dependencies)
    return dict(sorted(backups.items()))


def _copy_verified(
    source: Path, destination: Path, workspace: Path, expected: str
) -> None:
    _safe_path(workspace, source)
    raw = source.read_bytes()
    if _sha256(raw) != expected:
        raise ValueError("target dependency changed before backup")
    if destination.exists():
        if _sha256(destination.read_bytes()) != expected:
            raise ValueError(
                "target dependency backup already contains different bytes"
            )
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    _safe_path(workspace, destination)
    with destination.open("xb") as handle:
        handle.write(raw)


__all__ = [
    "backup_target_dependencies",
    "collect_target_dependencies",
    "verify_target_dependencies",
]
