"""Hash Docker-export contents on the trusted host, without extracting tar paths."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tarfile


def filesystem_records(stream):
    records = {}
    with tarfile.open(fileobj=stream, mode="r|") as archive:
        for entry in archive:
            name = entry.name.removeprefix("./").rstrip("/")
            if name in records:
                raise ValueError("Duplicate rootfs path: " + name)
            content = None
            if entry.isfile():
                digest = hashlib.sha256()
                source = archive.extractfile(entry)
                while chunk := source.read(1024 * 1024):
                    digest.update(chunk)
                content = digest.hexdigest()
            records[name] = [
                entry.type.decode("ascii"),
                entry.mode,
                entry.uid,
                entry.gid,
                entry.linkname,
                entry.devmajor,
                entry.devminor,
                content,
                {
                    key: value
                    for key, value in entry.pax_headers.items()
                    if key not in {"mtime", "atime", "ctime"}
                },
            ]
    if not records:
        raise ValueError("Empty rootfs export")
    return records


def fingerprint(stream):
    records = filesystem_records(stream)
    encoded = json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def canonical_image_reference(value: str) -> str:
    """Build Docker's positional operand from a fixed prefix and parsed digest."""
    if value == "bioetl-router-host:acceptance":
        return "bioetl-router-host:acceptance"
    match = re.fullmatch(
        r"(sha256:|satorykono/bioetl-grafana-router7-canvas@sha256:)([0-9a-f]{64})",
        value,
    )
    if match is None:
        raise ValueError("Unsupported image reference")
    digest = bytes.fromhex(match.group(2)).hex()
    if match.group(1) == "sha256:":
        return "sha256:" + digest
    return "satorykono/bioetl-grafana-router7-canvas@sha256:" + digest


def main(argv: list[str] | None = None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        raise ValueError("Unsupported image reference")
    image = canonical_image_reference(args[0])
    docker = (
        "C:/Program Files/Docker/Docker/resources/bin/docker.exe"
        if sys.platform == "win32"
        else "/usr/bin/docker"
    )
    container = subprocess.check_output(
        [docker, "create", "--entrypoint", "/bin/true", "--", image], text=True
    ).strip()
    if not re.fullmatch(r"[0-9a-f]{64}", container):
        raise ValueError("Invalid container ID")
    try:
        with subprocess.Popen(
            [docker, "export", container], stdout=subprocess.PIPE
        ) as process:
            try:
                result = fingerprint(process.stdout)
            except BaseException:
                process.kill()
                raise
            if process.wait() != 0:
                raise RuntimeError("Docker export failed")
        print(result)
    finally:
        subprocess.run(
            [docker, "rm", "-v", container], check=True, stdout=subprocess.DEVNULL
        )


if __name__ == "__main__":
    main()
