"""Post-execution independent QA and plain-language reporting, without retuning."""
import hashlib
import re
from urllib.parse import unquote
import numpy as np
from PIL import Image
from prepare_data import ROOT,DOCS,sha256
from run_phase3 import write_json
from assess_analytic_contribution import read
from phase4_pipeline import WORK,LOCK,CATALOG,COHORT,load_final_bundle,frozen_lock
from calibrated_schedule import CalibratedSchedule
from simulation import reference_simulate,BASE_ACTIONS
from kernels import simulate_window


def independent_runtime_checks(lock,catalog):
    chosen_policies=('author','fixed_60','control_wide','control_same_estimator_pooled',
      'control_same_estimator_bay_state','control_same_estimator_unshrunk')
    training=np.load(WORK/'local-training-statistics.npz');supported=set(map(int,training['bays']));checks=[]
    for primary,label in ((True,'primary_7_days'),(False,'sensitivity_1_day')):
        d=load_final_bundle(lock,primary_only=primary);initial,seeds=d.phases(10)
        ids=sorted(range(len(d.starts)),key=lambda w:hashlib.sha256(f'phase4-independent-QA:{d.window_ids[w]}'.encode()).hexdigest())[:2]
        missing=[w for w in range(len(d.starts)) if int(d.bays[d.bay_indexes[w]]) not in supported]
        if missing:ids.append(missing[0])
        models={name:np.load(WORK/'models'/(name+'.npz')) for name in catalog['components'] if catalog['components'][name]['kind']!='S2'}
        for key in chosen_policies:
            weights=catalog['policies'][key]['weights'];payload={'schema_version':1,'allocation_seed':20261025,
              'observed_run_edges_seconds':[60,300,900,3600,14400],'component_weights':weights,'components':{}}
            for name in weights:
                m=models[name];payload['components'][name]={'pooled_fallback':m['tables'][0].tolist(),
                  'bay_tables':{str(int(b)):t.tolist() for b,t in zip(m['bays'],m['tables'])}}
            runtime=CalibratedSchedule(payload)
            for w in dict.fromkeys(ids):
                lo,hi=d.offsets[w:w+2];e=d.ends[lo:hi];s=d.states[lo:hi];bay=int(d.bays[d.bay_indexes[w]])
                b=int(d.bay_indexes[w]);start=int(d.starts[w]+initial[w,0])
                raw,hist,decisions=reference_simulate(e,s,start,lambda o:(runtime.next_pause(bay,o),False))
                name=runtime.component_for_bay(bay);m=models[name]
                compiled,ch=simulate_window(e,s,start,1,np.array([60,60],np.int64),m['tables'][b],np.zeros(48,np.int64),
                  True,True,m['cdfs'][b],BASE_ACTIONS,seeds[w,0])
                np.testing.assert_array_equal(raw,compiled);np.testing.assert_array_equal(hist,ch)
                checks.append({'window_set':label,'window_id':d.window_ids[w],'bay':bay,'policy':key,'component':name,
                  'no_local_history':bay not in supported,'initialization_phase':0,'all17_and_histogram_equal':True,
                  'raw':raw.tolist(),'decision_count':len(decisions)})
        print('Independent runtime QA complete: '+label,flush=True)
    return checks


def cached_runtime_checks(lock,catalog):
    path=WORK/'independent-runtime-checks.json';meta=WORK/'independent-runtime-receipt.json'
    expected={'code_sha256':sha256(__file__),'entry_lock_sha256':sha256(LOCK),
      'plan_sha256':sha256(DOCS/'phase4-verification-plan.json')}
    if path.exists():
        saved=read(meta)
        for k,v in expected.items():assert saved[k]==v
        assert saved['checks_sha256']==sha256(path)
        return read(path)
    checks=independent_runtime_checks(lock,catalog);write_json(path,checks)
    write_json(meta,{**expected,'checks_sha256':sha256(path)})
    return checks


