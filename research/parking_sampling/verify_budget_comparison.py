"""Check expected-resource LPs, raw counters, legacy equality and provenance."""
import io
import ast
import json
import re
import sys
import unittest
from pathlib import Path
from urllib.parse import unquote
import numpy as np
from PIL import Image
from prepare_data import ROOT,DOCS,sha256
from budget_comparison import definitions,choose_mixture
from run_budget_comparison import WORK,read,FAMILIES,C3_WORK
from fit_history_scheduler import WORK as C5_WORK
from run_phase3 import write_json


def main():
    modules=('test_prepare_data','test_methods','test_refinement','test_novelty_audit','test_episode_pair_certificate',
             'test_stability_audit','test_history_certificate','test_history_scheduler','test_budget_comparison',
             'test_budget_coverage_annex')
    stream=io.StringIO();suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n) for n in modules)
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    receipt={'created_on':'2026-10-25','tests_run':result.testsRun,'passed':result.wasSuccessful(),
      'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
      'test_sha256':{n+'.py':sha256(Path(__file__).parent/(n+'.py')) for n in modules},
      'test_log':stream.getvalue(),'previous_receipts_preserved':True,'final_test_read':False}
    write_json(DOCS/'phase3-budget-comparison-verification.json',receipt)
    if not result.wasSuccessful():print(stream.getvalue());sys.exit(1)
    assert result.testsRun==87
    mappings=list(read(DOCS/'phase3-history-scheduler-history.json')['historical_file_mapping'])
    for original,snapshot in [('docs/research/adaptive-sampling/README.md','README-before-budget.md'),
       ('docs/research/adaptive-sampling/phase3-novelty-gate.json','phase3-novelty-gate-before-budget.json')]:
        path=WORK/'history'/snapshot
        mappings.append({'original_path':original,'snapshot_path':path.relative_to(ROOT).as_posix(),
          'snapshot_sha256':sha256(path),'reason':'Live status updated after the predeclared matched-budget diagnostic'})
    first_annex=WORK/'coverage-annex/history/budget_coverage_annex-v1.py'
    mappings.append({'original_path':'research/parking_sampling/budget_coverage_annex.py',
      'snapshot_path':first_annex.relative_to(ROOT).as_posix(),'snapshot_sha256':sha256(first_annex),
      'reason':'Version2 handles infeasible control families explicitly; bank and LP constraints unchanged'})
    def check(relative,expected):
        path=ROOT/relative
        if path.exists() and sha256(path)==expected:return 'unchanged'
        for m in mappings:
            if m['original_path']==relative and m['snapshot_sha256']==expected:
                assert sha256(ROOT/m['snapshot_path'])==expected;return 'snapshot'
        raise AssertionError('Unexplained changed frozen artifact: '+relative)
    counts={};snapshots=0
    for name in ('phase3-artifact-manifest.json','phase3-method-lock.json','phase3-refinement-lock.json',
                 'phase3-novelty-artifacts.json','phase3-stability-artifacts.json','phase3-history-scheduler-artifacts.json'):
        lock=read(DOCS/name)
        for relative,h in lock['files'].items():snapshots+=check(relative,h)=='snapshot'
        counts[name]=len(lock['files'])
    lock=read(WORK/'pre-fit-lock.json')
    assert lock['plan_sha256']==sha256(DOCS/'phase3-budget-comparison-plan.json')
    for name,h in lock['code_sha256'].items():check('research/parking_sampling/'+name,h)
    selected=read(WORK/'selection-before-check-replay.json');results=read(WORK/'development-results.json')
    assert selected['pre_fit_lock_sha256']==sha256(WORK/'pre-fit-lock.json')
    assert results['selection_sha256']==sha256(WORK/'selection-before-check-replay.json')
    assert read(WORK/'pre-check-lock.json')['selection_sha256']==results['selection_sha256']
    for rel,h in selected['fitting_bank_files'].items():assert sha256(ROOT/rel)==h
    bank=definitions();index={d.policy.name:i for i,d in enumerate(bank)}
    cached={};replays=0
    for path in sorted((WORK/'banks').glob('*.npz')):
        arrays=np.load(path);info=read(path.with_suffix('.json'))
        assert info['arrays_sha256']==sha256(path)
        assert info['policy_bank_sha256']==sha256(WORK/'policy-bank-before-replay.json')
        assert list(arrays['names'])==[d.policy.name for d in bank]
        values=arrays['by_bay'];assert values.shape==(269,info['bays'],17)
        assert np.all(values[:,:,0]==values[0,:,0]) and np.all(values>=0)
        assert np.all(arrays['delay_histograms'].sum(axis=1)==values[:,:,5].sum(axis=1))
        assert set(map(int,arrays['bays'])).issubset(lock['cohorts'][info['cohort']])
        assert set(info['source_files'])=={'train_development' if info['cohort']=='training256' else 'validation_development'}
        cached[path.stem]=(values,arrays['bays']);replays+=269*info['windows']*info['repetitions']
    assert len(cached)==8
    fitted=np.array([cached[c][0].sum(axis=1) for c in selected['cells']])
    for item in selected['selected'].values():
        ids=[i for i,d in enumerate(bank) if item['family'] in d.groups];target=index[item['target']]
        fit=choose_mixture(fitted[:,ids,:],fitted[:,target,:])
        assert abs(fit['max_error_ratio']-item['fitting_max_error_ratio'])<1e-9
        weights=np.array([item['weights'].get(bank[i].policy.name,0.) for i in ids])
        expected=np.einsum('p,cpj->cj',weights,fitted[:,ids,:])
        assert abs(weights.sum()-1)<1e-9
        assert np.all(expected[:,1]<=fitted[:,target,1]+.01)
        assert np.all(expected[:,2:4]<=item['fitting_max_error_ratio']*fitted[:,target,2:4]+.01)
    envelopes=0
    for cell,group in results['cohorts'].items():
        values,bays=cached[cell];totals=values.sum(axis=1)
        for key,item in group['equal_expected_budget_hindsight_envelopes'].items():
            weights=np.zeros(269)
            for name,w in item['weights'].items():weights[index[name]]=w
            raw=weights@totals;target=totals[index[item['target']]]
            np.testing.assert_allclose(raw,item['expected_raw'],rtol=1e-12,atol=1e-6)
            assert abs(raw[1]/target[1]-1)<1e-7
            assert max(raw[2:4]/target[2:4])<=item['max_error_ratio']+1e-9
            assert item['hindsight_reference_not_frozen_policy'] is True;envelopes+=1
        for key,item in group['frozen_controls'].items():
            weights=selected['selected'][key]['weights']
            mixed=sum(w*values[index[name]] for name,w in weights.items())
            np.testing.assert_allclose(mixed.sum(axis=0),item['control_expected_raw'],rtol=1e-12,atol=1e-5)
    assert envelopes==40
    from budget_coverage_annex import ANNEX,extra_definitions,solve_covered
    annexlock=read(ANNEX/'pre-fit-lock.json');v1lock=read(WORK/'coverage-annex/pre-fit-lock.json')
    for name,h in v1lock['code_sha256'].items():check('research/parking_sampling/'+name,h)
    for name,h in annexlock['code_sha256'].items():check('research/parking_sampling/'+name,h)
    assert annexlock['plan_sha256']==sha256(DOCS/'phase3-budget-coverage-annex-v2-plan.json')
    assert annexlock['base_plan_sha256']==sha256(DOCS/'phase3-budget-coverage-annex-plan.json')
    assert annexlock['primary_results_sha256']==sha256(WORK/'development-results.json')
    # Independently prove that version2 did not modify the extra bank or LP.
    def function_source(path,name):
        source=path.read_text(encoding='utf-8');tree=ast.parse(source)
        return ast.get_source_segment(source,next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name))
    for name in ('extra_definitions','solve_covered'):
        assert function_source(first_annex,name)==function_source(ROOT/'research/parking_sampling/budget_coverage_annex.py',name)
    annexsel=read(ANNEX/'selection-before-annex-check.json');annex=read(ANNEX/'results.json')
    assert annexsel['annex_lock_sha256']==sha256(ANNEX/'pre-fit-lock.json')
    assert annex['selection_sha256']==sha256(ANNEX/'selection-before-annex-check.json')
    assert read(ANNEX/'pre-check-lock.json')['selection_sha256']==annex['selection_sha256']
    extended=bank+extra_definitions();extended_index={d.policy.name:i for i,d in enumerate(extended)}
    assert len(extended)==326;extended_cells={}
    for cell,(old,bays) in cached.items():
        path=ANNEX/(cell+'.npz');arrays=np.load(path);meta=read(path.with_suffix('.json'))
        assert sha256(path)==meta['arrays_sha256'];np.testing.assert_array_equal(arrays['bays'],bays)
        assert arrays['by_bay'].shape==(57,len(bays),17)
        np.testing.assert_array_equal(arrays['names'],[d.policy.name for d in extended[269:]])
        assert np.all(arrays['by_bay'][:,:,0]==old[0,:,0])
        extended_cells[cell]=np.concatenate((old,arrays['by_bay']),axis=0)
        replays+=57*meta['windows']*meta['repetitions']
        if cell.startswith(('training256','tuning128')):
            reuse=read(ANNEX/(cell+'-cache-reuse.json'))
            assert sha256(ROOT/reuse['source'])==reuse['source_sha256']==sha256(path)
    av=np.array([extended_cells[c].sum(axis=1) for c in annexsel['cells']])
    fitting_feasible=0;fitting_infeasible=0;annex_feasible=0;annex_infeasible=0
    for key,item in annexsel['selected'].items():
        ids=[i for i,d in enumerate(extended) if item['family'] in d.groups];ti=extended_index[item['target']]
        if item['feasible']:
            fitted=solve_covered(av[:,ids,:],av[:,ti,:])
            assert abs(fitted['max_error_ratio']-item['max_error_ratio'])<1e-8
            weights=np.array([item['weights'].get(extended[i].policy.name,0.) for i in ids])
            expected=np.einsum('p,cpj->cj',weights,av[:,ids,:])
            assert abs(weights.sum()-1)<1e-9
            assert np.all(expected[:,14]<=av[:,ti,14]+1e-7)
            assert np.all(expected[:,1]/av[:,ti,1]<=1+1e-7)
            fitting_feasible+=1
        else:
            try:solve_covered(av[:,ids,:],av[:,ti,:])
            except ValueError as e:assert 'infeasible' in str(e).lower()
            else:raise AssertionError('Unreported feasible fitting family')
            fitting_infeasible+=1
    for cell,rows in annex['cohorts'].items():
        values=extended_cells[cell];totals=values.sum(axis=1)
        for key,item in rows.items():
            chosen=annexsel['selected'][key];ids=[i for i,d in enumerate(extended) if chosen['family'] in d.groups]
            ti=extended_index[chosen['target']];env=item['hindsight_envelope']
            if env['feasible']:
                w=np.zeros(326)
                for name,weight in env['weights'].items():w[extended_index[name]]=weight
                raw=w@totals;np.testing.assert_allclose(raw,env['expected_raw'],rtol=1e-12,atol=1e-5)
                assert abs(raw[1]/totals[ti,1]-1)<1e-7 and raw[14]<=totals[ti,14]+1e-7
                assert max(raw[2:4]/totals[ti,2:4])<=env['max_error_ratio']+1e-8
                annex_feasible+=1
            else:
                try:solve_covered(totals[None,ids,:],totals[ti][None,:],True)
                except ValueError as e:assert 'infeasible' in str(e).lower()
                else:raise AssertionError('Unreported feasible check envelope')
                annex_infeasible+=1
            if chosen['feasible']:
                mixed=sum(weight*values[extended_index[name]] for name,weight in chosen['weights'].items()).sum(axis=0)
                assert abs(mixed[1]/totals[ti,1]-item['frozen_control_to_target_resource_ratio'])<1e-10
                assert abs(mixed[14]-item['frozen_control_metrics']['M60_expected_count'])<1e-7
                assert (mixed[14]<=totals[ti,14]+1e-7)==item['frozen_control_M60_admissible']
    # Exact equality with the previous C5 experiment's unchanged C3/C4 targets.
    prior=read(C5_WORK/'results.json')
    for target,oldname in (('C3','C3_shape_G75_A900'),('C4','C3_shape_G72_A900')):
        oldrow=next(r for r in prior['candidates'] if r['name']==oldname)
        for cell,oldcell in [('training256_primary_7_days','training_primary_7_days'),
          ('training256_sensitivity_1_day','training_sensitivity_1_day'),('tuning128_primary_7_days','tuning_primary_7_days'),
          ('tuning128_sensitivity_1_day','tuning_sensitivity_1_day')]:
            np.testing.assert_array_equal(cached[cell][0][index[target]].sum(axis=0),oldrow['cells'][oldcell]['raw'])
    # S2 and fixed60 on original512 must reproduce frozen full phase arrays.
    legacy=0
    for label in ('primary_7_days','sensitivity_1_day'):
        for name in ('fixed_60','S2_1440','S2_2880'):
            old=np.load(C3_WORK/label/(name+'.npz'))
            np.testing.assert_array_equal(cached['check512_'+label][1],old['bays'])
            np.testing.assert_array_equal(cached['check512_'+label][0][index[name]],old['by_bay_phase'].sum(axis=1));legacy+=1
    assert read(DOCS/'phase3-history-scheduler-verification.json')['tests_run']==76
    gate=read(DOCS/'phase3-novelty-gate.json')
    assert gate['phase4_may_start'] is False and gate['final_867_bay_test_evaluated'] is False
    assert results['new_check_cohort_opened'] is False
    for pattern in ('phase3-budget-envelopes.png','phase3-budget-error-scatter.png'):
        with Image.open(DOCS/'figures'/pattern) as im:assert im.width>=2000 and im.height>=1000
    links=0
    for name in ('README.md','phase3-budget-comparison-report.md'):
        for target in re.findall(r'\]\(([^\s]+)\)',(DOCS/name).read_text(encoding='utf-8')):
            if target.startswith(('http:','https:','#','mailto:')):continue
            p=DOCS/unquote(target.split('#')[0])
            assert p.exists() or p==DOCS/'phase3-budget-comparison-artifacts.json',target
            links+=1
    history=DOCS/'phase3-budget-comparison-history.json'
    write_json(history,{'created_on':'2026-10-25','historical_file_mapping':mappings,
      'current_readme_sha256':sha256(DOCS/'README.md'),'current_gate_sha256':sha256(DOCS/'phase3-novelty-gate.json')})
    receipt=DOCS/'phase3-budget-comparison-artifact-verification.json'
    write_json(receipt,{'created_on':'2026-10-25','passed':True,'tests_run':result.testsRun,
      'prior_manifest_entries_checked':counts,'prior_entries_resolved_by_snapshots':snapshots,
      'policies':269,'bank_cells':8,'window_policy_phase_replays':replays,'frozen_mixtures_verified':10,
      'exact_expected_budget_envelopes_verified':envelopes,'C3_C4_fitting_target_equalities_verified':8,
      'coverage_annex_policies':326,'coverage_annex_fitting_feasible':fitting_feasible,
      'coverage_annex_fitting_infeasible':fitting_infeasible,'coverage_annex_envelopes_feasible':annex_feasible,
      'coverage_annex_envelopes_infeasible':annex_infeasible,'annex_v1_v2_bank_and_LP_source_identical':True,
      'frozen_S2_and_fixed60_bay_counter_equalities_verified':legacy,'local_links_checked':links,
      'figures_visual_QA':'Both scientific PNGs inspected; frozen selection and hindsight normalization distinguished',
      'old76_test_receipt_preserved':True,'new_check_cohort_opened':False,'final_test_evaluated':False,'phase4_may_start':False})
    paths={p for p in WORK.rglob('*') if p.is_file()}
    paths.update(DOCS.glob('phase3-budget-comparison-*'))
    paths.update(DOCS.glob('phase3-budget-coverage-annex-*'))
    paths.discard(DOCS/'phase3-budget-comparison-artifacts.json')
    paths.update(DOCS/n for n in ('README.md','phase3-novelty-gate.json'))
    for pat in ('phase3-budget-envelopes.*','phase3-budget-error-scatter.*'):paths.update((DOCS/'figures').glob(pat))
    for name in ('budget_comparison.py','run_budget_comparison.py','test_budget_comparison.py',
                 'report_budget_comparison.py','verify_budget_comparison.py','README-budget-comparison.md',
                 'budget_coverage_annex.py','test_budget_coverage_annex.py'):
        paths.add(ROOT/'research/parking_sampling'/name)
    write_json(DOCS/'phase3-budget-comparison-artifacts.json',{'created_on':'2026-10-25',
      'scope':'predeclared_budget_matched_development_diagnostic',
      'files':{p.relative_to(ROOT).as_posix():sha256(p) for p in sorted(paths)},
      'new_check_cohort_opened':False,'final_test_evaluated':False,'phase4_may_start':False})
    print(json.dumps({'tests_passed':result.testsRun,'prior_entries_verified':sum(counts.values()),
      'snapshots_used':snapshots,'window_policy_phase_replays':replays,'new_artifacts_frozen':len(paths),
      'equal_budget_envelopes_verified':envelopes,'phase4_may_start':False}))


if __name__=='__main__':main()
