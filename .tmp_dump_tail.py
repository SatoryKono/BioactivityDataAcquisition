from pathlib import Path
p=Path('E:/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/infrastructure/adapters/chembl/fetch_resilience_mixin.py')
lines=p.read_text(encoding='utf-8').splitlines()
print('len',len(lines))
for i in range(330, min(len(lines), 380)):
    print(f'{i+1:4d}: {lines[i]}')
