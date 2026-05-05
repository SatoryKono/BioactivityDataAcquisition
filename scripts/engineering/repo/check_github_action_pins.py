#!/usr/bin/env python3
from __future__ import annotations
import re
from pathlib import Path

TARGETS=[Path('.github/workflows'),Path('.github/actions')]
USE_RE=re.compile(r'^(?P<i>\s*)uses:\s*(?P<a>[\w.-]+/[\w.-]+)@(?P<r>[^\s#]+)(?P<c>\s*#.*)?\s*$')
SHA_RE=re.compile(r'^[0-9a-f]{40}$')

def iter_files():
    for root in TARGETS:
        if root.exists():
            for p in root.rglob('*'):
                if p.suffix in {'.yml','.yaml'}:
                    yield p

def main()->int:
    errs=[]
    for fp in sorted(iter_files()):
        for n,line in enumerate(fp.read_text().splitlines(),1):
            m=USE_RE.match(line)
            if not m: continue
            ref=m.group('r'); comment=(m.group('c') or '').strip()
            if not SHA_RE.fullmatch(ref):
                errs.append(f"{fp}:{n} uses non-pinned ref '{ref}'")
                continue
            if not comment:
                errs.append(f"{fp}:{n} pinned SHA missing version comment")
    if errs:
        print('GitHub Action pin policy violations:')
        print('\n'.join(f'- {e}' for e in errs))
        return 1
    print('OK: all GitHub action uses are pinned to SHA with version comments.')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
