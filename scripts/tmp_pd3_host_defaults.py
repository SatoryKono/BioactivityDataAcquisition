#!/usr/bin/env python3
"""Inject cast(Any, None) defaults for unannotated-init host attrs; drop uninit flags."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "bioetl"
BP = ROOT / ".venv-win" / "Scripts" / "basedpyright.exe"

# Class body annotation without default: "    name: Type"
ANN = re.compile(
    r"^(?P<indent>[ \t]+)(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*:\s*(?P<type>[^=\n#]+?)\s*(?P<comment>#.*)?$"
)


def has_default(line: str) -> bool:
    # type annotation with default: name: T = ...
    return bool(re.search(r":\s*[^=#\n]+=", line))


def inject_defaults(text: str) -> str:
    lines = text.splitlines(True)
    out: list[str] = []
    in_class = False
    class_indent = ""
    needs_any_import = False
    for i, line in enumerate(lines):
        # track simple class body
        mclass = re.match(r"^([ \t]*)class\s+\w+", line)
        if mclass:
            in_class = True
            class_indent = mclass.group(1)
            out.append(line)
            continue
        if in_class:
            # leave class on dedent to same/less than class indent with non-empty
            if line.strip() and not line.startswith(class_indent + " ") and not line.startswith(class_indent + "\t"):
                if not line.startswith(class_indent):
                    in_class = False
            # still in class body methods reset - only inject before first def
        if in_class and line.lstrip().startswith("def ") or (
            in_class and line.lstrip().startswith("async def ")
        ):
            # after first method, stop injecting at class level for this class
            # keep in_class but only annotations before first method are host attrs
            pass

        if (
            in_class
            and not has_default(line)
            and not line.lstrip().startswith("def ")
            and not line.lstrip().startswith("async def ")
            and not line.lstrip().startswith("@")
            and not line.lstrip().startswith("class ")
        ):
            m = ANN.match(line.rstrip("\n"))
            if m and m.group("name") not in {"self", "cls"}:
                # only private/host-like attrs
                name = m.group("name")
                if name.startswith("_") or name in {
                    "logger",
                    "metrics",
                    "pipeline_name",
                    "provider_name",
                    "run_id",
                    "run_type",
                    "bronze",
                    "silver",
                    "gold",
                    "base_path",
                    "config",
                    "storage",
                }:
                    indent = m.group("indent")
                    typ = m.group("type").strip()
                    comment = m.group("comment") or ""
                    # skip Protocol method ellipsis bodies etc
                    if typ.endswith("..."):
                        out.append(line)
                        continue
                    new = f"{indent}{name}: {typ} = cast(Any, None)  # host attr default (PD3)\n"
                    if comment and "host attr" not in comment:
                        new = f"{indent}{name}: {typ} = cast(Any, None)  # host attr default (PD3) {comment[1:].strip()}\n"
                    out.append(new)
                    needs_any_import = True
                    continue
        out.append(line)

    text2 = "".join(out)
    if needs_any_import and "cast(Any, None)" in text2:
        if "from typing import" in text2 and "Any" not in text2.split("from typing import", 1)[1].split("\n", 1)[0]:
            text2 = re.sub(
                r"from typing import ([^\n]+)",
                lambda m: (
                    m.group(0)
                    if "Any" in m.group(1) and "cast" in m.group(1)
                    else f"from typing import Any, cast, {m.group(1)}"
                    if "cast" not in m.group(1) and "Any" not in m.group(1)
                    else f"from typing import Any, {m.group(1)}"
                    if "Any" not in m.group(1)
                    else f"from typing import cast, {m.group(1)}"
                ),
                text2,
                count=1,
            )
        elif "from typing import" not in text2:
            # after future
            if "from __future__ import annotations" in text2:
                text2 = text2.replace(
                    "from __future__ import annotations\n",
                    "from __future__ import annotations\n\nfrom typing import Any, cast\n",
                    1,
                )
            else:
                text2 = "from typing import Any, cast\n" + text2
    return text2


def strip_uninit_directive(text: str) -> str:
    lines = []
    for line in text.splitlines(True):
        if line.lstrip().startswith("# pyright:") and "reportUninitializedInstanceVariable=false" in line:
            body = line.split("pyright:", 1)[1]
            others = [
                p.strip()
                for p in re.split(r"[, ]+", body)
                if p.strip().startswith("report")
                and "reportUninitializedInstanceVariable" not in p
            ]
            if others:
                lines.append(f"# pyright: {', '.join(others)}\n")
            continue
        lines.append(line)
    return "".join(lines)


def bp_errors(path: Path) -> int:
    try:
        completed = subprocess.run(
            [str(BP), str(path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
    except Exception:
        return 999
    text = (completed.stdout or "") + "\n" + (completed.stderr or "")
    for line in reversed(text.splitlines()):
        if "error" in line and "warning" in line:
            m = re.search(r"(\d+)\s+errors?", line)
            if m:
                return int(m.group(1))
    return 0 if completed.returncode == 0 else 999


def main() -> None:
    # candidate files with uninit flag
    changed = 0
    for path in SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "reportUninitializedInstanceVariable=false" not in text:
            continue
        # only mixins/support-ish
        rel = str(path.relative_to(SRC)).replace("\\", "/")
        if not any(
            x in rel
            for x in (
                "mixin",
                "support",
                "facade",
                "runner",
                "observer",
                "postrun",
                "batch_writer",
                "aggregates/_",
                "storage/",
                "adapters/",
            )
        ):
            continue
        original = text
        updated = inject_defaults(text)
        updated = strip_uninit_directive(updated)
        if updated == original:
            continue
        path.write_text(updated, encoding="utf-8")
        err = bp_errors(path)
        if err == 0:
            print(f"OK {rel}")
            changed += 1
        else:
            path.write_text(original, encoding="utf-8")
            print(f"REVERT {rel} errors={err}")
    print(f"changed_ok={changed}")


if __name__ == "__main__":
    main()
