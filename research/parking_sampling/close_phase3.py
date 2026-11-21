"""Version the research question and freeze a complete, unexecuted final pipeline."""
import importlib.metadata
import io
import re
import unittest
import duckdb
import numpy as np
from urllib.parse import unquote
from prepare_data import ROOT,DOCS,sha256
from run_phase3 import write_json
from assess_analytic_contribution import read
from verify_local_risk import MODULES
from phase4_pipeline import WORK,LOCK,PROTOCOL,CATALOG,COHORT,CAL,BASE,validate_frozen

CODE=ROOT/'research/parking_sampling'


def write_once(path,data):
    if path.exists():assert read(path)==data,'Already frozen content differs: '+str(path)
    else:write_json(path,data)


def policy_catalog():
    from budget_comparison import definitions
    from budget_coverage_annex import extra_definitions
    from local_risk_wide_control import bank
    from run_local_risk import grid
    selection=read(CAL/'selection-before-check.json');head=selection['headline'];policies={
      'author':{'weights':selection['selected'][head]['weights'],'role':'primary author method'},
      **{name:{'weights':{name:1.},'role':'fixed reference'} for name in ('fixed_5','fixed_30','fixed_60','fixed_120','fixed_300')},
      'C3':{'weights':{'C3':1.},'role':'historical author schedule'},'C4':{'weights':{'C4':1.},'role':'historical author schedule'},
      **{name:{'weights':{name:1.},'role':'S2 adaptation, separate objective and budget'} for name in ('S2_1440','S2_2880')}}
    for c in selection['controls'].values():
        if c['target']==head and c['feasible']:
            policies['control_'+c['family']]={'weights':c['weights'],'role':'frozen control; no final weight refit'}
    wide=read(BASE/'wide-control/selection-before-check.json');policies['control_wide']={'weights':wide['weights'],'role':'frozen broad simple control'}
    union=read(BASE/'union-control/selection-before-control-summary.json')
    policies['control_union']={'weights':union['weights'],'role':'all previous/simple definitions; identical weights to broad control if so recorded'}
    old={d.policy.name:d.policy for d in definitions()+extra_definitions()};wd=dict(bank());local={d['name']:d for d in grid()}
    needed=sorted(set().union(*(set(p['weights']) for p in policies.values())));components={}
    for name in needed:
        if name in local:
            d=local[name];components[name]={'kind':'local',**{k:d[k] for k in ('arm','lambda_F','lambda_O')}}
        elif name in wd:components[name]={'kind':'table','table':wd[name].tolist()}
        else:
            p=old[name]
            if p.kind==2:components[name]={'kind':'S2','budget':p.parameters['budget']}
            else:
                table=[]
                for ctx in range(48):
                    s=ctx//24;t=(ctx%24)//6;a=ctx%6
                    value=p.delays[s] if p.kind==0 else p.lookup[(s*4+(t if p.use_time else 0))*6+(a if p.use_run else 0)]
                    table.append(int(value))
                components[name]={'kind':'table','table':table}
    return {'created_on':'2026-10-25','selection_sha256':sha256(CAL/'selection-before-check.json'),
      'allocation_seed':20261025,'additional_seeds':list(range(20261025,20261035)),'policies':policies,'components':components,
      'S2_training_file':'.codex-work/parking-research-phase3-20261018/models/markov-counts.npz',
      'S2_training_note':'Frozen earlier Jan-Jun training over4218 Bays, including reserved training only; no final outcomes. Same-estimator ablations instead use identical frozen1063-Bay shared priors and the same appended local histories as author.'}


