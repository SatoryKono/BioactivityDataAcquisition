"""Fix &nbsp; in sequence diagram participant/actor lines."""

import glob
import re


def fix_file(filepath: str) -> bool:
    with open(filepath, "r", encoding="utf-8") as fh:
        content = fh.read()

    if "sequenceDiagram" not in content:
        return False

    lines = content.split("\n")
    changed = False
    new_lines = []

    for line in lines:
        stripped = line.lstrip()
        if (
            stripped.startswith("participant ") or stripped.startswith("actor ")
        ) and "&nbsp;" in line:
            new_line = line.replace("&nbsp;", "").rstrip()
            # Clean up redundant 'as SameName' (e.g., 'participant CLI as CLI' -> 'participant CLI')
            m = re.match(r"^(\s*(?:participant|actor)\s+)(\w+)\s+as\s+\2\s*$", new_line)
            if m:
                new_line = m.group(1) + m.group(2)
            new_lines.append(new_line)
            if new_line != line:
                changed = True
        else:
            new_lines.append(line)

    if changed:
        with open(filepath, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(new_lines))
    return changed


fixed = []
for f in glob.glob("docs/02-architecture/mmd-diagrams/**/*.mmd", recursive=True):
    if fix_file(f):
        fixed.append(f)

print(f"Fixed {len(fixed)} files:")
for f in sorted(fixed):
    print(f"  {f}")