def verify_aggregate(result,catalog):
    cells={};cohort=read(COHORT);bays=np.array(cohort['bay_ids']);names=list(catalog['components'])
    for label,data in result['cohorts'].items():
        values=[];hists=[]
        for name in names:
            p=WORK/label/(name+'.npz');meta=read(p.with_suffix('.json'));assert sha256(p)==meta['arrays_sha256']
            assert meta['entry_lock_sha256']==sha256(LOCK)
            assert meta['training_receipt_sha256']==sha256(WORK/'training-receipt.json')
            a=np.load(p);raw=a['by_bay_phase'];h=a['histograms'];np.testing.assert_array_equal(a['bays'],bays)
            assert raw.shape==(867,10,17) and h.shape==(867,301) and np.all(raw>=0)
            np.testing.assert_array_equal(h.sum(axis=1),raw[:,:,5].sum(axis=1))
            np.testing.assert_array_equal(h@np.arange(301),raw[:,:,6].sum(axis=1))
            np.testing.assert_array_equal(raw[:,:,7]-raw[:,:,12],raw[:,:,5])
            assert np.all(raw[:,:,12:17]<=raw[:,:,7:12])
            assert np.all(np.diff(raw[:,:,7:12],axis=2)<=0) and np.all(np.diff(raw[:,:,12:17],axis=2)<=0)
            values.append(raw.sum(axis=1));hists.append(h)
        values=np.array(values);hists=np.array(hists);reference=values[names.index('fixed_60')]
        assert np.all(values[:,:,0]==reference[:,0])
        assert np.all(values[:,:,7:12]==reference[:,7:12])
        assert np.all(reference[:,14]==0)
        index={n:i for i,n in enumerate(names)};bycached=np.load(WORK/label/'policy-bay-counters.npz')
        for key,definition in catalog['policies'].items():
            weights=definition['weights'];r=data['policies'][key]
            expected=sum(w*values[index[n]] for n,w in weights.items());expected[:,0]=reference[:,0]
            np.testing.assert_allclose(expected.sum(axis=0),r['expected_raw'],rtol=1e-13,atol=1e-5)
            realized=np.stack([values[index[n],i] for i,n in enumerate(r['primary_allocation'])])
            np.testing.assert_array_equal(realized.sum(axis=0),r['primary_raw'])
            j=bycached['names'].tolist().index(key)
            np.testing.assert_array_equal(realized,bycached['primary'][j]);np.testing.assert_array_equal(expected,bycached['expected'][j])
        head=catalog['policies']['author']['weights'];ordered=sorted(head);cdf=np.cumsum([head[n] for n in ordered]);cdf[-1]=1.
        for row in data['author_all10_allocation_seeds']:
            totals=np.zeros(17,dtype=np.int64)
            for i,b in enumerate(bays):
                u=int.from_bytes(hashlib.sha256(f"local-risk-allocation:{row['seed']}:{int(b)}".encode()).digest()[:8],'little')/2**64
                selected=ordered[min(int(np.searchsorted(cdf,u,side='right')),len(ordered)-1)]
                totals+=values[index[selected],i]
            np.testing.assert_array_equal(totals,row['raw'])
        assert [x['seed'] for x in data['author_all10_allocation_seeds']]==list(range(20261025,20261035))
        raw=data['policies']['author']['primary_raw'];ref=data['policies']['fixed_60']['primary_raw']
        correct=(100*(1-raw[1]/ref[1])>=10 and raw[2]<=ref[2] and raw[3]<=ref[3])
        assert bool(correct)==data['success']['point_estimate_display_success']
        cells[label]={'components':len(names),'policies':len(catalog['policies']),'bays':867,'phases':10,
          'all_histograms_and_profiles_valid':True,'author_point_gate':bool(correct),'final_original_M60_zero':raw[14]==0}
    return cells


