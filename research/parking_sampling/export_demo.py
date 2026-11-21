"""Export a small, reproducible application demo without refitting phase 4.

Examples are chosen from locked window metadata, never by a performance score.
The browser policy receives only a sampled observation. Recorded intervals belong
to the replay simulator and the comparison plot, not the policy interface.
"""
from bisect import bisect_right
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np

from calibrated_schedule import CalibratedSchedule
from frozen_local_priors import apply_frozen_priors
from local_risk import ACTIONS, make_tables
from phase4_pipeline import ROOT, WORK, CAL, CATALOG, frozen_lock, load_final_bundle
from simulation import Observation, reference_simulate


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def verify_delivery():
    manifest = json.loads((ROOT / 'docs/research/adaptive-sampling/results-checksums.json').read_text(encoding='utf-8'))
    frozen = {name: expected for name, expected in manifest['files'].items() if not name.startswith('frontend/')}
    for name, expected in frozen.items():
        if digest(ROOT / name) != expected:
            raise RuntimeError('Frozen research artifact changed: ' + name)
    if digest(WORK / 'results.json') != frozen['docs/research/adaptive-sampling/phase4-display-results.json']:
        raise RuntimeError('The workspace results differ from the published experiment')
    return len(frozen) + 1


def clip_metrics(segments, decisions, start, end):
    """Independent interval intersections for a cropped, history-initialized trace."""
    f = o = 0
    for i, (time, state, *_rest) in enumerate(decisions):
        a = max(start, time)
        b = min(end, decisions[i + 1][0] if i + 1 < len(decisions) else end)
        for segment in segments:
            if state == segment['state']:
                continue
            length = max(0, min(b, segment['end']) - max(a, segment['start']))
            if state == 0:
                f += length
            else:
                o += length
    return {'calls': sum(start <= row[0] < end for row in decisions), 'falseFreeSeconds': f, 'falseOccupiedSeconds': o}


