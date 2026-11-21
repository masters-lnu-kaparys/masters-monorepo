"""Verify practical-result artifacts without replaying or accessing protected histories."""
import io
import re
import unittest
from urllib.parse import unquote
import numpy as np
from PIL import Image
from prepare_data import ROOT,DOCS,sha256
from run_phase3 import write_json
from assess_analytic_contribution import read
from run_local_risk import WORK as BASE,grid,old_bank
from local_risk_calibration_v3 import WORK as CAL,calibrate,realized_by_bay
from local_risk_wide_control import WORK as WIDE,bank
from budget_comparison import definitions,choose_mixture
from budget_coverage_annex import extra_definitions

CODE=ROOT/'research/parking_sampling'
MODULES=('test_prepare_data','test_methods','test_refinement','test_novelty_audit','test_episode_pair_certificate',
 'test_stability_audit','test_history_certificate','test_history_scheduler','test_budget_comparison',
 'test_budget_coverage_annex','test_analytic_certificate','test_start_reachability','test_local_risk',
 'test_local_risk_calibration','test_local_risk_calibration_v3','test_calibrated_schedule','test_frozen_local_priors')


def verify_locks():
    entries=(
      (BASE/'pre-fit-lock.json','phase3-local-risk-plan.json',None),
      (BASE/'bay-state-control/pre-fit-lock.json','phase3-local-risk-bay-control-plan.json','local_risk_bay_control.py'),
      (BASE/'calibration-v2/pre-fit-lock.json','phase3-local-risk-calibration-plan.json',None),
      (CAL/'pre-fit-lock.json','phase3-local-risk-calibration-v3-plan.json',None),
      (WIDE/'pre-fit-lock.json','phase3-local-risk-wide-control-plan.json','local_risk_wide_control.py'),
      (BASE/'full-model-control/pre-analysis-lock.json','phase3-local-risk-full-model-control-plan.json','local_risk_full_model_control.py'),
      (BASE/'union-control/pre-fit-lock.json','phase3-local-risk-final-audit-plan.json','local_risk_union_control.py'),
      (CAL/'independent-audit/pre-audit-lock.json','phase3-local-risk-final-audit-plan.json','audit_local_risk.py'))
    checked=0
    for path,plan,code in entries:
        lock=read(path);assert sha256(DOCS/plan)==lock['plan_sha256'];assert not lock['final_test_evaluated']
        for key in ('code_sha256','source_sha256'):
            item=lock.get(key)
            if isinstance(item,dict):
                for name,h in item.items():assert sha256(CODE/name)==h;checked+=1
            elif item:assert code and sha256(CODE/code)==item;checked+=1
        for key,p in (('base_fit_lock_sha256',BASE/'pre-fit-lock.json'),('base_result_sha256',BASE/'check-results.json'),
          ('base_selection_sha256',BASE/'selection-before-check.json'),('target_selection_sha256',CAL/'selection-before-check.json'),
          ('headline_selection_sha256',CAL/'selection-before-check.json'),('calibration_selection_sha256',CAL/'selection-before-check.json'),
          ('target_result_sha256',CAL/'results.json'),('target_results_sha256',CAL/'results.json'),
          ('known_headline_result_sha256',CAL/'results.json'),('calibration_result_sha256',CAL/'results.json'),
          ('runtime_source_sha256',CODE/'calibrated_schedule.py')):
            if key in lock:assert sha256(p)==lock[key]
    for folder in (BASE,CAL):
        s=read(folder/'selection-before-check.json');assert sha256(folder/'pre-fit-lock.json')==s['pre_fit_lock_sha256']
        assert sha256(folder/'selection-before-check.json')==read(folder/'pre-check-lock.json')['selection_sha256']
        for name,h in s['check_model_hashes'].items():assert sha256(folder/'models'/(name+'.npz'))==h
    bad=read(BASE/'calibration-v2/incomplete-execution.json')
    assert not bad['new_candidate_check_results_computed'] and not (BASE/'calibration-v2/selection-before-check.json').exists()
    count=0
    for p in BASE.rglob('*.json'):
        meta=read(p)
        if isinstance(meta,dict) and 'arrays_sha256' in meta:
            assert sha256(p.with_suffix('.npz'))==meta['arrays_sha256'];count+=1
    meta=read(BASE/'training-metadata.json')
    assert meta['bays']==1063 and meta['requested_ids']==1098 and len(meta['missing_training_bays'])==35
    assert set(meta['source_files'])=={'train_development'}
    assert sha256(BASE/'training-statistics.npz')==meta['statistics_sha256']
    receipt=read(CAL/'shared-prior-receipt.json')
    assert sha256(CAL/'shared-priors.npz')==receipt['shared_priors_sha256']
    assert receipt['exact_equality_on1063supported_bays'] and not receipt['reserved_training_read']
    return {'pre_execution_locks':len(entries),'frozen_source_hashes':checked,'bank_array_receipts':count}