def write_assessment(result,catalog):
    primary=result['cohorts']['primary_7_days'];sensitivity=result['cohorts']['sensitivity_1_day']
    head=primary['policies']['author'];ref=primary['policies']['fixed_60'];a=head['primary_metrics'];b=ref['primary_metrics']
    reduction={k:100*(1-a[k]/b[k]) for k in ('samples_per_bay_day','F_seconds_per_bay_day','O_seconds_per_bay_day')}
    table=[]
    for key,row in primary['policies'].items():
        m=row['primary_metrics'];e=row['expected_metrics'];exphead=head['expected_metrics']
        m60=m['vacancies']['60']['missed_fraction'];miss=f'{100*m60:.3f}%' if m60 is not None else 'немає даних'
        admissible=e['samples_per_bay_day']<=exphead['samples_per_bay_day']+1e-8
        table.append(f"| {key} | {m['samples_per_bay_day']:.1f} | {m['F_seconds_per_bay_day']:.1f} | {m['O_seconds_per_bay_day']:.1f} | {miss} | {'так' if admissible else 'ні'} |")
    controls='\n'.join(table);gate=primary['success'];bs=head['bay_summary'];j=primary['author_vs_fixed60_intervals']['bonferroni_joint3_approx95']
    seeds=primary['author_all10_allocation_seeds'];savings=[100*(1*x['raw'][1]/ref['primary_raw'][1]) for x in seeds]
    savings=[100-x for x in savings]
    positive=gate['point_estimate_display_success']
    conclusion='Основний точковий критерій підтверджено' if positive else 'Основний точковий критерій не підтверджено'
    support='отримано' if gate['joint3_interval_support'] else 'не отримано'
    comparison=[]
    for key in ('control_same_estimator_pooled','control_same_estimator_bay_state','control_same_estimator_unshrunk','control_wide','control_pooled'):
        row=primary['policies'][key];m=row['expected_metrics'];h=head['expected_metrics'];c=primary['contrasts'][key]
        comparison.append(f"| {key} | {c['expected_calls_ratio_control_over_author']:.4f} | {m['F_seconds_per_bay_day']/h['F_seconds_per_bay_day']:.4f} | {m['O_seconds_per_bay_day']/h['O_seconds_per_bay_day']:.4f} | {'так' if c['control_expected_budget_no_larger'] else 'ні'} |")
    comp='\n'.join(comparison)
    miss=a['vacancies']['60'];mf=100*miss['missed_fraction'] if miss['missed_fraction'] is not None else None
    text=f'''# Що показав остаточний експеримент

25.10.2026. **{conclusion}.** Спільну наближену інтервальну підтримку трьох покращень {support}. Це результат одного заздалегідь відкладеного оцінювання за [протоколом 0.2](phase4-display-protocol.md), без зміни параметрів за кінцевими результатами.

## Основний результат на 867 місцях

На довгих відомих вікнах метод має {a['samples_per_bay_day']:.1f} вимірювань на місце-добу проти {b['samples_per_bay_day']:.1f} у щохвилинного контролю. Скорочення становить **{reduction['samples_per_bay_day']:.2f}%**. Час помилкового «вільно» становить {a['F_seconds_per_bay_day']:.2f} проти {b['F_seconds_per_bay_day']:.2f} с на місце-добу, зміна **{reduction['F_seconds_per_bay_day']:.2f}% скорочення**; час помилкового «зайнято» - {a['O_seconds_per_bay_day']:.2f} проти {b['O_seconds_per_bay_day']:.2f}, **{reduction['O_seconds_per_bay_day']:.2f}% скорочення**. Від'ємне скорочення означало б погіршення й не приховувалося б.

Це основний наперед заданий вибір таблиць, зерно 20261025. Усі десять зафіксованих зерен дають скорочення вимірів від {min(savings):.2f}% до {max(savings):.2f}%. Вони не є десятьма незалежними вибірками. Результат коротших вікон також збережено незалежно від його знака: [повний звіт і графік](phase4-display-report.md).

Граничні інтервали 98,333333% для спільної трійки: скорочення вимірів {j['calls_reduction_percent']}; різниця F у секундах {j['F_difference_seconds_per_bay_day']}; різниця O {j['O_difference_seconds_per_bay_day']}. Побудова є наближеною, умовною щодо навчання та не враховує окремо просторової залежності між місцями. Статистична підтримка не є доведенням світової новизни.

## Обов'язковий компроміс і нерівномірність

Вільні епізоди від хвилини без нового виміру: {miss['missed']:.0f}/{miss['eligible']:.0f} епізодів-фаз, **{mf:.3f}%**. У щохвилинного контролю - нуль. Це показник покриття епізодів спостереженнями; він не є часткою часу повністю неправильного показу карти. Початковий критерій нульового M60 для основного методу {'виконано на цьому тесті' if gate['original_zero_M60_satisfied'] else 'не виконано'}, а його попередня невдача на розробленні в будь-якому разі збережена.

За однакової ваги кожного BayId середні N/F/O методу: {bs['macro_method_NFO']}; щохвилинного контролю: {bs['macro_fixed60_NFO']}. Власний F гірший на {bs['worse_F_bays']}/867 місцях, O - на {bs['worse_O_bays']}/867, більше вимірювань - на {bs['more_calls_bays']}/867. Наявна локальна історія для {bs['history_supported_bays']} місць, резервний спільний варіант для {bs['no_history_bays']}; показники обох груп є в повному JSON. Отже, середній ефект не є гарантією кожному місцю.

## Усі зафіксовані контрольні методи

N/F/O наведено для реалізованого вибору таблиць. Останній стовпець порівнює очікуваний бюджет контролю з авторським методом; він не підміняє фактичну реалізовану різницю. У JSON збережено обидва порівняння.

| Метод | N на місце-добу | F, с | O, с | M60 | Очікуваний бюджет не більший за автора |
|---|---:|---:|---:|---:|---|
{controls}

Ізольовані контрольні зіставлення за точним сподіванням вибору таблиць. Відношення більше одиниці означає більший показник контролю. Однакового фактичного бюджету автоматично не припускаємо.

| Контроль | N контроль / автор | F контроль / автор | O контроль / автор | Контроль у межах очікуваного бюджету автора |
|---|---:|---:|---:|---|
{comp}

Якщо контроль використовує більше ресурсу, зіставлення не оголошується перевагою за рівного ресурсу. Додаткові контрольні інтервали точкові, без спільної поправки на все сімейство. Ретроспективне налаштування контрольних ваг на остаточному тесті не виконувалося.

## Що можна захищати

Власний результат - конкретний метод L.1-L.6 та відтворюване експериментальне дослідження його часових помилок, витрат і обмежень. Загальні інструменти згладжування та оптимізації відомі: [розмежування джерел і внеску](phase3-local-risk-sources.md). Позитивний точковий критерій і статистична підтримка наведені окремо вище; негативні додаткові показники не змінюються заради висновку.

Дані: [City of Melbourne2019](https://data.melbourne.vic.gov.au/explore/dataset/on-street-car-parking-sensor-data-2019/information/), CC BY4.0. Відтворюється записаний сенсорний стан, без власної фізичної розмітки. Строк батареї й точність ультразвуку не вимірювалися. [Сирі числа та всі зерна](phase4-display-results.json), [CSV](phase4-display-results.csv), [незалежна перевірка](phase4-verification.json).
'''
    text=re.sub(r'(?<=[а-яіїєґА-ЯІЇЄҐ])(?=\d)|(?<=\d)(?=[а-яіїєґА-ЯІЇЄҐ])',' ',text)
    (DOCS/'phase4-assessment.md').write_text(text,encoding='utf-8')
    brief=f'''# Коротке пояснення результату для захисту

Я досліджую, як часто потрібно перевіряти зайнятість паркомісця. За основу взято щохвилинне вимірювання. Запропонований спосіб використовує минулу історію конкретного місця, оцінює час можливого неправильного показу після різних пауз і підтримує нестійкі локальні оцінки спільними даними інших місць.

Після вибору методу його параметри та правила перевірки були зафіксовані. Остаточний експеримент проведено на окремих867 місцях за жовтень-грудень2019. Їхні стани за цей період не використовувалися для налаштування. Навчання за січень-червень для цих місць дозволялося за наперед визначеною процедурою.

На основних вікнах отримано {reduction['samples_per_bay_day']:.1f}% менше вимірювань, {reduction['F_seconds_per_bay_day']:.1f}% менший час помилкового показу «вільно» та {reduction['O_seconds_per_bay_day']:.1f}% менший час помилкового показу «зайнято». Основний точковий критерій {'виконано' if positive else 'не виконано'}; спільну наближену статистичну підтримку трьох покращень {support}.

Компроміс полягає в тому, що {mf:.3f}% вільних епізодів від хвилини не мають нового виміру всередині. Також виграш нерівномірний між місцями. Ці показники наведені поряд із покращеннями. Дослід оцінює розклад вимірювань і актуальність карти; фізичну точність датчика та споживання батареї з нього не визначаю.

Власний внесок - конкретна модифікація оцінювання й калібрування розкладу та перевірка її деталей проти зафіксованих контрольних методів. Загальні математичні принципи запозичені з літератури й наведені з посиланнями.

[Повна оцінка](phase4-assessment.md) · [Графік](figures/phase4-display-results.png) · [Протокол](phase4-display-protocol.md)
'''
    (DOCS/'phase4-defense-brief.md').write_text(re.sub(r'(?<=[а-яіїєґА-ЯІЇЄҐ])(?=\d)|(?<=\d)(?=[а-яіїєґА-ЯІЇЄҐ])',' ',brief),encoding='utf-8')
    return reduction


