"""Private isolated conversion worker. Receives an owner-private snapshot only."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
if not (sys.flags.isolated and sys.flags.no_site and len(sys.argv) == 2):
    raise SystemExit("Isolated converter requires exactly one snapshot")
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
from markitdown import MarkItDown, StreamInfo
from markitdown.converters import HtmlConverter

if source.suffix.lower() == ".html":
    # Use the HTML parser directly so content sniffing cannot select other converters.
    with source.open("rb") as stream:
        text = (
            HtmlConverter()
            .convert(stream, StreamInfo(extension=".html", mimetype="text/html"))
            .text_content
        )
else:
    text = MarkItDown(enable_plugins=False).convert(str(source)).text_content
output = text.encode("utf-8")
if len(output) > 1024 * 1024:
    raise SystemExit("Converter output exceeds bound")
sys.stdout.buffer.write(output)
sys.stdout.buffer.flush()