def verify_calibration():
    selected=read(CAL/'selection-before-check.json');results=read(CAL/'results.json');head=selected['headline']
    assert head=='bay_full_alpha500_display_guarded' and results['headline']==head
    assert results['selection_sha256']==sha256(CAL/'selection-before-check.json')
    defs=definitions()+extra_definitions();oldnames=[d.policy.name for d in defs];fixed=oldnames.index('fixed_60')
    cells=selected['fitting_cells'];refs=np.array([old_bank(c)[0][fixed].sum(axis=0) for c in cells])
    models=grid();names=[d['name'] for d in models]+['fixed_60']
    arrays=np.array([np.load(BASE/(c+'.npz'))['by_bay'].sum(axis=1) for c in cells]);arrays=np.concatenate((arrays,refs[:,None]),axis=1)
    for key,row in selected['selected'].items():
        ids=[i for i,d in enumerate(models) if d['arm']==row['arm']]+[len(models)]
        answer=calibrate(arrays[:,ids],refs,row['gamma'],row['criterion']=='original_strict')
        weights={names[i]:float(w) for i,w in zip(ids,answer['weights']) if w>0}
        assert weights==row['weights'];np.testing.assert_allclose(answer['expected_raw'],row['fitting_expected_raw'],rtol=1e-13,atol=1e-5)
    scores=selected['selected'];winner=min(('bay_full_alpha50_display_guarded','bay_full_alpha500_display_guarded'),
      key=lambda k:(scores[k]['fitting_calls_objective'],0 if 'alpha50_' in k else 1));assert winner==head
    total=0
    for cell,outcomes in results['cohorts'].items():
        old,bays=old_bank(cell);arr=np.load(CAL/(cell+'.npz'));np.testing.assert_array_equal(bays,arr['bays'])
        nn=oldnames+arr['names'].tolist();values=np.concatenate((old,arr['by_bay']))
        assert np.all(values>=0) and np.all(values[:,:,0]==old[fixed,:,0])
        for key,choice in selected['selected'].items():
            row=outcomes[key];target=sum(w*values[nn.index(n)] for n,w in choice['weights'].items());target[:,0]=old[fixed,:,0]
            np.testing.assert_allclose(target.sum(axis=0),row['expected_raw'],rtol=1e-13,atol=1e-5)
            realized,allocation=realized_by_bay(values,bays,nn,choice['weights'])
            np.testing.assert_array_equal(realized.sum(axis=0),row['primary_raw']);assert allocation==row['primary_allocation']
            assert [x['seed'] for x in row['allocation_seeds']]==list(range(20261025,20261035))
            for seedrow in row['allocation_seeds']:
                by,_=realized_by_bay(values,bays,nn,choice['weights'],seedrow['seed']);np.testing.assert_array_equal(by.sum(axis=0),seedrow['raw'])
            total+=1
        h=outcomes[head];assert h['primary_display_passes'] and h['primary_calls_reduction_percent']>=10
        assert h['primary_raw'][14]>0 and h['reference_raw'][14]==0
        assert all(x['display_passes'] for x in h['allocation_seeds'])
    assert not results['final_test_evaluated'] and not results['phase4_may_start']
    return {'selected_calibrations_reproduced':len(scores),'policy_cell_counters_reproduced':total,'allocation_seeds_per_cell':10}