def main():
    checked = verify_delivery()
    data = load_final_bundle(frozen_lock(), primary_only=True)
    catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
    weights = catalog['policies']['author']['weights']
    train = np.load(WORK / 'local-training-statistics.npz')
    local_lookup = {int(b): i for i, b in enumerate(train['bays'])}
    rank = sorted(range(len(data.starts)), key=lambda i: hashlib.sha256(f'phase4-illustration:{data.window_ids[i]}'.encode()).digest())
    selected = [rank[0]]
    selected_bays = {int(data.bays[data.bay_indexes[rank[0]]])}
    for needs_history in (True, False):
        candidate = next(i for i in rank if int(data.bays[data.bay_indexes[i]]) not in selected_bays
                         and (int(data.bays[data.bay_indexes[i]]) in local_lookup) == needs_history)
        selected.append(candidate)
        selected_bays.add(int(data.bays[data.bay_indexes[candidate]]))

    priors = np.load(CAL / 'shared-priors.npz')
    risk_by_bay = {}
    for bay in selected_bays:
        if bay in local_lookup:
            i = local_lookup[bay]
            risk = apply_frozen_priors(train['n'][i:i + 1], train['cost'][i:i + 1], priors['state'], priors['context'], 500)[0]
            risk_by_bay[str(bay)] = risk.tolist()

    policy = {'schema_version': 1, 'allocation_seed': 20261025,
              'observed_run_edges_seconds': [60, 300, 900, 3600, 14400],
              'component_weights': weights, 'components': {}}
    for name in weights:
        definition = catalog['components'][name]
        frozen = np.load(WORK / 'models' / (name + '.npz'))
        index = {int(b): i for i, b in enumerate(frozen['bays'])}
        fallback = make_tables(priors['context'][None], definition['lambda_F'], definition['lambda_O'])[0]
        tables = {}
        for bay in sorted(selected_bays):
            stored = frozen['tables'][index[bay]]
            risk = np.asarray(risk_by_bay.get(str(bay), priors['context']))
            np.testing.assert_array_equal(make_tables(risk[None], definition['lambda_F'], definition['lambda_O'])[0], stored)
            if bay in local_lookup:
                tables[str(bay)] = stored.tolist()
            else:
                np.testing.assert_array_equal(fallback, stored)
        policy['components'][name] = {'bay_tables': tables, 'pooled_fallback': fallback.tolist(),
                                      'lambdaF': definition['lambda_F'], 'lambdaO': definition['lambda_O']}

    runtime = CalibratedSchedule(policy)
    initial, _ = data.phases(10)
    scenarios = []
    golden = {'assignments': [[int(bay), runtime.component_for_bay(int(bay))] for bay in data.bays], 'contexts': [], 'scenarios': []}
    for w in selected:
        bay = int(data.bays[data.bay_indexes[w]])
        lo, hi = data.offsets[w:w + 2]
        ends, states = data.ends[lo:hi], data.states[lo:hi]
        start = int(data.starts[w] + initial[w, 0])
        changes = ends[:-1][ends[:-1] >= start + 300]
        center = int(changes[0]) if len(changes) else start + 300
        left = max(start, center - 120)
        right = min(int(ends[-1]), left + 720)
        cut = int(np.searchsorted(ends, right, side='left'))
        cropped_ends = np.r_[ends[:cut], right]
        cropped_states = states[:cut + 1]
        _raw, _hist, author = reference_simulate(cropped_ends, cropped_states, start, lambda obs: (runtime.next_pause(bay, obs), False))
        _raw, _hist, fixed = reference_simulate(cropped_ends, cropped_states, start, lambda obs: (60, False))
        author = author[max(0, bisect_right([d[0] for d in author], left) - 1):]
        fixed = fixed[max(0, bisect_right([d[0] for d in fixed], left) - 1):]
        segments = []
        point = left
        while point < right:
            i = int(np.searchsorted(ends, point, side='right'))
            edge = min(right, int(ends[i]))
            segments.append({'start': point, 'end': edge, 'state': int(states[i])})
            point = edge
        def observation(row):
            return {'time': row[0], 'state': row[1], 'observedRunStart': row[2]}
        scenario = {'id': data.window_ids[w], 'bayId': bay, 'startTime': left, 'endTime': right,
                    'dateLocal': datetime.fromtimestamp(left, timezone.utc).strftime('%Y-%m-%d'),
                    'hasLocalHistory': bay in local_lookup, 'segments': segments,
                    'initial': {'author': observation(author[0]), 'fixed': observation(fixed[0])}}
        scenarios.append(scenario)
        golden['scenarios'].append({'id': scenario['id'],
                                   'author': [list(row[:4]) for row in author], 'fixed': [list(row[:4]) for row in fixed],
                                   'metrics': {'author': clip_metrics(segments, author, left, right),
                                               'fixed': clip_metrics(segments, fixed, left, right)}})
    # Age boundaries, clock bins, known histories and unseen-location fallback.
    for bay in [*sorted(selected_bays), 999999999]:
        for state in (0, 1):
            for clock_bin in range(4):
                for age in (0, 59, 60, 299, 300, 899, 900, 3599, 3600, 14399, 14400, 14401):
                    time = 1575158400 + clock_bin * 21600
                    obs = Observation(time, state, time - age)
                    golden['contexts'].append([bay, time, state, time - age, runtime.next_pause(bay, obs)])

    results = json.loads((WORK / 'results.json').read_text(encoding='utf-8'))['cohorts']['primary_7_days']['policies']
    payload = {'schemaVersion': 1, 'source': {'title': 'City of Melbourne, On-street Car Parking Sensor Data - 2019',
                'url': 'https://data.melbourne.vic.gov.au/explore/dataset/on-street-car-parking-sensor-data-2019/information/',
                'license': 'CC BY 4.0', 'clock': 'Melbourne civil timestamps; epoch values are labels, not UTC instants',
                'selection': 'First SHA256-ranked window, first distinct local-history bay, first distinct fallback bay; no outcome filter'},
               'policy': policy, 'actions': ACTIONS.tolist(),
               'risk': {'byBay': risk_by_bay, 'pooled': priors['context'].tolist()}, 'scenarios': scenarios,
               'study': {'bayCount': 867, 'author': results['author']['primary_metrics'],
                         'fixed': results['fixed_60']['primary_metrics'],
                         'missedMinuteEpisodesPercent': 100 * 6562 / 3245755}}
    asset = ROOT / 'frontend/public/data/sampling-demo.json'
    expected = ROOT / 'frontend/tests/fixtures/sampling-demo-golden.json'
    save(asset, payload)
    save(expected, golden)
    verified = verify_delivery()
    manifest = {'createdOn': '2026-11-01', 'frozenArtifactsVerified': verified,
                'researchRefitted': False, 'independentNewEffectEstimate': False,
                'frozenResultsSha256': digest(WORK / 'results.json'),
                'exporterSha256': digest(Path(__file__)),
                'files': {str(p.relative_to(ROOT).as_posix()): digest(p) for p in (asset, expected)},
                'selection': payload['source']['selection'],
                'scenarios': [{'id': s['id'], 'bayId': s['bayId'], 'hasLocalHistory': s['hasLocalHistory']} for s in scenarios],
                'verificationVectors': {'assignments': len(golden['assignments']), 'contexts': len(golden['contexts']),
                                        'traces': len(golden['scenarios'])}}
    save(ROOT / 'docs/research/adaptive-sampling/phase5-demo-export.json', manifest)
    print(json.dumps({'assets': str(asset.relative_to(ROOT)), 'scenarios': manifest['scenarios'],
                      'goldenVectors': manifest['verificationVectors'], 'frozenFilesUnchanged': checked == verified}, ensure_ascii=False))


if __name__ == '__main__':
    main()
