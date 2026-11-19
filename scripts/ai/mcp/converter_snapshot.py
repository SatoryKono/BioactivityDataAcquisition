"""Snapshot the installed MarkItDown dependency closure without executing .pth files."""

from __future__ import annotations

import hashlib
import importlib.metadata
import io
import json
import os
import re
import shutil
import uuid
import zipfile
from pathlib import Path


CONVERTER_MANIFEST = "converter.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(root):
    raw = (root / CONVERTER_MANIFEST).read_bytes()
    manifest = json.loads(raw)
    if root.name != hashlib.sha256(raw).hexdigest() or manifest.get("schema") != 1:
        raise ValueError("Converter snapshot identity mismatch")
    actual = set()
    for current, directories, files in os.walk(root, followlinks=False):
        for name in [*directories, *files]:
            path = Path(current) / name
            if (
                getattr(path.lstat(), "st_file_attributes", 0) & 0x400
                or path.is_symlink()
            ):
                raise ValueError("Converter snapshot contains a reparse point")
        actual.update(
            (Path(current) / name).relative_to(root).as_posix()
            for name in files
            if Path(current) / name != root / CONVERTER_MANIFEST
        )
    if actual != set(manifest["files"]):
        raise ValueError("Converter snapshot file set changed")
    for relative, expected in manifest["files"].items():
        if (
            Path(relative).is_absolute()
            or ".." in Path(relative).parts
            or digest(root / relative) != expected
        ):
            raise ValueError("Converter snapshot dependency drift")
    return manifest


def closure(site, extras=()):
    """Resolve only installed, version-compatible dependencies for selected formats."""
    from packaging.requirements import Requirement

    def normalize(name):
        return re.sub(r"[-_.]+", "-", name).lower()

    installed = {
        normalize(d.metadata["Name"]): d
        for d in importlib.metadata.distributions(path=[str(site)])
    }
    pending = [("markitdown", set(extras))]
    selected = {}
    packages = {}
    while pending:
        name, extras = pending.pop()
        name = normalize(name)
        previous = selected.get(name)
        if previous is not None and extras <= previous:
            continue
        selected[name] = (previous or set()) | extras
        distribution = installed[name]
        packages[name] = distribution.version
        for requirement in _active_requirements(
            distribution, selected[name], Requirement
        ):
            _validate_requirement(requirement, installed, normalize)
            pending.append((requirement.name, set(requirement.extras)))
    return installed, selected, packages


def _active_requirements(distribution, extras, requirement_type):
    for raw in distribution.requires or []:
        requirement = requirement_type(raw)
        if requirement.marker is None or any(
            requirement.marker.evaluate({"extra": extra}) for extra in {"", *extras}
        ):
            yield requirement


def _validate_requirement(requirement, installed, normalize):
    name = normalize(requirement.name)
    if name not in installed:
        raise ValueError("Converter dependency missing: " + requirement.name)
    if requirement.specifier and installed[name].version not in requirement.specifier:
        raise ValueError("Converter dependency version mismatch: " + requirement.name)


def _copy_distribution(staging, site, distribution):
    for relative in distribution.files or []:
        _copy_package_file(staging, site, distribution, relative)


def _copy_package_file(staging, site, distribution, relative):
    source = Path(os.path.abspath(distribution.locate_file(relative)))
    if (
        not source.is_relative_to(site)
        or "__pycache__" in source.parts
        or source.suffix == ".pyc"
    ):
        return
    if source.name == ".env" or source.name.startswith(".env."):
        raise ValueError("Converter package contains an environment file")
    for component in reversed((source, *source.parents)):
        if component.is_symlink() or getattr(component, "is_junction", lambda: False)():
            raise ValueError("Converter package traverses a reparse path")
    if source.resolve(strict=True) != source:
        raise ValueError("Converter package path is not physical")
    target = staging / "site-packages" / source.relative_to(site)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    if digest(source) != digest(target):
        raise ValueError("Converter dependency changed during copying")


def _discard_staging(staging, destination):
    # Delete only this invocation's exclusive directory, after validating the
    # final absolute target and every reparse-sensitive child. Never glob caches.
    if (
        not staging.is_absolute()
        or staging.parent != destination
        or not staging.name.startswith("building-")
        or staging.resolve(strict=True) != staging
        or destination.resolve(strict=True) != destination
    ):
        raise ValueError("Staging cleanup escaped its owned destination")
    for current, directories, files in os.walk(staging, followlinks=False):
        for name in [*directories, *files]:
            path = Path(current) / name
            if (
                getattr(path.lstat(), "st_file_attributes", 0) & 0x400
                or path.is_symlink()
            ):
                raise ValueError("Staging cleanup encountered a reparse point")
    shutil.rmtree(staging)


def _build_snapshot(staging, destination, site, extras):
    installed, selected, packages = closure(site, extras)
    for name in selected:
        _copy_distribution(staging, site, installed[name])
    runner = Path(__file__).with_name("converter_runner.py")
    shutil.copyfile(runner, staging / "converter_runner.py")
    manifest = {
        "schema": 1,
        "packages": packages,
        "formats": sorted(extras),
        "files": {
            p.relative_to(staging).as_posix(): digest(p)
            for p in sorted(staging.rglob("*"))
            if p.is_file()
        },
    }
    raw = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    (staging / CONVERTER_MANIFEST).write_bytes(raw)
    target = destination / hashlib.sha256(raw).hexdigest()
    if not target.exists():
        try:
            staging.rename(target)
        except OSError:
            if not target.is_dir():
                raise
            # A parallel builder may have published the same content identity.
    verify(target)
    return target


