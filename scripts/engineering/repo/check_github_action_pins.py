#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

TARGETS = [Path('.github/workflows'), Path('.github/actions')]
USE_RE = re.compile(
    r'^(?P<i>\s*)uses:\s*(?P<a>[\w.-]+/[\w.-]+)@(?P<r>[^\s#]+)(?P<c>\s*#.*)?\s*$'
)
SHA_RE = re.compile(r'^[0-9a-f]{40}$')


def iter_files() -> list[Path]:
    files: list[Path] = []
    for root in TARGETS:
        if root.exists():
            for path in root.rglob('*'):
                if path.suffix in {'.yml', '.yaml'}:
                    files.append(path)
    return files


def main() -> int:
    errs: list[str] = []
    for filepath in sorted(iter_files()):
        for line_no, line in enumerate(filepath.read_text().splitlines(), 1):
            match = USE_RE.match(line)
            if not match:
                continue
            ref = match.group('r')
            comment = (match.group('c') or '').strip()
            if not SHA_RE.fullmatch(ref):
                errs.append(f"{filepath}:{line_no} uses non-pinned ref '{ref}'")
                continue
            if not comment:
                errs.append(f'{filepath}:{line_no} pinned SHA missing version comment')
    if errs:
        print('GitHub Action pin policy violations:')
        print('\n'.join(f'- {err}' for err in errs))
        return 1
    print('OK: all GitHub action uses are pinned to SHA with version comments.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
