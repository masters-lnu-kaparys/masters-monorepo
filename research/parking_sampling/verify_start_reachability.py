"""New receipt, preserved status snapshots and verification of all older artifacts."""
import io
import re
import unittest
from urllib.parse import unquote
import numpy as np
from PIL import Image
from prepare_data import ROOT,DOCS,sha256
from run_phase3 import write_json
from assess_start_reachability import WORK
from assess_analytic_contribution import read
from start_reachability import FreeProfile,episode_reachability


def update_status():
    prior=read(DOCS/'phase3-analytic-history.json');mappings=list(prior['historical_file_mapping'])
    folder=WORK/'history';folder.mkdir(exist_ok=True)
    for name,key in (('README.md','current_readme_sha256'),('phase3-novelty-gate.json','current_gate_sha256')):
        source=DOCS/name;snapshot=folder/name
        if not snapshot.exists():
            assert sha256(source)==prior[key];snapshot.write_bytes(source.read_bytes())
        assert sha256(snapshot)==prior[key]
        mappings.append({'original_path':source.relative_to(ROOT).as_posix(),'snapshot_path':snapshot.relative_to(ROOT).as_posix(),
          'snapshot_sha256':sha256(snapshot),'reason':'Exact all-start reachability result added; prior analytical review retained byte-for-byte'})
    before=(folder/'README.md').read_text(encoding='utf-8');begin=before.index('**Поточний стан:');end=before.index('**Досліджуємо вибір часу')
    current='''**Поточний стан: фаза 3 триває; виконано [точну перевірку довільного початку роботи](phase3-start-reachability-report.md).** Для незмінених C3/75 і C4/72 сформульовано [умови досяжності](phase3-start-reachability-method.md) та збережено відтворювані приклади. C3 може пропускати цільові епізоди на перевірочних256/512 у вікнах від доби за пізнішого запуску; попередні нулі для стартів першої години залишаються правильними у своїй області. C4/72 на всіх восьми комірках має нуль за будь-якого старту за припущень перевірки. Це не гарантія майбутнього або фізичної точності.

Точний етап зменшив частину консервативних меж: навчальні256/від доби - з6 потенційних до2 індивідуально досяжних епізодів. Загалом9 рядків прикладів відповідають7 окремим записаним епізодам; критерії вікон перекриваються, для кожного епізоду може бути свій старт. Перевірено1758 малих випадків на25527 цілих і51054 дробових запусках. [Технічна перевірка](phase3-start-reachability-verification.json):104 тести; попередні результати збережено.

Є конкретний результат перевірки адаптивних розкладів: [аналітична межа](phase3-analytic-method.md) і точне уточнення для фіксованого шаблону пауз. Академічну новизну та новий кращий онлайн-планувальник не встановлено. [Попереднє порівняння за бюджетом](phase3-budget-comparison-report.md), [аналоги](phase3-analytic-sources.md), [постановка для керівника](phase3-supervisor-brief.md) збережені як історичні документи свого етапу. M60 означає вимір усередині епізоду, F/O - правильність карти. Остаточні867 місць не оцінювали; [фаза4](phase3-novelty-gate.json) залишається закритою до завершення критерію внеску та остаточного протоколу.

'''
    current=re.sub(r'(?<=[а-яіїєґА-ЯІЇЄҐ])(?=\d)|(?<=\d)(?=[а-яіїєґА-ЯІЇЄҐ])',' ',current)
    text=before[:begin]+current+before[end:]
    old=next(line for line in text.splitlines() if line.startswith('| **3. Методи'))
    new='| **3. Методи, авторська модифікація і перевірка** | Аналітична межа та точний пошук можливого пропуску для фіксованого правила за всіх початків роботи. C3/C4 не переналаштовувалися. | [Метод](phase3-start-reachability-method.md), [звіт і графік](phase3-start-reachability-report.md), [конкретні старти](phase3-start-reachability-witnesses.csv), [104 тести](phase3-start-reachability-verification.json). | **Триває.** Є точне уточнення перевірки та відтворювані пропуски C3 поза початковою годиною. Внесок ефективнішого онлайн-планувальника не встановлено; остаточний протокол не зафіксовано. |'
    (DOCS/'README.md').write_text(text.replace(old,new),encoding='utf-8')
    gate=read(folder/'phase3-novelty-gate.json')
    gate['status']='phase3_exact_all_start_verifier_complete_scheduler_contribution_unresolved'
    gate['completed_evidence']['exact_all_start_coverage']='Own specialized iff reduction S.1-S.2 for a finite free-run prefix then constant plateau. Integer boundaries and pauses reduce all real initialization times to integer representatives. Verified against1758 trace/profile cases and25527 integer plus51054 fractional forward runs. Exact stage resolves conservative bounds; this is policy verification, not a new superior online scheduler.'
    gate['completed_evidence']['exact_development_findings']='C3 individually attainable episode counts: training256 main1/sensitivity2, tuning128 main1/sensitivity3, check256 main0/sensitivity1, check512 main0/sensitivity1.9 witness rows correspond to7 distinct recorded episodes. Each may require a different initialization. Old first-hour-phase zero results remain scoped and unchanged. C4 generic bounds are zero in all8 cells; no future physical guarantee.'
    gate['completed_evidence']['verification']='104 tests passed; old95/87/76/70/59 receipts and all frozen artifacts retained with explicit status snapshots.'
    gate['current_work']='phase3-start-reachability-report.md'
    write_json(DOCS/'phase3-novelty-gate.json',gate)
    write_json(DOCS/'phase3-start-reachability-history.json',{'created_on':'2026-10-25','historical_file_mapping':mappings,
      'current_readme_sha256':sha256(DOCS/'README.md'),'current_gate_sha256':sha256(DOCS/'phase3-novelty-gate.json')})
    return mappings


