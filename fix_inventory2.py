import json
from collections import defaultdict
from pathlib import Path

from tests.helpers.git_index_scan import git_tracked_files

def main():
    _REPO = Path(".").resolve()
    _INV = _REPO / "reports" / "quality" / "test-basename-collision-inventory.json"
    payload = json.loads(_INV.read_text(encoding="utf-8"))

    by_base = defaultdict(list)
    for path in git_tracked_files(
        root=_REPO,
        paths=("tests",),
        suffixes=(".py",),
    ):
        if not path.name.startswith("test_"):
            continue
        by_base[path.name].append(path.relative_to(_REPO).as_posix())

    live_dups = {k: v for k, v in by_base.items() if len(v) > 1}
    payload["duplicate_basename_count"] = len(live_dups)
    payload["duplicate_basenames"] = live_dups

    _INV.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
