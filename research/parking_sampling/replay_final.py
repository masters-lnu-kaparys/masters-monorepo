"""Re-evaluate the held-out windows with the published, frozen parameters."""
import argparse
import json
from pathlib import Path

import duckdb
import numpy as np

from data_access import Bundle
from phase4_analysis import metric_summary, paired_intervals, success_gate
from phase4_pipeline import CATALOG, COHORT, aggregate_components, evaluate_component
from prepare_data import DOCS, sha256

RESULTS = Path(__file__).resolve().parent / 'results'
FINAL_ROLE = 'quarantine_final_test'


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def read_final_partition(prepared):
    manifest = read_json(prepared / 'data-manifest.json')
    original = read_json(DOCS / 'phase2-data-lock.json')['data_preparation']
    for key in ('source_archive_sha256', 'source_csv_sha256', 'protocol_sha256', 'preparation_code_sha256'):
        if manifest[key] != original[key]:
            raise ValueError(f'Prepared data differ from the original experiment: {key}')
    path = prepared / f'{FINAL_ROLE}.parquet'
    partition_hash = sha256(path)
    if partition_hash != manifest['files'][FINAL_ROLE]['sha256']:
        raise ValueError('Final partition differs from its preparation manifest')
    return path, partition_hash


def load_windows(path, partition_hash, cohort, primary):
    ids_key = 'primary_window_ids' if primary else 'sensitivity_window_ids'
    with duckdb.connect(config={'memory_limit': '1GB', 'threads': '2'}) as conn:
        rows = conn.execute(
            """SELECT bay, window_id, window_start, end_local_seconds, state
            FROM read_parquet(?)
            WHERE bay IN (SELECT unnest(?::BIGINT[])) AND (is_primary OR NOT ?)
            ORDER BY bay, window_start, start_local_seconds""",
            [str(path), cohort['bay_ids'], primary],
        ).fetchnumpy()
    changes = np.r_[True, rows['window_id'][1:] != rows['window_id'][:-1]]
    offsets = np.r_[np.flatnonzero(changes), len(rows['bay'])].astype(np.int64)
    starts = offsets[:-1]
    bays = np.unique(rows['bay']).astype(np.int64)
    np.testing.assert_array_equal(bays, cohort['bay_ids'])
    window_ids = tuple(rows['window_id'][starts])
    if sorted(window_ids) != sorted(cohort[ids_key]):
        raise ValueError('Prepared windows differ from the frozen cohort')
    return Bundle(
        rows['end_local_seconds'].astype(np.int64), rows['state'].astype(np.int8),
        offsets, rows['window_start'][starts].astype(np.int64),
        np.searchsorted(bays, rows['bay'][starts]).astype(np.int64), bays, window_ids,
        {FINAL_ROLE: partition_hash},
    )


def replay(workdir):
    path, partition_hash = read_final_partition(workdir / 'prepared')
    cohort = read_json(COHORT)
    catalog = read_json(CATALOG)
    reports = read_json(DOCS / 'phase4-display-results.json')['cohorts']
    policy_names = list(catalog['policies'])
    candidate_idx = policy_names.index('author')
    reference_idx = policy_names.index('fixed_60')
    count = 0
    with np.load(RESULTS / 'models.npz') as models:
        names = list(catalog['components'])
        np.testing.assert_array_equal(models['names'], names)
        tables, cdfs, kinds = models['tables'], models['cdfs'], models['kinds']
        for primary_only, label in ((True, 'primary_7_days'), (False, 'sensitivity_1_day')):
            data = load_windows(path, partition_hash, cohort, primary_only)
            np.testing.assert_array_equal(models['bays'], data.bays)
            values, histograms = [], []
            for i, name in enumerate(names):
                policy_id = name if catalog['components'][name]['kind'] == 'S2' else 'deterministic'
                initial, seeds = data.phases(10, policy_id=policy_id)
                by_bay_phase, histogram = evaluate_component(
                    data.ends, data.states, data.offsets, data.starts, data.bay_indexes,
                    initial, seeds, tables[i], cdfs[i], int(kinds[i]), len(data.bays),
                )
                values.append(by_bay_phase.sum(axis=1))
                histograms.append(histogram)
            values, histograms = np.asarray(values), np.asarray(histograms)
            with np.load(RESULTS / f'{label}.npz') as frozen:
                np.testing.assert_array_equal(frozen['names'], policy_names)
                np.testing.assert_array_equal(frozen['bays'], data.bays)
                expected_counters, primary_counters = frozen['expected'], frozen['primary']
                report = reports[label]
                for i, (name, policy) in enumerate(catalog['policies'].items()):
                    expected, _, primary, histogram, assignments = aggregate_components(
                        values, histograms, data.bays, names, policy['weights'], catalog['allocation_seed'],
                    )
                    np.testing.assert_array_equal(primary, primary_counters[i])
                    np.testing.assert_allclose(expected, expected_counters[i], rtol=0, atol=1e-7)
                    published = report['policies'][name]
                    np.testing.assert_array_equal(assignments, published['primary_allocation'])
                    if metric_summary(primary.sum(axis=0), histogram.sum(axis=0)) != published['primary_metrics']:
                        raise ValueError(f'{label}: published metrics differ for {name}')
                    count += 1

                candidate, reference = primary_counters[[candidate_idx, reference_idx]]
                intervals = paired_intervals(candidate, reference)
                published_intervals = report['author_vs_fixed60_intervals']
                for interval_type in ('pointwise95', 'bonferroni_joint3_approx95'):
                    for metric, bounds in intervals[interval_type].items():
                        np.testing.assert_allclose(
                            bounds, published_intervals[interval_type][metric], rtol=0, atol=1e-9,
                        )
                if success_gate(candidate.sum(axis=0), reference.sum(axis=0), intervals) != report['success']:
                    raise ValueError(f'{label}: the published success criteria do not match')
            print(f'{label}: all {len(catalog["policies"])} policies match at bay level', flush=True)
    print(f'{count} policy and window-set combinations reproduced')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workdir', type=Path, required=True, help='Output directory from prepare_data.py')
    replay(parser.parse_args().workdir.resolve())
