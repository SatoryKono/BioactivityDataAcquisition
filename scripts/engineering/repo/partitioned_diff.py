"""Scan every indexed path with bounded parallel native Git diff processes.

Pathspecs are literal and cover a disjoint partition of the complete index.
Index bytes are sampled again afterwards; missing or changing evidence refuses.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import os
import subprocess
import time


def partition(paths: tuple[bytes, ...], workers: int = 8) -> list[list[bytes]]:
    """Cover every path exactly once without traversing the working filesystem."""
    leaves: list[tuple[bytes, int]] = []

    def split(values: list[bytes], depth: int) -> None:
        groups: dict[bytes, list[bytes]] = {}
        for path in values:
            parts = path.split(b"/")
            key = b"/".join(parts[:depth])
            if len(parts) > depth:
                key += b"/"
            groups.setdefault(key, []).append(path)
        for prefix, children in groups.items():
            if len(children) > 64 and prefix.endswith(b"/"):
                split(children, depth + 1)
            else:
                leaves.append((prefix, len(children)))

    split(list(paths), 1)
    batches: list[list[bytes]] = [[] for _ in range(workers)]
    counts = [0] * workers
    for prefix, count in sorted(leaves, key=lambda item: (-item[1], item[0])):
        slot = min(range(workers), key=counts.__getitem__)
        batches[slot].append(prefix)
        counts[slot] += count
    return [sorted(batch) for batch in batches if batch]


def _git(args: list[str | bytes], deadline: float) -> bytes:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("source diff deadline exhausted")
    result = subprocess.run(
        ["git", "--literal-pathspecs", "-c", "core.fsmonitor=false", *args],
        env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"),
        capture_output=True,
        check=True,
        timeout=remaining,
    )
    return result.stdout


def _paths(index: bytes) -> tuple[bytes, ...]:
    paths = []
    for record in filter(None, index.split(b"\0")):
        metadata, separator, path = record.partition(b"\t")
        fields = metadata.split()
        if (
            not separator
            or len(fields) != 3
            or fields[0] not in {b"100644", b"100755", b"120000"}
            or fields[2] != b"0"
            or not path
            or path.startswith(b"/")
            or b".." in path.split(b"/")
        ):
            raise ValueError("source diff index is not qualified")
        paths.append(path)
    if len(set(paths)) != len(paths):
        raise ValueError("source diff index paths are ambiguous")
    return tuple(sorted(paths))


def scan() -> bytes:
    """Retain a ten-second total scan limit, including both index observations."""
    deadline = time.monotonic() + 10
    before = _git(["ls-files", "--stage", "-z"], deadline)
    batches = partition(_paths(before))

    def inspect(paths: list[bytes]) -> bytes:
        return _git(
            [
                "diff",
                "--no-ext-diff",
                "--no-textconv",
                "--ignore-submodules=none",
                "--",
                *paths,
            ],
            deadline,
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        patches = list(pool.map(inspect, batches))
    if _git(["ls-files", "--stage", "-z"], deadline) != before:
        raise ValueError("index changed during source diff")
    return b"".join(patches)