def cohort_metadata():
    data=read(ROOT/'.codex-work/parking-research-phase2-20261018/prepared/data-manifest.json')
    p=ROOT/data['window_manifest']['path'];assert sha256(p)==data['window_manifest']['sha256']
    c=duckdb.connect();rows=c.execute('SELECT bay,window_id,is_primary FROM read_parquet(?) WHERE split_role=? ORDER BY bay,window_id',
      [str(p),'quarantine_final_test']).fetchall();c.close()
    bays=sorted({int(b) for b,w,primary in rows if primary});assert len(bays)==867
    chosen=set(bays);primary=[w for b,w,p in rows if b in chosen and p];sensitivity=[w for b,w,p in rows if b in chosen]
    return {'created_on':'2026-10-25','bay_ids':bays,'primary_window_ids':primary,'sensitivity_window_ids':sensitivity,
      'window_metadata_sha256':sha256(p),'reserved_ids_in_original_split':len(data['reserved_bays']),
      'all_reserved_bays_with_day_windows':len({b for b,w,p in rows}),
      'selection_rule':'Exactly all867 previously fixed Bays with at least one known>=7day final window; sensitivity adds>=1day windows of these SAME Bays. Only quality-window metadata was read; no final occupancy states or policy outcomes.',
      'final_states_read':False,'final_metrics_computed':False}


def protocol():
    draft=read(DOCS/'phase4-display-protocol-draft.json');p=dict(draft)
    p.update({'protocol_id':'masters-parking-adaptive-display-v0.2','status':'frozen_before_final_states',
      'derived_from_draft_sha256':sha256(DOCS/'phase4-display-protocol-draft.json'),
      'supersedes_original_protocol':False,'active_for_new_research_question':True,
      'user_authorization':'2026-10-25 user said continue, selecting the statement to finalize the display-focused protocol and freeze the method for phase4; prior zero-M60 failure must remain.',
      'phase3_complete':True,'phase4_may_start':True,'final_test_evaluated':False,
      'cohort_file':COHORT.relative_to(ROOT).as_posix(),'candidate_and_control_catalog':CATALOG.relative_to(ROOT).as_posix(),
      'test_data':'867 primary BayIds selected solely from phase2 quality-window metadata. Oct-Dec2019 >=7day known windows primary; sensitivity includes >=1day windows of the SAME867 BayIds. The original split has955 reserved IDs and900 with day windows; additional33 day-only Bays are not silently appended to this fixed867-Bay comparison.',
      'initialization':'10 common offsets per window, original phase_offset seed20261018 and phase2 window_id using period late. For S2 random actions use stable_seed(20261018:{component_name}:{window_id}:{rep}); common initial offsets remain identical.',
      'control_analysis':'Frozen per-family mixtures from phase3, broad simple mixture, historical C3/C4, fixed references and S2_1440/2880. S2_960 is also retained inside frozen pooled control. Report primary realized and expected metrics separately. Same frozen Bay-hash allocation for each mixture. Compare actual budgets; do not claim equal-resource superiority if control uses more. No final hindsight weight optimization is performed.',
      'statistical_success':'Primary author vs fixed60 only: point calls reduction>=10%, F<=fixed60, O<=fixed60. Separate joint-support indicator requires positive lower bound for calls reduction and negative upper bounds for BOTH F/O changes in98.333333% marginal percentile intervals (Bonferroni3, approximate).5000 paired whole-Bay resamples,seed20261018; no refit. Other comparisons and sensitivity are secondary, pointwise95%, not a multiplicity-adjusted family of confirmatory claims.',
      'spatial_dependence_limit':'Bay bootstrap preserves within-Bay time dependence but does not explicitly model spatial dependence between nearby Bays. Intervals are approximate, conditional on fixed training and selection, not exact population coverage.',
      'historical_protocol_outcome':'Originalv0.1 zero-M60 condition failed for this author method on development; no later outcome changes that fact. The new question openly evaluates a display-quality/resource tradeoff while always disclosing vacancy coverage.',
      'sources':[
        {'id':'S20','title':'NIST/SEMATECH e-Handbook,7.4.7.3 Bonferroni method','url':'https://itl.nist.gov/div898/handbook/prc/section4/prc473.htm','scope':'Read general inequality and simultaneous interval construction. Used for3 predeclared metrics; not a proof of bootstrap marginal coverage.'},
        {'id':'local_method','path':'phase3-local-risk-method.md','scope':'Own equations L.1-L.6; source-specific analogues and limits in phase3-local-risk-sources.md'}]})
    return p