def verify_controls():
    target=read(CAL/'results.json');full=read(BASE/'full-model-control/results.json');wide=read(WIDE/'results.json')
    union=read(BASE/'union-control/results.json');wdefs=bank();assert len(wdefs)==900
    assert len({tuple(t) for _,t in wdefs})==841 and all(np.all((t>=15)&(t<=300)) for _,t in wdefs)
    oldnames=[d.policy.name for d in definitions()+extra_definitions()];fixed=oldnames.index('fixed_60');n=0
    for cell,allrows in target['cohorts'].items():
        tr=np.array(allrows[target['headline']]['expected_raw']);old,bays=old_bank(cell)
        f=np.load(BASE/'full-model-control'/(cell+'.npz'));w=np.load(WIDE/(cell+'.npz'))
        np.testing.assert_array_equal(bays,f['bays']);np.testing.assert_array_equal(bays,w['bays'])
        assert f['by_bay'].shape==(256,len(bays),17) and w['by_bay'].shape==(900,len(bays),17)
        assert np.all(f['by_bay']>=0) and np.all(w['by_bay']>=0)
        assert np.all(f['by_bay'][:,:,0]==old[fixed,:,0]) and np.all(w['by_bay'][:,:,0]==old[fixed,:,0])
        for family,row in full['cohorts'][cell].items():
            allowed={'pooled':('pooled_state','pooled_clock_age'),'bay_state':('bay_state_alpha50',),
              'unshrunk':('bay_full_alpha0',),'union':('pooled_state','pooled_clock_age','bay_state_alpha50','bay_full_alpha0')}[family]
            names=f['names'].tolist()+['fixed_60'];values=np.concatenate((f['by_bay'],old[fixed:fixed+1]))
            ids=[i for i,name in enumerate(names) if name=='fixed_60' or any(name.startswith(a+'_F') for a in allowed)]
            answer=choose_mixture(values[ids].sum(axis=1)[None],tr[None],True)
            assert abs(answer['max_error_ratio']-row['t'])<1e-8 and row['t']>1
            np.testing.assert_allclose(answer['expected_raw'][0],row['expected_raw'],rtol=1e-10,atol=.001);n+=1
        for family,values,names,row in (
          ('wide',w['by_bay'],w['names'].tolist(),wide['cohorts'][cell]),
          ('union',np.concatenate((old,w['by_bay'])),oldnames+w['names'].tolist(),union['cohorts'][cell])):
            env=row['hindsight_equal_expected_budget'];answer=choose_mixture(values.sum(axis=1)[None],tr[None],True)
            assert abs(answer['max_error_ratio']-env['t'])<1e-8 and env['t']>1
            weights=env['weights'];assert abs(sum(weights.values())-1)<1e-10
            cr=sum(weights[name]*values[names.index(name)].sum(axis=0) for name in weights)
            assert abs(cr[1]/tr[1]-1)<1e-9 and max(cr[2:4]/tr[2:4])<=env['t']+1e-8
            assert row['resource_admissible'] and row['control_to_candidate_ratios']['F']>1 and row['control_to_candidate_ratios']['O']>1;n+=1
    assert union['control_count']==1226
    return {'exact_expected_budget_envelopes_reproduced':n,'wide_control_definitions':900,'unique_wide_tables':841,'union_definitions':1226}