def update_status(result,reduction):
    prior=read(DOCS/'phase3-closure-history.json');mappings=list(prior['historical_file_mapping'])
    folder=WORK/'history-before-phase4-result';folder.mkdir(exist_ok=True)
    for name,key in (('README.md','current_readme_sha256'),('phase3-novelty-gate.json','current_gate_sha256')):
        source=DOCS/name;dest=folder/name
        if not dest.exists():assert sha256(source)==prior[key];dest.write_bytes(source.read_bytes())
        assert sha256(dest)==prior[key]
        mappings.append({'original_path':source.relative_to(ROOT).as_posix(),'snapshot_path':dest.relative_to(ROOT).as_posix(),
          'snapshot_sha256':sha256(dest),'reason':'Actual final result recorded; phase3 closure status preserved byte-for-byte'})
    before=(folder/'README.md').read_text(encoding='utf-8');start=before.index('**Поточний стан:');end=before.index('**Досліджуємо вибір часу')
    s=result['primary_success'];outcome='Основний точковий критерій виконано' if s['point_estimate_display_success'] else 'Основний точковий критерій не виконано'
    support='отримано' if s['joint3_interval_support'] else 'не отримано'
    status=f'''**Поточний стан: остаточний тест фази 4 виконано за незмінним протоколом.** {outcome}; спільну наближену інтервальну підтримку трьох покращень {support}. На основних вікнах867 місць скорочення вимірювань становить **{reduction['samples_per_bay_day']:.2f}%**, часу помилкового «вільно» - **{reduction['F_seconds_per_bay_day']:.2f}%**, «зайнято» - **{reduction['O_seconds_per_bay_day']:.2f}%**. Від'ємні значення скорочення означали б погіршення й також звітувалися б.

[Оцінка внеску та всіх компромісів](phase4-assessment.md), [основний звіт і графік](phase4-display-report.md), [повні числа](phase4-display-results.json), [текст для захисту](phase4-defense-brief.md), [перевірка](phase4-verification.json).

Метод і всі контрольні ваги зафіксовано до остаточних станів; після результатів переналаштування не виконувалося. [Протокол0.2](phase4-display-protocol.md) окремо досліджує витрати та час помилки карти. Початкову вимогу нульових пропусків вільних епізодів не підмінено; її невиконання та індивідуальні погіршення показані поряд із середніми. Відкладений тест тепер використаний і не може стати новим незалежним тестом після наступних змін алгоритму. Подальша робота - інтеграція зафіксованого правила та оформлення тексту, якщо не виявлено технічної помилки.

'''
    status=re.sub(r'(?<=[а-яіїєґА-ЯІЇЄҐ])(?=\d)|(?<=\d)(?=[а-яіїєґА-ЯІЇЄҐ])',' ',status)
    current=before[:start]+status+before[end:]
    old=next(x for x in current.splitlines() if x.startswith('| **4. Остаточні'))
    current=current.replace(old,'| **4. Остаточні експерименти та графіки** | Зафіксований метод і17 політик порівняно на867 місцях та двох відборах вікон. Параметри за тестом не змінювалися. | [Повний результат](phase4-assessment.md), [графік](phase4-display-report.md), [JSON](phase4-display-results.json), [перевірка](phase4-verification.json). | **Виконано.** Основний критерій і статистична підтримка наведені окремо; пропуски та особисті погіршення збережено. |')
    (DOCS/'README.md').write_text(current,encoding='utf-8')
    gate=read(folder/'phase3-novelty-gate.json');gate.update({'status':'phase4_final_evaluation_completed_without_retuning','phase3_complete':True,
      'phase4_complete':True,'final_867_bay_test_evaluated':True,'current_work':'phase4-assessment.md',
      'primary_final_success':s,'final_test_reusable_for_fresh_confirmation':False})
    write_json(DOCS/'phase3-novelty-gate.json',gate)
    write_json(DOCS/'phase4-history.json',{'created_on':'2026-10-25','historical_file_mapping':mappings,
      'current_readme_sha256':sha256(DOCS/'README.md'),'current_gate_sha256':sha256(DOCS/'phase3-novelty-gate.json')})
    return mappings