def main():
    modules=('test_prepare_data','test_methods','test_refinement','test_novelty_audit','test_episode_pair_certificate',
      'test_stability_audit','test_history_certificate','test_history_scheduler','test_budget_comparison',
      'test_budget_coverage_annex','test_analytic_certificate','test_start_reachability')
    stream=io.StringIO();suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n) for n in modules)
    test=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    receipt={'created_on':'2026-10-25','passed':False,'unit_tests_passed':test.wasSuccessful(),'tests_run':test.testsRun,
      'failures':len(test.failures),'errors':len(test.errors),'skipped':len(test.skipped),'test_log':stream.getvalue(),
      'test_sha256':{n+'.py':sha256(ROOT/'research/parking_sampling'/(n+'.py')) for n in modules},
      'previous_receipts_preserved':True,'final_test_evaluated':False,'phase4_may_start':False}
    target=DOCS/'phase3-start-reachability-verification.json';write_json(target,receipt)
    if not test.wasSuccessful():print(stream.getvalue());raise AssertionError('Test failure')
    assert test.testsRun==104
    mappings=update_status()
    def check(relative,expected):
        p=ROOT/relative
        if p.exists() and sha256(p)==expected:return 'unchanged'
        for row in mappings:
            if row['original_path']==relative and row['snapshot_sha256']==expected:
                assert sha256(ROOT/row['snapshot_path'])==expected;return 'snapshot'
        raise AssertionError('Unexplained frozen change: '+relative)
    manifests={};snapshots=0
    for name in ('phase3-artifact-manifest.json','phase3-method-lock.json','phase3-refinement-lock.json',
      'phase3-novelty-artifacts.json','phase3-stability-artifacts.json','phase3-history-scheduler-artifacts.json',
      'phase3-budget-comparison-artifacts.json','phase3-analytic-artifacts.json'):
        files=read(DOCS/name)['files'];manifests[name]=len(files)
        for relative,h in files.items():snapshots+=check(relative,h)=='snapshot'
    lock=read(WORK/'pre-analysis-lock.json')
    assert lock['plan_sha256']==sha256(DOCS/'phase3-start-reachability-plan.json')
    for name,h in lock['code_sha256'].items():assert sha256(ROOT/'research/parking_sampling'/name)==h
    small=read(WORK/'independent-start-enumeration.json');results=read(WORK/'recorded-reachability.json')
    assert small['pre_analysis_lock_sha256']==results['pre_analysis_lock_sha256']==sha256(WORK/'pre-analysis-lock.json')
    assert small['grid']['trace_profile_cases']==1458 and small['combined']['trace_profile_cases']==1758 and small['all_passed']
    for case in small['seeded_trace_profile_cases']:
        profile=FreeProfile(tuple(case['prefix_pauses']),case['plateau'],case['tau'])
        assert episode_reachability(case['ends'],case['states'],0,profile)==case['backward']
    positives=read(WORK/'positive-witnesses.json');negative=read(WORK/'excluded-candidates.json')
    assert len(results['cells'])==16 and len(positives)==9
    assert len({(x['bay'],x['a'],x['b']) for x in positives})==7
    operations={k:0 for k in ('candidate_last_samples','plateau_nodes','source_queries','prefix_attempts')}
    for cell,row in results['cells'].items():
        p=WORK/(cell+'.npz');assert sha256(p)==row['arrays_sha256'];a=np.load(p)
        assert dict(zip(a['names'].tolist(),map(int,a['by_bay'].sum(axis=0))))==row['counts']
        assert set(map(int,a['bays'])).issubset(lock['cohorts'][row['cohort']])
        assert set(row['source_files'])=={'train_development' if row['cohort']=='training256' else 'validation_development'}
        for key in operations:operations[key]+=row['operations'][key]
        counts=row['counts'];assert counts['attainable_episodes']<=counts['recursive_bound']<=counts['generic_pair_bound']
        assert sum(x['attainable'] for x in row['risky_episodes'])==counts['attainable_episodes']
        if row['policy']=='C4':assert counts['generic_pair_bound']==counts['attainable_episodes']==0
    for x in positives:
        assert x['independent_reference_verified'] and x['initial_offset_seconds']>3599
        w=x['witness'];t=w['last_free_sample'];assert x['b']-75<=t<x['preceding_busy_start']
        times=[d[0] for d in x['reference_decisions']]
        assert not any(x['a']<=t<x['b'] for t in times)
        assert w['initial_start']>=x['window_start'] and w['next_sample']>=x['b']
    summary=read(DOCS/'phase3-start-reachability-summary.json');assert summary['operations']==operations
    assert len(negative)==results['negative_candidate_rows']
    with Image.open(DOCS/'figures/phase3-start-reachability.png') as im:assert im.width>=2400 and im.height>=1200
    links=0
    for name in ('README.md','phase3-start-reachability-method.md','phase3-start-reachability-report.md'):
        for link in re.findall(r'\]\(([^\s]+)\)',(DOCS/name).read_text(encoding='utf-8')):
            if link.startswith(('http:','https:','#','mailto:')):continue
            assert (DOCS/unquote(link.split('#')[0])).exists(),(name,link);links+=1
    gate=read(DOCS/'phase3-novelty-gate.json');assert not gate['phase4_may_start'] and not gate['final_867_bay_test_evaluated']
    assert read(DOCS/'phase3-analytic-verification.json')['tests_run']==95
    receipt.update({'passed':True,'prior_manifest_entries_checked':manifests,'prior_snapshot_resolutions':snapshots,
      'small_trace_profile_cases':1758,'integer_initializations':25527,'fractional_initializations':51054,
      'recorded_policy_cells':16,'witness_rows_independently_verified':9,'distinct_positive_recorded_episodes':7,
      'all_witness_starts_outside_first_hour':True,'operations':operations,'local_links_checked':links,
      'figure_visual_QA':'Final PNG inspected; legends/text separated; source-witness and overlap/count caveats explicit',
      'new_check_cohort_opened':False})
    write_json(target,receipt)
    paths={p for p in WORK.rglob('*') if p.is_file()}
    paths.update(DOCS.glob('phase3-start-reachability-*'));paths.discard(DOCS/'phase3-start-reachability-artifacts.json')
    paths.update(DOCS/n for n in ('README.md','phase3-novelty-gate.json'))
    paths.update((DOCS/'figures').glob('phase3-start-reachability.*'))
    for name in ('start_reachability.py','test_start_reachability.py','assess_start_reachability.py',
      'report_start_reachability.py','verify_start_reachability.py','README-start-reachability.md'):
        paths.add(ROOT/'research/parking_sampling'/name)
    write_json(DOCS/'phase3-start-reachability-artifacts.json',{'created_on':'2026-10-25',
      'scope':'Fixed-policy all-start episode reachability on known development histories',
      'files':{p.relative_to(ROOT).as_posix():sha256(p) for p in sorted(paths)},'final_test_evaluated':False,'phase4_may_start':False})
    print({'tests_passed':test.testsRun,'prior_entries_verified':sum(manifests.values()),'snapshot_resolutions':snapshots,
      'new_artifacts_frozen':len(paths),'trace_profile_cases':1758,'integer_initializations':25527,
      'fractional_initializations':51054,'positive_rows':9,'distinct_positive_episodes':7})


if __name__=='__main__':main()
