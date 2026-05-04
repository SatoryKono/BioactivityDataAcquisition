import pathlib

root = pathlib.Path('E:/g-drive/05_AI/github/BioactivityDataAcquisition2')
for p in sorted(root.rglob('test_*.py')):
    try:
        loc = len(p.read_text(encoding='utf-8').splitlines())
        if loc > 2000:
            print(f'{p.relative_to(root)}: {loc} LOC')
    except Exception as e:
        print(f'Error reading {p}: {e}')
print('Done')