def main():
    target=DOCS/'phase4-verification.json';write_json(target,{'created_on':'2026-10-25','passed':False})
    lock=frozen_lock();catalog=read(CATALOG);result=read(WORK/'results.json')
    assert result==read(DOCS/'phase4-display-results.json')
    assert result['entry_lock_sha256']==sha256(LOCK) and not result['method_retuned']
    assert read(WORK/'training-receipt.json')['entry_lock_sha256']==sha256(LOCK)
    cells=verify_aggregate(result,catalog);checks=cached_runtime_checks(lock,catalog)
    reduction=write_assessment(result,catalog);mappings=update_status(result,reduction);manifests={};snapshots=0
    for name in ('phase3-artifact-manifest.json','phase3-method-lock.json','phase3-refinement-lock.json','phase3-novelty-artifacts.json',
      'phase3-stability-artifacts.json','phase3-history-scheduler-artifacts.json','phase3-budget-comparison-artifacts.json',
      'phase3-analytic-artifacts.json','phase3-start-reachability-artifacts.json','phase3-local-risk-artifacts.json','phase3-closure-artifacts.json'):
        files=read(DOCS/name)['files'];manifests[name]=len(files)
        for rel,h in files.items():
            if (ROOT/rel).exists() and sha256(ROOT/rel)==h:continue
            assert any(r['original_path']==rel and r['snapshot_sha256']==h and sha256(ROOT/r['snapshot_path'])==h for r in mappings),(name,rel)
            snapshots+=1
    links=0
    for name in ('phase4-assessment.md','phase4-defense-brief.md','phase4-display-report.md','README.md'):
        for link in re.findall(r'\]\(([^\s]+)\)',(DOCS/name).read_text(encoding='utf-8')):
            if link.startswith(('http:','https:','#')):continue
            assert (DOCS/unquote(link.split('#')[0])).exists(),(name,link);links+=1
    with Image.open(DOCS/'figures/phase4-display-results.png') as im:dimensions=[im.width,im.height]
    receipt={'created_on':'2026-10-25','passed':True,'entry_lock_sha256':sha256(LOCK),'verification_plan_sha256':sha256(DOCS/'phase4-verification-plan.json'),
      'verification_code_sha256':sha256(__file__),'frozen_analysis_results_sha256':sha256(WORK/'results.json'),
      'cells':cells,'independent_runtime_windows_policies':len(checks),'all17_and_histogram_equal':all(x['all17_and_histogram_equal'] for x in checks),
      'previous_manifest_entries_checked':manifests,'snapshot_resolutions':snapshots,'local_links_checked':links,'figure_dimensions':dimensions,
      'frozen_source_code_unchanged':True,'new_method_tuning':False,'final_test_evaluated':True,'all_outcomes_retained':True,
      'frozen_preflight_tests':read(DOCS/'phase3-closure-verification.json')['tests_run']}
    write_json(target,receipt)
    paths={p for p in WORK.rglob('*') if p.is_file()};paths.update(DOCS.glob('phase4-*'))
    paths.discard(DOCS/'phase4-artifacts.json');paths.update((DOCS/'figures').glob('phase4-*'))
    paths.update((DOCS/'README.md',DOCS/'phase3-novelty-gate.json',ROOT/'research/parking_sampling/assess_phase4_result.py'))
    paths={p for p in paths if p.is_file()}
    write_json(DOCS/'phase4-artifacts.json',{'created_on':'2026-10-25','files':{p.relative_to(ROOT).as_posix():sha256(p) for p in sorted(paths)},
      'phase4_complete':True,'final_test_evaluated':True,'method_retuned_after_final_states':False})
    print({'passed':True,'independent_checks':len(checks),'prior_entries_preserved':sum(manifests.values()),
      'new_artifacts':len(paths),'primary_result':result['primary_success']},flush=True)


if __name__=='__main__':main()
