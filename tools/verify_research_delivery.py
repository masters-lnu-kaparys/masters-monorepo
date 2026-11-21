"""Read-only integrity/numeric verification. Never fits or rewrites research files."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]

def verify():
    manifest = json.loads((ROOT/'docs/research/adaptive-sampling/phase4-delivery-artifacts.json').read_text(encoding='utf-8'))
    failures = []
    for name, expected in manifest['files'].items():
        p = ROOT/name
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != expected:
            failures.append(name)
    if failures:
        raise ValueError('Frozen artifacts missing or modified: ' + ', '.join(failures))
    import numpy as np
    results = json.loads((ROOT/'.codex-work/parking-final-display-v02-20261025/results.json').read_text(encoding='utf-8'))
    count = 0
    for label, cohort in results['cohorts'].items():
        a = np.load(ROOT/'.codex-work/parking-final-display-v02-20261025'/label/'policy-bay-counters.npz')
        for i, name in enumerate(a['names']):
            policy = cohort['policies'][str(name)]
            np.testing.assert_array_equal(a['primary'][i].sum(axis=0), policy['primary_raw'])
            np.testing.assert_allclose(a['expected'][i].sum(axis=0), policy['expected_raw'], rtol=0, atol=1e-4)
            count += 1
    print(json.dumps({'frozen_files':len(manifest['files']), 'policy_cohort_sums':count,
                      'passed':True,'refitted':False,'new_independent_experiment':False}))

if __name__ == '__main__':
    try: verify()
    except Exception as error:
        print(str(error),file=sys.stderr)
        sys.exit(1)
