"""New verification receipt; never overwrite any older verification script output."""
import io
import re
import unittest
from urllib.parse import unquote
import numpy as np
from PIL import Image
from prepare_data import ROOT,DOCS,sha256
from assess_analytic_contribution import WORK,read
from analytic_certificate import reset_certificate,exact_maximum_misses
from run_phase3 import write_json


def main():
    modules=('test_prepare_data','test_methods','test_refinement','test_novelty_audit','test_episode_pair_certificate',
      'test_stability_audit','test_history_certificate','test_history_scheduler','test_budget_comparison',
      'test_budget_coverage_annex','test_analytic_certificate')
    stream=io.StringIO();suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n) for n in modules)
    test=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    base={'created_on':'2026-10-25','tests_run':test.testsRun,'passed':test.wasSuccessful(),
      'failures':len(test.failures),'errors':len(test.errors),'skipped':len(test.skipped),
      'test_sha256':{n+'.py':sha256(ROOT/'research/parking_sampling'/(n+'.py')) for n in modules},
      'test_log':stream.getvalue(),'final_test_evaluated':False,'previous_receipts_preserved':True}
    path=DOCS/'phase3-analytic-verification.json';write_json(path,base)
    if not test.wasSuccessful():print(stream.getvalue());raise AssertionError('Tests failed')
    assert test.testsRun==95
    history=read(DOCS/'phase3-analytic-history.json');mappings=history['historical_file_mapping']
    def check(relative,expected):
        p=ROOT/relative
        if p.exists() and sha256(p)==expected:return 'unchanged'
        for row in mappings:
            if row['original_path']==relative and row['snapshot_sha256']==expected:
                assert sha256(ROOT/row['snapshot_path'])==expected;return 'snapshot'
        raise AssertionError('Unexplained change to frozen artifact: '+relative)
    manifests={};snapshots=0
    for name in ('phase3-artifact-manifest.json','phase3-method-lock.json','phase3-refinement-lock.json',
      'phase3-novelty-artifacts.json','phase3-stability-artifacts.json','phase3-history-scheduler-artifacts.json',
      'phase3-budget-comparison-artifacts.json'):
        files=read(DOCS/name)['files'];manifests[name]=len(files)
        for relative,h in files.items():snapshots+=check(relative,h)=='snapshot'
    lock=read(WORK/'pre-analysis-lock.json')
    assert lock['plan_sha256']==sha256(DOCS/'phase3-analytic-contribution-plan.json')
    for name,h in lock['code_sha256'].items():assert sha256(ROOT/'research/parking_sampling'/name)==h
    finite=read(WORK/'finite-enumeration.json');recorded=read(WORK/'recorded-counts.json')
    assert finite['pre_analysis_lock_sha256']==recorded['pre_analysis_lock_sha256']==sha256(WORK/'pre-analysis-lock.json')
    assert finite['all_passed'] and finite['grid']['cases']==2916 and len(finite['seeded_arbitrary_start_cases'])==200
    for case in finite['seeded_arbitrary_start_cases']:
        assert case['maximum_missed']<=case['local_bound'] and case['maximum_missed']<=case['full_window_bound']
    for case in finite['strict_and_conservative_examples'].values():
        p=case['parameters'];e=case['ends'];s=case['states']
        assert reset_certificate(e,s,0,**p)==case['counts']
        assert exact_maximum_misses(e,s,0,**p)==case['exact']
    # Explicit equality at p-r=A: the strict necessary condition must fail.
    equality=reset_certificate([2,3,6,8],[0,1,0,1],0,3,5,2)
    assert equality['adjacent_pair']==1 and equality['recursive_reset']==0
    assert exact_maximum_misses([2,3,6,8],[0,1,0,1],0,3,5,2)['maximum_missed']==0
    assert len(recorded['cells'])==8
    for name,row in recorded['cells'].items():
        p=WORK/(name+'.npz');assert sha256(p)==row['arrays_sha256'];arrays=np.load(p)
        assert dict(zip(arrays['names'].tolist(),map(int,arrays['by_bay'].sum(axis=0))))==row['counts']
        cohort=name.split('_')[0];assert set(map(int,arrays['bays'])).issubset(lock['cohorts'][cohort])
        assert set(row['source_files'])=={'train_development' if cohort=='training256' else 'validation_development'}
        assert row['counts']['recursive_reset']==row['counts']['legacy_history']
    sources=read(DOCS/'phase3-analytic-source-evidence.json')['sources']
    for name,row in sources.items():
        assert sha256(WORK/'sources'/(name+'.pdf'))==row['pdf_sha256']
        assert sha256(WORK/'sources'/(name+'.txt'))==row['text_sha256']
        assert row['read'] and row['not_claimed']
    with Image.open(DOCS/'figures/phase3-analytic-reset.png') as im:assert im.width>=2000 and im.height>=1000
    links=0
    for name in ('README.md','phase3-analytic-method.md','phase3-analytic-report.md','phase3-analytic-sources.md','phase3-supervisor-brief.md'):
        for target in re.findall(r'\]\(([^\s]+)\)',(DOCS/name).read_text(encoding='utf-8')):
            if target.startswith(('http:','https:','#','mailto:')):continue
            p=DOCS/unquote(target.split('#')[0]);assert p.exists(),(name,target);links+=1
    gate=read(DOCS/'phase3-novelty-gate.json')
    assert not gate['phase4_may_start'] and not gate['final_867_bay_test_evaluated']
    assert read(DOCS/'phase3-budget-comparison-verification.json')['tests_run']==87
    assert sha256(DOCS/'README.md')==history['current_readme_sha256']
    assert sha256(DOCS/'phase3-novelty-gate.json')==history['current_gate_sha256']
    base.update({'prior_manifest_entries_checked':manifests,'prior_entries_resolved_by_snapshots':snapshots,
      'finite_grid_cases':2916,'seeded_arbitrary_start_cases':200,'strict_examples_independently_rechecked':3,
      'recorded_cells_checked':8,'recorded_legacy_new_counts_identical':True,'primary_pdf_and_text_hashes_checked':3,
      'local_links_checked':links,'figure_visual_QA':'PNG inspected; no clipping; toy not physical experiment; empirical equality explicit',
      'new_check_cohort_opened':False,'phase4_may_start':False})
    write_json(path,base)
    paths={p for p in WORK.rglob('*') if p.is_file()}
    paths.update(DOCS.glob('phase3-analytic-*'));paths.discard(DOCS/'phase3-analytic-artifacts.json')
    paths.update(DOCS/n for n in ('README.md','phase3-novelty-gate.json','phase3-supervisor-brief.md'))
    paths.update((DOCS/'figures').glob('phase3-analytic-reset.*'))
    for name in ('analytic_certificate.py','test_analytic_certificate.py','assess_analytic_contribution.py',
      'fetch_analytic_sources.py','fetch_duration_source.py','report_analytic_contribution.py',
      'status_analytic_contribution.py','verify_analytic_contribution.py','README-analytic-contribution.md'):
        paths.add(ROOT/'research/parking_sampling'/name)
    write_json(DOCS/'phase3-analytic-artifacts.json',{'created_on':'2026-10-25','scope':'Analytical candidate, proof and prior-art review on known development data',
      'files':{p.relative_to(ROOT).as_posix():sha256(p) for p in sorted(paths)},
      'final_test_evaluated':False,'phase4_may_start':False})
    print({'tests_passed':test.testsRun,'prior_entries_verified':sum(manifests.values()),'snapshot_resolutions':snapshots,
      'new_artifacts_frozen':len(paths),'finite_grid':2916,'seeded':200,'recorded_cells':8,'local_links':links})


if __name__=='__main__':main()
