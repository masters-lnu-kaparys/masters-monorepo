"""Validate and freeze C5 without rewriting any earlier evidence receipt."""
import io
import json
import re
import sys
import unittest
from urllib.parse import unquote
from pathlib import Path
import numpy as np
from PIL import Image
from prepare_data import ROOT,DOCS,sha256
from data_access import load_bundle
from fit_history_scheduler import WORK,read,select_rows
from history_certificate import history_bound_bundle
from run_phase3 import write_json


def main():
    modules=('test_prepare_data','test_methods','test_refinement','test_novelty_audit','test_episode_pair_certificate',
             'test_stability_audit','test_history_certificate','test_history_scheduler')
    stream=io.StringIO()
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n) for n in modules)
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    receipt={'created_on':'2026-10-25','tests_run':result.testsRun,'passed':result.wasSuccessful(),
      'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
      'test_sha256':{n+'.py':sha256(Path(__file__).parent/(n+'.py')) for n in modules},'test_log':stream.getvalue(),
      'previous_receipts_preserved':True,'final_test_read':False}
    write_json(DOCS/'phase3-history-scheduler-verification.json',receipt)
    if not result.wasSuccessful():
        print(stream.getvalue());sys.exit(1)
    assert result.testsRun==76
    mappings=list(read(DOCS/'phase3-stability-history.json')['historical_file_mapping'])
    for original,snapshot in [('docs/research/adaptive-sampling/README.md','README-before-C5.md'),
       ('docs/research/adaptive-sampling/phase3-novelty-gate.json','phase3-novelty-gate-before-C5.json')]:
        path=WORK/'history'/snapshot
        mappings.append({'original_path':original,'snapshot_path':path.relative_to(ROOT).as_posix(),
          'snapshot_sha256':sha256(path),'reason':'C5 construction result and new tuning128 witness; old status retained exactly'})
    def check(relative,expected):
        path=ROOT/relative
        if path.exists() and sha256(path)==expected:return 'unchanged'
        for m in mappings:
            if m['original_path']==relative and m['snapshot_sha256']==expected:
                assert sha256(ROOT/m['snapshot_path'])==expected
                return 'snapshot'
        raise AssertionError('Unexplained change to frozen file: '+relative)
    prior={};snapshots=0
    for name in ('phase3-artifact-manifest.json','phase3-method-lock.json','phase3-refinement-lock.json',
                 'phase3-novelty-artifacts.json','phase3-stability-artifacts.json'):
        lock=read(DOCS/name)
        for relative,h in lock['files'].items():snapshots+=check(relative,h)=='snapshot'
        prior[name]=len(lock['files'])
    lock=read(WORK/'pre-fit-lock.json')
    check('docs/research/adaptive-sampling/phase3-history-scheduler-plan.json',lock['plan_sha256'])
    for name,h in lock['code_sha256'].items():check('research/parking_sampling/'+name,h)
    experiment=read(WORK/'results.json');frozen=read(WORK/'candidate-lock-before-replay.json')
    assert experiment['candidate_lock_sha256']==sha256(WORK/'candidate-lock-before-replay.json')
    assert frozen['calibration_sha256']==sha256(WORK/'calibration.json')
    assert frozen['pre_fit_lock_sha256']==sha256(WORK/'pre-fit-lock.json')
    assert len(experiment['candidates'])==44
    reference=next(r for r in experiment['candidates'] if r['name']=='fixed60')
    assert select_rows(experiment['candidates'],reference)==experiment['selected']
    entries=0
    for row in experiment['candidates']:
        for cell,v in row['cells'].items():
            arrays=np.load(WORK/cell/(row['name']+'.npz'))
            np.testing.assert_array_equal(arrays['by_bay_phase'].sum(axis=(0,1)),v['raw'])
            assert arrays['by_bay_phase'].shape[1]==v['repetitions']
            assert set(map(int,arrays['bays'])).issubset(lock['training_bays' if cell.startswith('training_') else 'tuning_bays'])
            entries+=1
    assert entries==176
    # Independently recompute the certificate using the previously frozen bound.
    data=load_bundle(('train_development',),bay_filter=lock['training_bays'],primary_only=False)
    calibration=read(WORK/'calibration.json')['calibration'];bounds={}
    for g,c in calibration.items():
        b=history_bound_bundle(data.ends,data.states,data.offsets,data.starts,np.zeros((len(data.starts),1),np.int64),
          data.bay_indexes,len(data.bays),60,int(g),c['required_age_seconds'])
        assert b[:,:,2].sum()==0
        assert b[:,:,1].sum()==c['risky_pairs']
        bounds[g]={'training_generic_bound':int(b[:,:,1].sum()),'constructed_history_bound':int(b[:,:,2].sum())}
    # Existing C3 main-window metrics must be bit-for-bit unchanged.
    from refine_policy import WORK as OLD
    c3=next(r for r in experiment['candidates'] if r['name']=='C3_shape_G75_A900')
    oldrow=next(r for r in read(OLD/'tuning-results.json')['results'] if r['name']=='C3_without_time_0.25_0.25_75')
    np.testing.assert_array_equal(c3['cells']['training_primary_7_days']['raw'],oldrow['training_raw'])
    np.testing.assert_array_equal(c3['cells']['tuning_primary_7_days']['raw'],oldrow['tuning_raw'])
    witness=read(WORK/'verified-witnesses.json')
    assert witness['verified_C3_M60']==1 and witness['all_17_raw_metrics_and_histograms_match_reference']
    assert read(WORK/'witness-verification-lock.json')['experiment_results_sha256']==sha256(WORK/'results.json')
    assert read(WORK/'witness-verification-lock.json')['verification_code_sha256']==sha256(ROOT/'research/parking_sampling/verify_history_scheduler_witness.py')
    for name,count in [('phase3-stability-verification.json',70),('phase3-novelty-verification.json',59)]:
        assert read(DOCS/name)['tests_run']==count
    gate=read(DOCS/'phase3-novelty-gate.json')
    assert gate['phase4_may_start'] is False and gate['final_867_bay_test_evaluated'] is False
    assert experiment['new_check_bays_opened'] is False and not any(x['passes_predeclared_gate'] for x in experiment['usefulness'].values())
    paths=set(p for p in WORK.rglob('*') if p.is_file())
    names=('history_scheduler.py','fit_history_scheduler.py','test_history_scheduler.py',
           'verify_history_scheduler_witness.py','build_history_scheduler_report.py','verify_history_scheduler.py')
    paths.update(ROOT/'research/parking_sampling'/n for n in names)
    paths.update(p for p in DOCS.glob('phase3-history-scheduler-*') if p.is_file())
    paths.discard(DOCS/'phase3-history-scheduler-artifacts.json')
    paths.update(DOCS/n for n in ('README.md','phase3-novelty-gate.json'))
    paths.update((DOCS/'figures').glob('phase3-history-scheduler-*'))
    for name in ('phase3-history-scheduler-comparison.png','phase3-history-scheduler-witness.png'):
        with Image.open(DOCS/'figures'/name) as im:assert im.width>=2000 and im.height>=1000
    links=0
    for name in ('README.md','phase3-history-scheduler-report.md'):
        for target in re.findall(r'\]\(([^\s]+)\)',(DOCS/name).read_text(encoding='utf-8')):
            if target.startswith(('http:','https:','#','mailto:')):continue
            target_path=DOCS/unquote(target.split('#')[0])
            assert target_path.exists() or target_path==DOCS/'phase3-history-scheduler-artifacts.json',target
            links+=1
    history_path=DOCS/'phase3-history-scheduler-history.json'
    write_json(history_path,{'created_on':'2026-10-25','historical_file_mapping':mappings,
               'current_readme_sha256':sha256(DOCS/'README.md'),'current_gate_sha256':sha256(DOCS/'phase3-novelty-gate.json')})
    verify_path=DOCS/'phase3-history-scheduler-artifact-verification.json'
    write_json(verify_path,{'created_on':'2026-10-25','passed':True,'test_count':result.testsRun,
       'prior_manifest_entries_checked':prior,'prior_entries_resolved_by_snapshots':snapshots,
       'candidate_cells_verified':entries,'independently_recomputed_training_bounds':bounds,
       'C3_previous_main_metrics_unchanged':True,'verified_new_C3_M60':1,'local_links_checked':links,
       'figures_visual_QA':'Both PNGs inspected; labels readable, episode and observation semantics explicit',
       'final_test_states_opened':False,'phase4_gate_opened':False,'new_check_cohort_opened':False})
    paths.update((history_path,verify_path))
    write_json(DOCS/'phase3-history-scheduler-artifacts.json',{'created_on':'2026-10-25',
       'scope':'C5_predeclared_construction_negative_result_and_verified_tuning_witness',
       'files':{p.relative_to(ROOT).as_posix():sha256(p) for p in sorted(paths)},
       'final_test_evaluated':False,'phase4_may_start':False,'new_check_bays_opened':False})
    print(json.dumps({'tests_passed':result.testsRun,'prior_entries_verified':sum(prior.values()),
      'snapshots':snapshots,'candidate_cells_verified':entries,'new_artifacts_frozen':len(paths),
      'new_C3_witness_verified':1,'phase4_may_start':False,'final_test_evaluated':False}))


if __name__=='__main__':main()