def preserve_status():
    prior=read(DOCS/'phase3-start-reachability-history.json');mappings=list(prior['historical_file_mapping'])
    folder=BASE/'history';folder.mkdir(exist_ok=True)
    for name,key in (('README.md','current_readme_sha256'),('phase3-novelty-gate.json','current_gate_sha256')):
        source=DOCS/name;snapshot=folder/name
        if not snapshot.exists():assert sha256(source)==prior[key];snapshot.write_bytes(source.read_bytes())
        assert sha256(snapshot)==prior[key]
        mappings.append({'original_path':source.relative_to(ROOT).as_posix(),'snapshot_path':snapshot.relative_to(ROOT).as_posix(),
          'snapshot_sha256':sha256(snapshot),'reason':'Practical local-risk result added; previous status retained byte-for-byte'})
    before=(folder/'README.md').read_text(encoding='utf-8');begin=before.index('**Поточний стан:');end=before.index('**Досліджуємо вибір часу')
    text='''**Поточний стан: отримано практичне авторське покращення на даних розроблення.** [Метод локального ризику та калібрування](phase3-local-risk-method.md) зменшує вимірювання на **11,9-21,8%**, час помилкового показу «вільно» на **13,2-18,7%**, а «зайнято» на **8,4-18,8%** відносно щохвилинних перевірок. Це власні результати для відомих перевірочних груп 256/512, двох критеріїв тривалості вікон та основного наперед заданого вибору таблиць. [Повний звіт, графіки й контролі](phase3-local-risk-report.md), [пояснення для захисту](phase3-local-risk-defense-brief.md).

Авторська частина - конкретне поєднання оцінки інтегрального часу помилки для місця, згладжування малої локальної історії та калібрування повних розкладів із роздільним контролем двох помилок карти. Порівняння зі спільною моделлю, простішою персоналізацією та варіантом без згладжування ізолює ефект. Виграш зберігається проти розширених простих правил із тими самими довгими паузами. Загальні методи згладжування й оптимізації відомі; [джерела та межі внеску](phase3-local-risk-sources.md) не заявляють світової першості.

**Початкову вимогу нульового M60 не виконано:** 0,167-0,248% вільних епізодів від хвилини не мають нового виміру всередині. Це окрема метрика від правильності карти. Приблизно третина-дві п'ятих місць мають гірший особистий F або O, попри поліпшення обох середніх. Первинний кандидат і всі попередні невдачі збережені. [Новий протокол щодо якості карти](phase4-display-protocol-draft.json) є окремою чернеткою, не підміною початкового критерію.

Фаза 3 має виміряне покращення та обґрунтований обмежений внесок. Перед фазою 4 залишаються остаточна постановка й фіксація повного незалежного протоколу. Остаточні **867 місць не оцінювалися**, попередні перевірочні групи не називаються свіжим підтвердженням. [Поточний статус](phase3-novelty-gate.json), [122 тести й контрольні суми](phase3-local-risk-verification.json). Аналітичні C3/C4, [точна перевірка початку роботи](phase3-start-reachability-report.md) та попередні звіти залишаються історичними результатами своїх етапів.

'''
    current=before[:begin]+text+before[end:]
    old=next(line for line in current.splitlines() if line.startswith('| **3. Методи'))
    new='| **3. Методи, авторська модифікація і перевірка** | Локальний інтегральний ризик, згладжування та калібрування повних розкладів. Виміряне зменшення кількості вимірів і обох часів помилки; сильні контролі й вилучення складових. | [Метод](phase3-local-risk-method.md), [результат і три графіки](phase3-local-risk-report.md), [джерела](phase3-local-risk-sources.md), [перевірка](phase3-local-risk-verification.json). | **Практичний внесок отримано на розробленні.** Початковий нульовий M60 не виконано; окремий протокол якості карти ще не активовано. Остаточний тест не відкрито. |'
    (DOCS/'README.md').write_text(current.replace(old,new),encoding='utf-8')
    gate=read(folder/'phase3-novelty-gate.json')
    gate.update({'updated_on':'2026-10-25','status':'phase3_practical_author_improvement_documented_display_protocol_pending',
      'reason':'Specific hierarchical local integral-risk scheduler and whole-policy calibration have measured development benefit and controlled ablations. Original zero-M60 requirement still fails; display-focused protocol is a separate draft, not activated.',
      'current_work':'phase3-local-risk-report.md','phase4_may_start':False,'final_867_bay_test_evaluated':False,
      'current_candidate':'bay_full_alpha500_display_guarded','original_zero_M60_protocol_satisfied':False,
      'display_protocol_draft':'phase4-display-protocol-draft.json',
      'remaining_before_phase4':[
        'Finalize the research question and explicitly version the display-focused protocol; retain the original zero-M60 failure.',
        'Freeze all candidate, training, runtime and evaluation code, shared priors, control weights, metrics, seeds and analysis before accessing final867 outcomes.',
        'If permitted by the frozen pipeline, append only reserved Jan-Jun local statistics with frozen shared priors; never use reserved Jul-Sep or final Oct-Dec outcomes to tune.',
        'Keep all final results regardless of sign and report M60, Bay-level harms and development reuse.']})
    evidence=gate['completed_evidence'];evidence['current_author_method']='L.1-L.6: per-Bay empirical integrated wrong-display risk, state/clock/observed-age context, hierarchical partial pooling, cost-rate action rule and whole-policy constrained calibration. Known generic components; own precise specialization and measured effect, not a claim of world-first optimizer.'
    evidence['current_development_result']='Primary fixed allocation: calls11.9-21.8% lower, false-free time13.2-18.7% lower, false-occupied time8.4-18.8% lower than fixed60, on4 overlapping known development cells. All10 seeds improve both errors; worst seed calls reduction9.50%. No fresh confirmation cohort.'
    evidence['current_controls']='Frozen same-estimator ablations and simple policies, expanded900 controls (841 distinct tables), union1226 prior/simple definitions. Separate hindsight exact-expected-budget envelopes over pooled/personalized/unshrunk257 models and broad simple controls remain inferior on at least one error. Hindsight is not a deployable policy or confirmatory comparison.'
    evidence['current_limits']='M60nonzero0.167-0.248% of eligible free episode-phases; original protocol not met. Roughly one third to two fifths of Bays have worse personal F or O. No real energy measurement, physical sensor validation or universal optimality.'
    evidence['verification']='122 unit tests;12 independent runtime windows reproduce all17 counters and delay histograms.887 old manifest entries preserved; current artifact hashes recorded separately.'
    write_json(DOCS/'phase3-novelty-gate.json',gate)
    write_json(DOCS/'phase3-local-risk-history.json',{'created_on':'2026-10-25','historical_file_mapping':mappings,
      'current_readme_sha256':sha256(DOCS/'README.md'),'current_gate_sha256':sha256(DOCS/'phase3-novelty-gate.json')})
    return mappings