def protocol_text(p):
    return '''# Зафіксований протокол остаточного оцінювання, версія 0.2

Дата: 25.10.2026. [Машиночитаний протокол](phase4-display-protocol.json), [таблиці кандидатів і ваги](phase4-display-policies.json), [фіксований склад вибірки](phase4-display-cohort.json), [фіксація коду](phase4-display-entry-lock.json).

## Дослідницьке питання та збережений негативний результат

Чи можна за історією конкретного паркомісця зменшити кількість перевірок і водночас скоротити обидва часи неправильного показу на карті порівняно з вимірюванням щохвилини? Основний об'єкт перевірки - зафіксований [метод L.1-L.6](phase3-local-risk-method.md). Аналоги, запозичені складові та обмежений авторський внесок розмежовано в [огляді джерел](phase3-local-risk-sources.md).

Це **нова, явно виділена постановка**. Початковий [протокол 0.1](phase1-protocol.md) вимагав також нульових пропусків вільних епізодів від хвилини. Основний метод цього критерію на розробленні не виконав. Висновок збережено; позитивні результати за версією 0.2 не перетворюють його на успіх за версією 0.1. Жодного допустимого для експлуатації відсотка пропусків із результатів не виводимо.

## Незалежна відкладена вибірка

Фіксуються всі 867 місць із придатними вікнами жовтня-грудня 2019 тривалістю від 7 діб за незмінними правилами фази 2. Для перевірки чутливості додаються вікна від доби **тих самих 867 місць**. Ці два набори перекриваються. Початковий розподіл містив 955 зарезервованих ідентифікаторів, 900 із них мають добові вікна; 33 місця без довгого вікна не додаються до основної порівнюваної групи. Склад визначено лише з уже підготовлених метаданих якості, до читання станів остаточного тесту.

Пробіли й конфлікти не заповнюються, дати переходу часу масковані, інтервали напіввідкриті. Час - локальні календарні секунди без підтвердженого UTC-зсуву. Кожне відоме вікно має десять спільних початкових фаз. До першого виміру його стан не відгадується; крайові епізоди не включаються в показники повної тривалості. Відбір та правила підрахунку успадковано від [фази 1](phase1-protocol.md) і [підготовки даних](phase2-data-report.md).

## Навчання та повна фіксація до оцінювання

Спільні оцінки, параметр згладжування 500, дії, три ваги повних таблиць і всі випадкові зерна залишаються вибраними у фазі 3. Після фіксації навчального конвеєра дозволяється лише додати локальні статистики місць за січень-червень. Їхній зарезервований липень-вересень і жовтень-грудень не використовуються для навчання. Відсутня локальна історія означає спільний резервний варіант. Це прогнозування майбутньої поведінки місць із минулою історією, а не перевірка цілком нового пристрою без історії.

Контролі з тією самою оцінкою ризику отримують ті самі локальні історії та незмінні спільні оцінки. S2 використовує раніше заморожену навчальну таблицю переходів за січень-червень для 4218 місць; її ширша спільна історія розкрита в каталозі, тому ізольований ефект згладжування оцінюється саме за контролями з однаковим оцінювачем.

Фіксуються вихідний код навчання, симуляції, аналізу та тестів, версії пакетів, хеші даних, спільних оцінок, моделей і контрольних ваг. Навчені локальні таблиці додатково хешуються до першого читання остаточних станів. Після цього всі кінцеві результати зберігаються незалежно від знака. Переналаштування на цих 867 місцях означало б нове пошукове дослідження, для якого потрібна інша незалежна вибірка.

## Показники та правило висновку

Основні показники: N - вимірювання на відому місце-добу; F - секунди помилкового показу «вільно»; O - секунди помилкового показу «зайнято» за ту саму одиницю часу. Основний реалізований вибір таблиць має наперед задане зерно 20261025. Точне сподівання за вибором таблиці показується окремо. Показуються всі десять зерен 20261025-20261034 без вибору найкращого.

Точковий критерій на довгих вікнах: N менше щохвилинного щонайменше на 10%, F та O не більші. Окремий критерій статистичної підтримки: нижня межа скорочення N додатна, а верхні межі різниць F та O від'ємні. Для трьох основних показників використовуються 98,333333% граничні інтервали; конструкція за нерівністю Бонферроні наведена в [NIST/SEMATECH, розділ 7.4.7.3](https://itl.nist.gov/div898/handbook/prc/section4/prc473.htm). Вона не виправляє можливу неточність окремих наближених інтервалів.

Інтервали отримуються 5000 парними повторними відборами цілих BayId із зерном 20261018: усі вікна й фази одного місця залишаються разом. Додатково подаються звичайні точкові 95% інтервали. Метод не перенавчається при повторному відборі. Інтервали умовні щодо навчання й вибору моделі; просторова залежність між місцями окремо не моделюється. Тому це наближене статистичне свідчення у визначеній області, а не точна гарантія популяційної якості.

Обов'язкові додаткові результати: пропуски вільних епізодів за порогами 0,30,60,120,300 с з чисельником і знаменником; медіана й 95-й процентиль затримки серед виявлених епізодів; середні з однаковою вагою місць; кількість місць із гіршими власними F/O та більшою кількістю вимірів; групи з локальною історією та без неї. Нульовий знаменник означає відсутність даних. M60 не є часткою часу неправильного показу карти.

Основне порівняння - авторський метод проти щохвилинного. Додатково зберігаються зафіксовані прості, спільні, персоналізовані та незгладжені контролі, широкі прості правила з паузами до 300 с, попередні C3/C4, постійні інтервали й адаптація S2. Показується фактична різниця бюджетів. Перевага за однакового ресурсу не заявляється, якщо контроль витратив більше. Додаткові зіставлення не видаються за сімейство незалежно підтверджених гіпотез; контрольні ваги за тестом не оптимізуються.

## Межі висновку та відтворення

Джерело: [City of Melbourne, сенсорна історія 2019](https://data.melbourne.vic.gov.au/explore/dataset/on-street-car-parking-sensor-data-2019/information/), CC BY 4.0. Це відтворення записаних станів, без незалежної фізичної розмітки, вимірювання батареї чи перевірки ультразвуку. Наукові аналоги й межі внеску наведено в [реєстрі джерел](phase3-local-risk-sources.md).

Команди й захист від зміни зафіксованих артефактів: [README фази 4](../../../research/parking_sampling/README-phase4.md). Закриття фази 3 означає готовність такого експерименту, а не позитивний результат іще не виконаного остаточного тесту.
'''


