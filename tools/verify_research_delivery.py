"""Check the published research files and re-sum the frozen per-bay counters."""
from pathlib import Path
import hashlib
import json

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs/research/adaptive-sampling'
RESULTS = ROOT / 'research/parking_sampling/results'


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def verify():
    files = read_json(DOCS / 'results-checksums.json')['files']
    failures = [
        name for name, expected in files.items()
        if not (ROOT / name).is_file() or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected
    ]
    if failures:
        raise ValueError('Frozen artifacts missing or modified: ' + ', '.join(failures))

    results = read_json(DOCS / 'phase4-display-results.json')
    cohort_ids = read_json(DOCS / 'phase4-display-cohort.json')['bay_ids']
    count = 0
    for label, cohort in results['cohorts'].items():
        with np.load(RESULTS / f'{label}.npz') as arrays:
            policies = cohort['policies']
            np.testing.assert_array_equal(arrays['bays'], cohort_ids)
            np.testing.assert_array_equal(arrays['names'], list(policies))
            primary, expected = arrays['primary'], arrays['expected']
            for i, policy in enumerate(policies.values()):
                np.testing.assert_array_equal(primary[i].sum(axis=0), policy['primary_raw'])
                np.testing.assert_allclose(expected[i].sum(axis=0), policy['expected_raw'], rtol=0, atol=1e-4)
                count += 1

    print(json.dumps({'checked_files': len(files), 'policy_cohort_sums': count, 'passed': True}))


if __name__ == '__main__':
    verify()