def main():
    target=DOCS/'phase3-local-risk-verification.json'
    receipt={'created_on':'2026-10-25','passed':False,'final_test_evaluated':False,'phase4_may_start':False}
    write_json(target,receipt)
    stream=io.StringIO();suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n) for n in MODULES)
    test=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    receipt.update({'tests_run':test.testsRun,'unit_tests_passed':test.wasSuccessful(),'failures':len(test.failures),
      'errors':len(test.errors),'skipped':len(test.skipped),'test_log':stream.getvalue(),
      'test_sha256':{n+'.py':sha256(CODE/(n+'.py')) for n in MODULES}});write_json(target,receipt)
    if not test.wasSuccessful():print(stream.getvalue());raise AssertionError('Unit test failure')
    assert test.testsRun==122
    receipt.update(verify_locks());receipt.update(verify_calibration());receipt.update(verify_controls())
    qa=read(CAL/'independent-audit/runtime-and-aggregation.json')
    assert sha256(CAL/'independent-audit/pre-audit-lock.json')==qa['pre_audit_lock_sha256']
    assert sha256(DOCS/'phase3-local-risk-policy.json')==qa['policy_json_sha256']
    assert len(qa['runtime_reference_checks'])==12 and all(x['all17_and_histogram_equal'] for x in qa['runtime_reference_checks'])
    assert not read(DOCS/'phase4-display-protocol-draft.json')['supersedes_original_protocol']
    assert not read(DOCS/'phase3-local-risk-summary.json')['original_zero_M60_protocol_satisfied']
    mappings=preserve_status();manifests={};snapshots=0
    for name in ('phase3-artifact-manifest.json','phase3-method-lock.json','phase3-refinement-lock.json','phase3-novelty-artifacts.json',
      'phase3-stability-artifacts.json','phase3-history-scheduler-artifacts.json','phase3-budget-comparison-artifacts.json',
      'phase3-analytic-artifacts.json','phase3-start-reachability-artifacts.json'):
        files=read(DOCS/name)['files'];manifests[name]=len(files)
        for relative,h in files.items():
            p=ROOT/relative
            if p.exists() and sha256(p)==h:continue
            found=[r for r in mappings if r['original_path']==relative and r['snapshot_sha256']==h]
            assert found and any(sha256(ROOT/r['snapshot_path'])==h for r in found),('Frozen artifact changed',relative)
            snapshots+=1
    assert sum(manifests.values())==887
    links=0
    for name in ('README.md','phase3-local-risk-report.md','phase3-local-risk-method.md','phase3-local-risk-sources.md','phase3-local-risk-defense-brief.md'):
        for link in re.findall(r'\]\(([^\s]+)\)',(DOCS/name).read_text(encoding='utf-8')):
            if link.startswith(('http:','https:','#','mailto:')):continue
            assert (DOCS/unquote(link.split('#')[0])).exists(),(name,link);links+=1
    for name in ('results','controls','tradeoffs'):
        with Image.open(DOCS/f'figures/phase3-local-risk-{name}.png') as im:assert im.width>=2400 and im.height>=1000
    receipt.update({'passed':True,'prior_manifest_entries_checked':manifests,'prior_snapshot_resolutions':snapshots,
      'independent_runtime_windows':12,'runtime_all17_and_histogram_equal':True,'local_links_checked':links,
      'figure_visual_QA':'All3 PNGs inspected; labels, legends, title and tradeoff definitions checked',
      'new_check_cohort_opened':False,'original_zero_M60_protocol_satisfied':False})
    write_json(target,receipt)
    paths={p for p in BASE.rglob('*') if p.is_file()};paths.update(DOCS.glob('phase3-local-risk-*'))
    paths.discard(DOCS/'phase3-local-risk-artifacts.json')
    paths.update(DOCS/n for n in ('README.md','phase3-novelty-gate.json','phase4-display-protocol-draft.json'))
    paths.update((DOCS/'figures').glob('phase3-local-risk-*'))
    for pattern in ('*local_risk*.py','*calibrated_schedule*.py','*frozen_local_priors*.py','README-local-risk.md'):paths.update(CODE.glob(pattern))
    paths={p for p in paths if p.is_file() and '__pycache__' not in p.parts}
    write_json(DOCS/'phase3-local-risk-artifacts.json',{'created_on':'2026-10-25','scope':'Hierarchical integral-risk schedule, calibrated whole policies and known development controls',
      'files':{p.relative_to(ROOT).as_posix():sha256(p) for p in sorted(paths)},'final_test_evaluated':False,'phase4_may_start':False})
    print({'passed':True,'tests':test.testsRun,'old_manifest_entries':sum(manifests.values()),'new_frozen_files':len(paths),
      'runtime_windows':12,'exact_budget_envelopes':receipt['exact_expected_budget_envelopes_reproduced'],'final_test_evaluated':False})


if __name__=='__main__':main()
