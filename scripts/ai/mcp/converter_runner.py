"""Private isolated conversion worker. Receives an owner-private snapshot only."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import zipfile
from pathlib import Path

HTML_EXTENSION = ".html"

sys.dont_write_bytecode = True
if not (sys.flags.isolated and sys.flags.no_site and len(sys.argv) == 2):
    raise SystemExit("Isolated converter requires exactly one snapshot")
nonce = os.environ.pop("PC_AGENT_MARKDOWNIFY_LAUNCH_NONCE", "")
if (
    len(nonce) != 64
    or any(char not in "0123456789abcdef" for char in nonce)
    or sys.stdin.buffer.readline(80) != (nonce + "\n").encode()
):
    raise SystemExit("Converter launch barrier was not authorized")
root = Path(__file__).resolve().parent
raw = (root / "converter.json").read_bytes()
if hashlib.sha256(raw).hexdigest() != root.name:
    raise SystemExit("Converter manifest mismatch")
manifest = json.loads(raw)
actual = set()
for current, directories, files in os.walk(root, followlinks=False):
    for name in [*directories, *files]:
        path = Path(current) / name
        if getattr(path.lstat(), "st_file_attributes", 0) & 0x400 or path.is_symlink():
            raise SystemExit("Converter path changed")
    actual.update(
        (Path(current) / name).relative_to(root).as_posix()
        for name in files
        if Path(current) / name != root / "converter.json"
    )
if actual != set(manifest["files"]):
    raise SystemExit("Converter file set changed")
for relative, expected in manifest["files"].items():
    if Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise SystemExit("Converter manifest path invalid")
    if hashlib.sha256((root / relative).read_bytes()).hexdigest() != expected:
        raise SystemExit("Converter dependency changed")
source = Path(sys.argv[1])
private = Path.home() / "AppData/Local/pc-agent/mcp-shared/markdownify-bioetl-v1"
if (
    not source.is_relative_to(private)
    or not source.parent.name.startswith("job-")
    or not source.name.startswith("input.")
    or source.resolve(strict=True) != source
):
    raise SystemExit("Converter requires an owner-private job snapshot")
sys.path.append(str(root / "site-packages"))
from markitdown import MarkItDown
from markitdown.converters import (
    DocxConverter,
    HtmlConverter,
    PdfConverter,
    PptxConverter,
    XlsxConverter,
)

converters = {
    HTML_EXTENSION: HtmlConverter,
    ".pdf": PdfConverter,
    ".docx": DocxConverter,
    ".pptx": PptxConverter,
    ".xlsx": XlsxConverter,
}
extension = source.suffix.lower()
permitted = {HTML_EXTENSION, *("." + item for item in manifest.get("formats", []))}
if extension not in permitted or extension not in converters:
    raise SystemExit("Converter snapshot format is not permitted")
if extension == HTML_EXTENSION and zipfile.is_zipfile(source):
    raise SystemExit("HTML snapshot contains a ZIP archive")
converter = MarkItDown(enable_builtins=False, enable_plugins=False)
converter.register_converter(converters[extension]())
text = converter.convert(str(source)).text_content
output = text.encode("utf-8")
if len(output) > 1024 * 1024:
    raise SystemExit("Converter output exceeds bound")
sys.stdout.buffer.write(output)
sys.stdout.buffer.flush()