def build(destination, site, extras=()):
    """Copy the installed closure; release only this invocation's temporary copy."""
    destination.mkdir(parents=True, exist_ok=True)
    if not destination.is_absolute() or destination.resolve(strict=True) != destination:
        raise ValueError("Converter destination is not physical")
    staging = destination / ("building-" + uuid.uuid4().hex)
    staging.mkdir()
    try:
        return _build_snapshot(staging, destination, site, extras)
    finally:
        if staging.exists():
            _discard_staging(staging, destination)


QUALIFICATION_TEXT = "BioETL converter qualification"
_PACKAGE_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_OFFICE_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _relationship(kind, target):
    return (
        f'<Relationships xmlns="{_PACKAGE_REL}"><Relationship Id="rId1" '
        f'Type="{_OFFICE_REL}/{kind}" Target="{target}"/></Relationships>'
    )


def _office_parts(extension):
    """Minimal synthetic Office documents; no project or user data is read."""
    if extension == ".docx":
        return (
            "word/document.xml",
            "wordprocessingml.document.main+xml",
            {
                "word/document.xml": (
                    '<w:document xmlns:w="http://schemas.openxmlformats.org/'
                    'wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>'
                    + QUALIFICATION_TEXT
                    + "</w:t></w:r></w:p></w:body></w:document>"
                )
            },
        )
    if extension == ".xlsx":
        return (
            "xl/workbook.xml",
            "spreadsheetml.sheet.main+xml",
            {
                "xl/workbook.xml": (
                    '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                    f'xmlns:r="{_OFFICE_REL}"><sheets><sheet name="Probe" '
                    'sheetId="1" r:id="rId1"/></sheets></workbook>'
                ),
                "xl/_rels/workbook.xml.rels": _relationship(
                    "worksheet", "worksheets/sheet1.xml"
                ),
                "xl/worksheets/sheet1.xml": (
                    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                    '<sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>'
                    + QUALIFICATION_TEXT
                    + "</t></is></c></row></sheetData></worksheet>"
                ),
            },
        )
    if extension == ".pptx":
        return (
            "ppt/presentation.xml",
            "presentationml.presentation.main+xml",
            {
                "ppt/presentation.xml": (
                    '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
                    f'xmlns:r="{_OFFICE_REL}"><p:sldIdLst><p:sldId id="256" r:id="rId1"/>'
                    '</p:sldIdLst><p:sldSz cx="9144000" cy="6858000"/></p:presentation>'
                ),
                "ppt/_rels/presentation.xml.rels": _relationship(
                    "slide", "slides/slide1.xml"
                ),
                "ppt/slides/slide1.xml": (
                    '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
                    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:cSld><p:spTree>'
                    '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
                    '<p:grpSpPr/><p:sp><p:nvSpPr><p:cNvPr id="2" name="Probe"/><p:cNvSpPr/>'
                    "<p:nvPr/></p:nvSpPr><p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t>"
                    + QUALIFICATION_TEXT
                    + "</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>"
                ),
            },
        )
    raise ValueError("No qualification document for this format")


def _office_sample(extension):
    main, content_type, parts = _office_parts(extension)
    content_types = {
        "xl/worksheets/sheet1.xml": "spreadsheetml.worksheet+xml",
        "ppt/slides/slide1.xml": "presentationml.slide+xml",
    }
    overrides = {main: content_type}
    overrides.update(
        {name: kind for name, kind in content_types.items() if name in parts}
    )
    parts["[Content_Types].xml"] = (
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        + "".join(
            f'<Override PartName="/{name}" ContentType="application/vnd.openxmlformats-officedocument.{kind}"/>'
            for name, kind in overrides.items()
        )
        + "</Types>"
    )
    parts["_rels/.rels"] = _relationship("officeDocument", main)
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, value in parts.items():
            archive.writestr(name, value)
    return stream.getvalue()


def _pdf_sample():
    content = f"BT /F1 12 Tf 50 750 Td ({QUALIFICATION_TEXT}) Tj ET".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(content)).encode()
        + b" >>\nstream\n"
        + content
        + b"\nendstream",
    ]
    raw = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, value in enumerate(objects, 1):
        offsets.append(len(raw))
        raw.extend(f"{index} 0 obj\n".encode() + value + b"\nendobj\n")
    start = len(raw)
    raw.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        raw.extend(f"{offset:010d} 00000 n \n".encode())
    raw.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n".encode()
    )
    return bytes(raw)


def qualification_sample(extension):
    """Return a bounded synthetic document containing the qualification marker."""
    if extension == ".html":
        return (
            "<!doctype html><html><body><p>" + QUALIFICATION_TEXT + "</p></body></html>"
        ).encode()
    if extension == ".pdf":
        return _pdf_sample()
    return _office_sample(extension)
