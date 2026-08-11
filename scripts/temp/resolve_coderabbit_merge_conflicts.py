"""Resolve merge conflicts under reports/quality/coderabbit/20260811/.

Strategy:
- review_*.log (both added): keep the larger side; if equal keep ours (HEAD).
- BLOCKERS.md: union sections from both sides (dedupe by heading).
- progress.json: deep-merge results by scope id; prefer status=ok, else larger bytes.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def git_show(stage: int, path: str) -> bytes:
    proc = subprocess.run(
        ["git", "show", f":{stage}:{path}"],
        cwd=ROOT,
        capture_output=True,
    )
    return proc.stdout if proc.returncode == 0 else b""


def unmerged_paths() -> list[str]:
    out = subprocess.check_output(
        ["git", "diff", "--name-only", "--diff-filter=U"],
        cwd=ROOT,
        text=True,
    )
    return [line.strip() for line in out.splitlines() if line.strip()]


def resolve_log(path: str) -> bytes:
    ours = git_show(2, path)
    theirs = git_show(3, path)
    if not ours and theirs:
        return theirs
    if ours and not theirs:
        return ours
    # Prefer non-trivial content; connection-failure stubs are short.
    if len(theirs) > len(ours):
        return theirs
    return ours


_SECTION_RE = re.compile(r"(?m)^## .+")


def resolve_blockers(path: str) -> str:
    ours = git_show(2, path).decode("utf-8", "replace")
    theirs = git_show(3, path).decode("utf-8", "replace")
    # Strip conflict markers if present in working tree fallback
    for text in (ours, theirs):
        if "<<<<<<<" in text:
            # should not happen in stage blobs
            pass

    def sections(text: str) -> tuple[str, list[tuple[str, str]]]:
        matches = list(_SECTION_RE.finditer(text))
        if not matches:
            return text.strip(), []
        preamble = text[: matches[0].start()].strip()
        parts: list[tuple[str, str]] = []
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[start:end].strip()
            heading = m.group(0).strip()
            parts.append((heading, body))
        return preamble, parts

    pre_o, sec_o = sections(ours)
    pre_t, sec_t = sections(theirs)
    preamble = pre_o or pre_t
    by_heading: dict[str, str] = {}
    order: list[str] = []
    for heading, body in sec_o + sec_t:
        if heading not in by_heading:
            by_heading[heading] = body
            order.append(heading)
        else:
            # keep longer body
            if len(body) > len(by_heading[heading]):
                by_heading[heading] = body
    chunks = [preamble] if preamble else []
    chunks.extend(by_heading[h] for h in order)
    return "\n\n".join(chunks).rstrip() + "\n"


def _prefer_result(a: dict, b: dict) -> dict:
    """Prefer successful / richer campaign result."""
    sa = str(a.get("status", ""))
    sb = str(b.get("status", ""))
    if sa == "ok" and sb != "ok":
        return a
    if sb == "ok" and sa != "ok":
        return b
    ba = int(a.get("bytes") or 0)
    bb = int(b.get("bytes") or 0)
    if bb > ba:
        return b
    if ba > bb:
        return a
    # Prefer later elapsed or non-empty reason details from ours by default
    return a


def resolve_progress(path: str) -> str:
    ours = json.loads(git_show(2, path).decode("utf-8") or "{}")
    theirs = json.loads(git_show(3, path).decode("utf-8") or "{}")
    merged: dict = {}
    # Prefer non-empty scalar fields from the side that has more results
    o_results = ours.get("results") or {}
    t_results = theirs.get("results") or {}
    base = theirs if len(t_results) > len(o_results) else ours
    other = ours if base is theirs else theirs
    for key in ("campaign", "base_sha", "started_utc", "finished_utc", "notes"):
        merged[key] = base.get(key) or other.get(key)
    # Merge all top-level keys except results
    for src in (other, base):
        for k, v in src.items():
            if k == "results":
                continue
            if k not in merged or merged[k] in (None, "", {}, []):
                merged[k] = v
    results: dict[str, dict] = {}
    for src in (o_results, t_results):
        for scope_id, payload in src.items():
            if not isinstance(payload, dict):
                continue
            if scope_id not in results:
                results[scope_id] = payload
            else:
                results[scope_id] = _prefer_result(results[scope_id], payload)
    merged["results"] = dict(sorted(results.items()))
    # Recompute simple counters if present
    if "completed" in ours or "completed" in theirs or "counts" in merged:
        statuses: dict[str, int] = {}
        for payload in results.values():
            st = str(payload.get("status") or "unknown")
            statuses[st] = statuses.get(st, 0) + 1
        merged["counts"] = {
            "scopes": len(results),
            "by_status": dict(sorted(statuses.items())),
        }
    return json.dumps(merged, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    paths = unmerged_paths()
    if not paths:
        print("No unmerged paths")
        return 0
    resolved: list[str] = []
    for path in paths:
        abs_path = ROOT / path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        if path.endswith("BLOCKERS.md"):
            abs_path.write_text(resolve_blockers(path), encoding="utf-8")
        elif path.endswith("progress.json"):
            abs_path.write_text(resolve_progress(path), encoding="utf-8")
        elif path.endswith(".log"):
            abs_path.write_bytes(resolve_log(path))
        else:
            # default: ours
            data = git_show(2, path) or git_show(3, path)
            abs_path.write_bytes(data)
        resolved.append(path)
        print(f"resolved {path}")
    subprocess.check_call(["git", "add", "--", *resolved], cwd=ROOT)
    remaining = unmerged_paths()
    print(f"resolved_count={len(resolved)} remaining={len(remaining)}")
    if remaining:
        print("REMAINING:", *remaining, sep="\n  ")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