def main():
    if LOCK.exists():validate_frozen(read(LOCK));print('Phase3 already closed; frozen final pipeline unchanged');return
    assert read(DOCS/'phase3-local-risk-verification.json')['passed']
    prior=read(DOCS/'phase3-local-risk-history.json');mappings=list(prior['historical_file_mapping'])
    history=WORK/'history';history.mkdir(parents=True,exist_ok=True)
    for name,key in (('README.md','current_readme_sha256'),('phase3-novelty-gate.json','current_gate_sha256')):
        p=DOCS/name;q=history/name
        assert sha256(p)==prior[key]
        if not q.exists():q.write_bytes(p.read_bytes())
        assert sha256(q)==prior[key]
        mappings.append({'original_path':p.relative_to(ROOT).as_posix(),'snapshot_path':q.relative_to(ROOT).as_posix(),
          'snapshot_sha256':sha256(q),'reason':'Phase3 closed under separately versioned display question; previous status preserved'})
    manifests={}
    for name in ('phase3-artifact-manifest.json','phase3-method-lock.json','phase3-refinement-lock.json','phase3-novelty-artifacts.json',
      'phase3-stability-artifacts.json','phase3-history-scheduler-artifacts.json','phase3-budget-comparison-artifacts.json',
      'phase3-analytic-artifacts.json','phase3-start-reachability-artifacts.json','phase3-local-risk-artifacts.json'):
        files=read(DOCS/name)['files'];manifests[name]=len(files)
        for rel,h in files.items():
            p=ROOT/rel
            if p.exists() and sha256(p)==h:continue
            assert any(r['original_path']==rel and r['snapshot_sha256']==h and sha256(ROOT/r['snapshot_path'])==h for r in mappings),(name,rel)
    cohort=cohort_metadata();catalog=policy_catalog();p=protocol()
    write_once(COHORT,cohort);write_once(CATALOG,catalog);write_once(PROTOCOL,p)
    (DOCS/'phase4-display-protocol.md').write_text(protocol_text(p),encoding='utf-8')
    modules=(*MODULES,'test_phase4_pipeline');stream=io.StringIO()
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n) for n in modules)
    tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    receipt={'created_on':'2026-10-25','passed':tests.wasSuccessful(),'tests_run':tests.testsRun,'failures':len(tests.failures),
      'errors':len(tests.errors),'test_log':stream.getvalue(),'previous_manifest_entries_checked':manifests,
      'test_source_sha256':{n:sha256(CODE/(n+'.py')) for n in modules},'final_states_read':False,'final_test_evaluated':False}
    write_json(DOCS/'phase3-closure-verification.json',receipt)
    if not tests.wasSuccessful():print(stream.getvalue());raise AssertionError('Preflight failed; phase3 not closed')
    assert tests.testsRun==131
    for name in ('phase4-display-protocol.md',):
        for link in re.findall(r'\]\(([^\s]+)\)',(DOCS/name).read_text(encoding='utf-8')):
            if link.startswith(('https:','http:','#')):continue
            target=DOCS/unquote(link)
            if target==LOCK:continue
            assert target.exists(),(name,link)
    # The complete code and controls are frozen before train/evaluate can run.
    names=('phase4_pipeline.py','phase4_analysis.py','test_phase4_pipeline.py','close_phase3.py','local_risk.py',
      'frozen_local_priors.py','data_access.py','simulation.py','kernels.py','policies.py','markov_baseline.py',
      'prepare_data.py','run_phase3.py','assess_analytic_contribution.py','requirements.txt','README-phase4.md')
    paths={CODE/n for n in names}
    # Imported legacy modules are kept immutable too, including import-time dependencies.
    paths.update(CODE.glob('*.py'))
    paths.update((PROTOCOL,CATALOG,COHORT,DOCS/'phase4-display-protocol.md',DOCS/'phase3-closure-verification.json',
      DOCS/'phase2-data-lock.json',DOCS/'phase3-local-risk-artifacts.json',CAL/'shared-priors.npz',CAL/'selection-before-check.json',
      BASE/'wide-control/selection-before-check.json',BASE/'union-control/selection-before-control-summary.json',
      ROOT/catalog['S2_training_file'],ROOT/'.codex-work/parking-research-phase2-20261018/prepared/data-manifest.json'))
    paths.update(CODE/(n+'.py') for n in modules)
    paths.add(ROOT/'.codex-work/parking-research-phase2-20261018/prepared/windows.parquet')
    lock={'created_on':'2026-10-25','phase3_complete':True,'phase4_may_start':True,'final_test_evaluated_at_freeze':False,
      'active_protocol':'masters-parking-adaptive-display-v0.2','original_zero_M60_protocol_satisfied':False,
      'allowed_roles':['quarantine_train_reserved','quarantine_final_test'],
      'training_code_sha256':{x.name:sha256(x) for x in sorted(CODE.glob('*.py'))},
      'package_versions':{n:importlib.metadata.version(n) for n in ('duckdb','numpy','scipy','numba','llvmlite','matplotlib')},
      'files':{x.relative_to(ROOT).as_posix():sha256(x) for x in sorted(paths)},
      'source_partition_sha256':{k:v['sha256'] for k,v in read(ROOT/'.codex-work/parking-research-phase2-20261018/prepared/data-manifest.json')['files'].items()
        if k in ('quarantine_train_reserved','quarantine_final_test')},
      'supersedes_for_readiness':'phase4-entry-lock.json; old candidate decision remains immutable'}
    write_once(LOCK,lock);validate_frozen(lock)
    before=(history/'README.md').read_text(encoding='utf-8');begin=before.index('**Поточний стан:');end=before.index('**Досліджуємо вибір часу')
    status='''**Поточний стан: фазу 3 закрито; метод і повний протокол фази 4 зафіксовано до остаточного оцінювання.** Власний практичний результат на розробленні: на 11,9-21,8% менше вимірювань, на 13,2-18,7% менший час помилкового «вільно» та на 8,4-18,8% менший час помилкового «зайнято». [Звіт із графіками та контролями](phase3-local-risk-report.md), [метод і обмеження](phase3-local-risk-method.md).

[Протокол 0.2](phase4-display-protocol.md) досліджує якість карти та витрати. Початковий критерій нульового M60 не виконано й не переписано: це збережений негативний результат за версією 0.1. Пропуски вільних епізодів, індивідуальні погіршення та всі десять зерен залишаються обов'язковими результатами. Загальна користь і власна модифікація підтверджені на розробленні; світова першість не заявляється.

[Фіксація коду, моделей і правил](phase4-display-entry-lock.json), [867 місць і вікна](phase4-display-cohort.json), [131 тест підготовки](phase3-closure-verification.json). Остаточні стани жовтня-грудня ще не читалися, результати на них не обчислювалися. Наступна фаза виконує вже зафіксований експеримент; результат зберігається незалежно від знака, переналаштування за тестом заборонене.

'''
    current=before[:begin]+status+before[end:]
    old=next(x for x in current.splitlines() if x.startswith('| **3. Методи'))
    current=current.replace(old,'| **3. Методи, авторська модифікація і перевірка** | Локальний інтегральний ризик, згладжування та калібрування повних розкладів. Виміряний ефект складових і сильні контролі. | [Результат](phase3-local-risk-report.md), [джерела](phase3-local-risk-sources.md), [зафіксований протокол](phase4-display-protocol.md). | **Закрито за окремою постановкою 0.2.** Початковий нульовий M60 не виконано; цей результат збережено. |')
    (DOCS/'README.md').write_text(current,encoding='utf-8')
    gate=read(history/'phase3-novelty-gate.json');gate.update({'updated_on':'2026-10-25','status':'phase3_complete_display_protocol_frozen_phase4_ready',
      'phase3_complete':True,'phase4_may_start':True,'current_work':'phase4-display-protocol.md','final_867_bay_test_evaluated':False,
      'reason':'User authorized continuation; separate display-focused question versioned explicitly. Own method, controlled effects, literature limits and full final pipeline are frozen. Original zero-M60 failure retained.',
      'remaining_before_phase4':[],'active_protocol':'phase4-display-protocol.json','entry_lock':'phase4-display-entry-lock.json'})
    gate['completed_evidence']['phase3_closure']='131 tests; complete final training/runtime/analysis/control code and867 metadata cohort locked before final states. Phase4 may run without further method selection. Positive final result is not assumed.'
    write_json(DOCS/'phase3-novelty-gate.json',gate)
    write_json(DOCS/'phase3-closure-history.json',{'created_on':'2026-10-25','historical_file_mapping':mappings,
      'current_readme_sha256':sha256(DOCS/'README.md'),'current_gate_sha256':sha256(DOCS/'phase3-novelty-gate.json')})
    paths.update((LOCK,DOCS/'README.md',DOCS/'phase3-novelty-gate.json',DOCS/'phase3-closure-history.json',*history.iterdir()))
    write_json(DOCS/'phase3-closure-artifacts.json',{'created_on':'2026-10-25','files':{x.relative_to(ROOT).as_posix():sha256(x) for x in sorted(paths)},
      'phase3_complete':True,'phase4_may_start':True,'final_test_evaluated':False})
    print({'phase3_complete':True,'phase4_ready':True,'tests':tests.testsRun,'old_manifest_entries_preserved':sum(manifests.values()),
      'final_bays':len(cohort['bay_ids']),'primary_windows':len(cohort['primary_window_ids']),'sensitivity_windows':len(cohort['sensitivity_window_ids']),
      'frozen_components':len(catalog['components']),'frozen_policies':len(catalog['policies']),'final_test_evaluated':False})


if __name__=='__main__':main()
