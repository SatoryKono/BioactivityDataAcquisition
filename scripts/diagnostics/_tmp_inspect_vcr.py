import yaml
from collections import Counter
from pathlib import Path

paths = [
    Path('tests/fixtures/vcr/chembl/test_chembl_assay_full_cycle.yaml'),
    Path('tests/fixtures/vcr/semanticscholar/TestSemanticScholarAdapterIntegration.test_fetch_with_query.yaml'),
]
for p in paths:
    data = yaml.safe_load(p.read_text(encoding='utf-8'))
    interactions = data.get('interactions', [])
    codes = Counter(i.get('response', {}).get('status', {}).get('code') for i in interactions)
    print(f"\n{p}: interactions={len(interactions)} codes={dict(codes)}")
    for idx, item in enumerate(interactions):
        uri = item.get('request', {}).get('uri', '')
        code = item.get('response', {}).get('status', {}).get('code')
        if 'chembl/api/data/assay' in uri and code == 500:
            print('  chembl500 idx', idx)
        if 'api.semanticscholar.org/graph/v1/paper/search' in uri and code == 429:
            print('  sem429 idx', idx, 'uri=', uri[:180])
